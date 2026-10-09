#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Odom and LiDAR guarded centre-line patrol for the 4.2 m arena.

The route is a surveyed sequence of axis-aligned road-centre goals.  Robot
odometry, LaserScan and robot camera are the only inputs used for motion and
signal decisions. Gazebo model state is deliberately absent from this node.
"""
from __future__ import print_function

import csv
import json
import math
import os
import time

import cv2
import rospy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String
from tf.transformations import euler_from_quaternion
from sq_task_plan_4p2 import FRONT_CAMERA, TASK_KIND


ROADS = [(-2.1, 2.1, 1.5, 2.1), (-2.1, -1.5, -1.5, 1.5),
         (-1.5, .3, .3, .9), (-.3, .3, -1.5, .9),
         (-2.1, 1.5, -2.1, -1.5), (.9, 1.5, -1.5, 1.5)]
LIGHTS = ('TL_UP_WAIT', 'TL_LOW_WAIT')


def clamp(value, limit):
    return max(-limit, min(limit, value))


def angle_error(goal, actual):
    return math.atan2(math.sin(goal - actual), math.cos(goal - actual))


def road_safe(x, y, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    for dx in (-.167, .167):
        for dy in (-.1515, .1515):
            px, py = x + dx*c - dy*s, y + dx*s + dy*c
            if not any(x0-.003 <= px <= x1+.003 and y0-.003 <= py <= y1+.003
                       for x0, x1, y0, y1 in ROADS):
                return False
    return True


def load_route(path):
    with open(path, 'rb') as handle:
        rows = list(csv.reader(line for line in handle if not line.startswith('#')))
    if not rows or rows[0][0].decode('utf8') != u'名称':
        raise ValueError('invalid route CSV')
    return [(row[0].decode('utf8'), float(row[1]), float(row[2]), float(row[3]))
            for row in rows[1:]]


class Patrol(object):
    def __init__(self):
        rospy.init_node('sq_patrol_4p2')
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        route_file = rospy.get_param('~route_file', os.path.join(root, 'route', 'sq_route_patrol_4p2.csv'))
        self.route = load_route(route_file)
        assigned = [name for name, _, _, _ in self.route
                    if not name.startswith(u'过路')]
        if len(assigned) != len(TASK_KIND) or set(assigned) != set(TASK_KIND):
            raise ValueError('route observation tasks do not match 4.2 m task plan')
        self.start_index = int(rospy.get_param('~start_index', 1))
        self.end_index = int(rospy.get_param('~end_index', len(self.route)))
        self.report_file = rospy.get_param('~report_file', '/tmp/sq4_patrol_4p2.json')
        self.capture_dir = rospy.get_param('~capture_dir', '/tmp/sq4_patrol_frames')
        self.odom = None
        self.scan = None
        self.frame = None
        self.task_frame = None
        self.vision = 'unknown'
        self.vision_seen = 0.0
        self.bridge = CvBridge()
        self.pub_cmd = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.pub_cur = rospy.Publisher('/sq/patrol/current', String, queue_size=1, latch=True)
        self.pub_res = rospy.Publisher('/sq/patrol/result', String, queue_size=10)
        self.pub_observation = rospy.Publisher('/sq/patrol/observation', String, queue_size=10)
        self.pub_voice = rospy.Publisher('/sq/voice/say', String, queue_size=10)
        rospy.Subscriber('/odom', Odometry, self.on_odom, queue_size=1)
        rospy.Subscriber('/scan', LaserScan, self.on_scan, queue_size=1)
        rospy.Subscriber('/camera/rgb/image_raw', Image, self.on_image, queue_size=1)
        rospy.Subscriber('/task_camera/image_raw', Image, self.on_task_image, queue_size=1)
        rospy.Subscriber('/sq/vision/traffic_light', String, self.on_vision, queue_size=1)
        self.records = []
        self.road_samples = 0
        self.outside_samples = 0

    def on_odom(self, message):
        self.odom = message

    def on_scan(self, message):
        self.scan = message

    def on_image(self, message):
        self.frame = message

    def on_task_image(self, message):
        self.task_frame = message

    def on_vision(self, message):
        self.vision = message.data
        self.vision_seen = time.time()

    def pose(self):
        message = self.odom
        if message is None or (rospy.Time.now() - message.header.stamp).to_sec() > 1.0:
            raise RuntimeError('stale odometry')
        p, q = message.pose.pose.position, message.pose.pose.orientation
        yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])[2]
        return p.x, p.y, yaw

    def check_road(self):
        x, y, yaw = self.pose()
        self.road_samples += 1
        if not road_safe(x, y, yaw):
            self.outside_samples += 1
            raise RuntimeError('body left road at %.3f %.3f yaw %.3f' % (x, y, yaw))
        return x, y, yaw

    def clear_ahead(self):
        message = self.scan
        if message is None or (rospy.Time.now() - message.header.stamp).to_sec() > 1.0:
            raise RuntimeError('stale lidar')
        ranges = message.ranges
        nearest = 100.0
        for i, distance in enumerate(ranges):
            ray = message.angle_min + i * message.angle_increment
            if (abs(ray) < .26 and not math.isnan(distance) and not math.isinf(distance)
                    and message.range_min < distance < nearest):
                nearest = distance
        if nearest < .23:
            raise RuntimeError('obstacle %.3f m ahead' % nearest)

    def publish_world_velocity(self, vx, vy, wz):
        _, _, yaw = self.check_road()
        command = Twist()
        command.linear.x = math.cos(yaw)*vx + math.sin(yaw)*vy
        command.linear.y = -math.sin(yaw)*vx + math.cos(yaw)*vy
        command.angular.z = wz
        self.pub_cmd.publish(command)

    def stop(self):
        for _ in range(3):
            self.pub_cmd.publish(Twist())
            time.sleep(.05)

    def rotate(self, target):
        deadline = time.time() + 18
        try:
            while time.time() < deadline and not rospy.is_shutdown():
                _, _, yaw = self.check_road()
                error = angle_error(target, yaw)
                if abs(error) < .055:
                    self.stop()
                    return
                self.publish_world_velocity(0, 0, clamp(1.8*error, .38))
                time.sleep(.05)
            raise RuntimeError('rotation timeout')
        finally:
            self.stop()

    def drive(self, start, goal):
        sx, sy = start
        gx, gy = goal
        total = math.hypot(gx-sx, gy-sy)
        if total < .005:
            return
        if abs(gx-sx) > .015 and abs(gy-sy) > .015:
            raise RuntimeError('diagonal route segment is not a road centre line')
        self.rotate(math.atan2(gy-sy, gx-sx))
        deadline = time.time() + max(18, total/.06+10)
        try:
            while time.time() < deadline and not rospy.is_shutdown():
                x, y, _ = self.check_road()
                ex, ey = gx-x, gy-y
                remaining = math.hypot(ex, ey)
                if remaining < .025:
                    self.stop()
                    return
                if remaining > .12:
                    self.clear_ahead()
                vx, vy = clamp(1.3*ex, .085), clamp(1.3*ey, .085)
                self.publish_world_velocity(vx, vy, 0)
                time.sleep(.05)
            raise RuntimeError('drive timeout')
        finally:
            self.stop()

    def wait_for_green(self):
        # Start only after seeing an entire red-to-green transition in the
        # camera.  A green already in progress may have too little time left.
        deadline = time.time() + 70
        red_count = 0
        green_count = 0
        announced = None
        while time.time() < deadline and not rospy.is_shutdown():
            state = self.vision if time.time()-self.vision_seen < .7 else 'unknown'
            if state == 'red':
                red_count += 1
                green_count = 0
                if red_count >= 3 and announced != 'red':
                    self.pub_voice.publish(String(data=u'识别到红灯，停车等待'.encode('utf8')))
                    announced = 'red'
            elif state == 'green' and red_count >= 3:
                green_count += 1
                if green_count >= 3:
                    self.pub_voice.publish(String(data=u'识别到绿灯，开始通行'.encode('utf8')))
                    return
            elif state == 'yellow' and announced != 'yellow':
                green_count = 0
                self.pub_voice.publish(String(data=u'识别到黄灯，继续等待'.encode('utf8')))
                announced = 'yellow'
            elif state != 'green':
                green_count = 0
            time.sleep(.2)
        raise RuntimeError('no fresh visual red-to-green transition')

    def capture(self, index, name):
        # Front RGBD camera resolves plates, people and meter digits. The wide
        # monocular camera includes whole building facades and roadside areas.
        front_view = name in FRONT_CAMERA
        message = self.frame if front_view else self.task_frame
        if message is None or (rospy.Time.now()-message.header.stamp).to_sec() > .7:
            return ''
        if not os.path.isdir(self.capture_dir):
            os.makedirs(self.capture_dir)
        path = os.path.join(self.capture_dir, '%02d_%s.jpg' % (index, name))
        try:
            image = self.bridge.imgmsg_to_cv2(message, 'bgr8')
            return path if cv2.imwrite(path, image) else ''
        except Exception:
            return ''

    def save(self):
        with open(self.report_file, 'wb') as handle:
            handle.write(json.dumps({'records': self.records, 'planned_count': len(self.route),
                                     'road_samples': self.road_samples,
                                     'outside_samples': self.outside_samples},
                                    ensure_ascii=False, indent=2).encode('utf8'))

    def run(self):
        deadline = time.time()+60
        while time.time()<deadline and not rospy.is_shutdown():
            if self.odom is not None and self.scan is not None:
                break
            time.sleep(.1)
        if self.odom is None or self.scan is None:
            raise RuntimeError('odom or lidar missing')
        if self.start_index == 1:
            previous = (1.8, 1.8)
        else:
            previous = (self.route[self.start_index-2][1], self.route[self.start_index-2][2])
        x, y, _ = self.check_road()
        if math.hypot(x-previous[0],y-previous[1]) > .12:
            raise RuntimeError('start pose does not match preceding route point')
        for index in range(self.start_index, min(self.end_index,len(self.route))+1):
            name, gx, gy, yaw = self.route[index-1]
            self.pub_cur.publish(String(data=name.encode('utf8')))
            started = time.time()
            try:
                self.drive(previous, (gx,gy))
                self.rotate(yaw)
                if name in LIGHTS:
                    self.wait_for_green()
                x, y, a = self.check_road()
                image_path = self.capture(index,name.encode('ascii','ignore')) if not name.startswith(u'过路') else ''
                if image_path:
                    self.pub_observation.publish(String(data=json.dumps({
                        'task_id': name, 'task_type': TASK_KIND[name],
                        'index': index, 'image': image_path,
                        'stamp': rospy.Time.now().to_sec(),
                    }, ensure_ascii=False).encode('utf8')))
                record = {'index':index,'name':name,'target':[gx,gy,yaw],
                          'odom':[round(x,3),round(y,3),round(a,3)],
                          'xy_error_m':round(math.hypot(x-gx,y-gy),3),
                          'elapsed_s':round(time.time()-started,1),
                          'status':'success','image':image_path}
                if not name.startswith(u'过路'):
                    self.pub_res.publish(String(data=(name+u' 已到达观察位').encode('utf8')))
                previous = (gx,gy)
            except Exception as exc:
                self.stop()
                record = {'index':index,'name':name,'target':[gx,gy,yaw],
                          'elapsed_s':round(time.time()-started,1),
                          'status':'failed','reason':str(exc)}
                self.records.append(record)
                self.save()
                raise
            self.records.append(record)
            self.save()
            rospy.loginfo('[sq4 patrol] %d %s error %.3f m' %
                          (index,name.encode('utf8'),record['xy_error_m']))
        self.stop()


if __name__ == '__main__':
    try:
        Patrol().run()
    except (RuntimeError, ValueError) as exc:
        rospy.logerr('[sq4 patrol] %s' % exc)
        raise
    finally:
        try:
            rospy.Publisher('/cmd_vel',Twist,queue_size=1).publish(Twist())
        except Exception:
            pass
