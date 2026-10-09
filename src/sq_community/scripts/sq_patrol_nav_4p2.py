#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""4.2 m multi-goal patrol using the previously proven move_base action path.

Observation and transit goals are loaded from the current 4.2 m route CSV.
Camera frames and OCR events use the same topics as the odometry patrol. The
traffic-light stop gates still read the robot camera, never Gazebo truth.
"""
from __future__ import print_function

import csv
import json
import math
import os
import time

import actionlib
import cv2
import rospy
from cv_bridge import CvBridge
from geometry_msgs.msg import Quaternion, Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String
from tf.transformations import euler_from_quaternion, quaternion_from_euler
from sq_task_plan_4p2 import FRONT_CAMERA, TASK_KIND
from sq_patrol_4p2 import angle_error, clamp, road_safe, on_stop_line, make_deadline, before_deadline


LIGHTS = ('TL_UP_WAIT', 'TL_UP_WAIT_2', 'TL_LOW_WAIT')


def load_route(path):
    with open(path, 'rb') as handle:
        rows = list(csv.reader(line for line in handle if not line.startswith('#')))
    if not rows or rows[0][0].decode('utf8') != u'名称':
        raise ValueError('invalid route CSV')
    return [(row[0].decode('utf8'), float(row[1]), float(row[2]), float(row[3]))
            for row in rows[1:]]


class Patrol(object):
    def __init__(self):
        rospy.init_node('sq_patrol_nav_4p2')
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.route = load_route(rospy.get_param('~route_file',
                               os.path.join(root, 'route', 'sq_route_patrol_4p2.csv')))
        assigned = [name for name, _, _, _ in self.route
                    if not name.startswith(u'过路')]
        if len(assigned) != len(TASK_KIND) or set(assigned) != set(TASK_KIND):
            raise ValueError('route observation tasks do not match 4.2 m task plan')
        self.start_index = int(rospy.get_param('~start_index', 1))
        self.end_index = int(rospy.get_param('~end_index', len(self.route)))
        self.goal_timeout = float(rospy.get_param('~goal_timeout', 60.0))
        self.report_file = rospy.get_param('~report_file', '/tmp/sq4_patrol_nav.json')
        self.capture_dir = rospy.get_param('~capture_dir', '/tmp/sq4_patrol_nav_frames')
        self.bridge = CvBridge()
        self.frame = None
        self.task_frame = None
        self.vision = 'unknown'
        self.vision_seen = 0.0
        self.odom = None
        self.scan = None
        self.records = []
        self.road_samples = 0
        self.outside_samples = 0
        self.pub_cmd = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        self.pub_cur = rospy.Publisher('/sq/patrol/current', String, queue_size=1,
                                       latch=True)
        self.pub_res = rospy.Publisher('/sq/patrol/result', String, queue_size=10)
        self.pub_observation = rospy.Publisher('/sq/patrol/observation', String,
                                               queue_size=10)
        self.pub_voice = rospy.Publisher('/sq/voice/say', String, queue_size=10)
        rospy.Subscriber('/camera/rgb/image_raw', Image, self.on_image, queue_size=1)
        rospy.Subscriber('/task_camera/image_raw', Image, self.on_task_image,
                         queue_size=1)
        rospy.Subscriber('/sq/vision/traffic_light', String, self.on_vision,
                         queue_size=1)
        rospy.Subscriber('/odom', Odometry, self.on_odom, queue_size=1)
        rospy.Subscriber('/scan', LaserScan, self.on_scan, queue_size=1)
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)

    def on_image(self, message):
        self.frame = message

    def on_task_image(self, message):
        self.task_frame = message

    def on_vision(self, message):
        self.vision = message.data
        self.vision_seen = time.time()

    def on_odom(self, message):
        self.odom = message

    def on_scan(self, message):
        self.scan = message

    def odom_pose(self):
        message = self.odom
        if message is None or (rospy.Time.now()-message.header.stamp).to_sec() > 1.0:
            raise RuntimeError('stale odometry during goal refinement')
        p, q = message.pose.pose.position, message.pose.pose.orientation
        yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])[2]
        return p.x, p.y, yaw

    def guarded_turn(self, yaw):
        """Rotate only while lidar and the whole footprint have clearance."""
        start_x, start_y, _ = self.odom_pose()
        deadline = make_deadline(20)
        try:
            while before_deadline(deadline):
                px, py, current = self.odom_pose()
                if math.hypot(px-start_x, py-start_y) > .06 or not road_safe(px, py, current):
                    raise RuntimeError('unsafe local yaw refinement')
                if self.scan is None or (rospy.Time.now()-self.scan.header.stamp).to_sec() > 1.0:
                    raise RuntimeError('stale lidar during goal refinement')
                # The laser is mounted 10 cm to the robot's right, so a raw
                # 21 cm reading toward the west wall can still leave 31 cm
                # from the body center. Compare hits in the base frame.
                nearby = []
                for i, distance in enumerate(self.scan.ranges):
                    if (math.isnan(distance) or math.isinf(distance) or
                            not self.scan.range_min < distance < self.scan.range_max):
                        continue
                    ray = self.scan.angle_min + i*self.scan.angle_increment
                    hit_x = .025 + distance*math.cos(ray)
                    hit_y = -.100 + distance*math.sin(ray)
                    nearby.append(math.hypot(hit_x, hit_y))
                if nearby and min(nearby) < .245:
                    raise RuntimeError('obstacle too close for yaw refinement')
                error = angle_error(yaw, current)
                if abs(error) >= .08 and on_stop_line(px,py,current):
                    raise RuntimeError('yaw refinement overlaps a stop line')
                if abs(error) < .08:
                    return True
                command = Twist()
                command.angular.z = clamp(1.5*error, .35)
                self.pub_cmd.publish(command)
                time.sleep(.05)
            raise RuntimeError('local yaw refinement timeout')
        finally:
            self.pub_cmd.publish(Twist())
            time.sleep(.1)
            self.pub_cmd.publish(Twist())

    def finish_near_goal(self, name, x, y, yaw):
        """Refine task-camera yaw after DWA aborts within 15 cm of a goal."""
        px, py, _ = self.odom_pose()
        if math.hypot(px-x, py-y) > .15:
            return False
        rospy.logwarn('[sq4 nav] %s DWA stopped %.3f m from goal; refining yaw' %
                      (name, math.hypot(px-x, py-y)))
        return self.guarded_turn(yaw)

    def wait_server(self):
        deadline = time.time() + 90
        while time.time() < deadline and not rospy.is_shutdown():
            if self.client.wait_for_server(rospy.Duration(1.0)):
                return
            time.sleep(.2)
        raise RuntimeError('move_base action server unavailable')

    def goal(self, x, y, yaw):
        target = MoveBaseGoal()
        target.target_pose.header.frame_id = 'map'
        target.target_pose.header.stamp = rospy.Time.now()
        target.target_pose.pose.position.x = x
        target.target_pose.pose.position.y = y
        q = quaternion_from_euler(0, 0, yaw)
        target.target_pose.pose.orientation = Quaternion(*q)
        return target

    def navigate(self, name, x, y, yaw):
        self.client.send_goal(self.goal(x, y, yaw))
        deadline = time.time() + self.goal_timeout
        recovered_heading = False
        while time.time() < deadline and not rospy.is_shutdown():
            px, py, current = self.odom_pose()
            self.road_samples += 1
            if not road_safe(px, py, current):
                self.outside_samples += 1
                self.client.cancel_goal()
                self.pub_cmd.publish(Twist())
                raise RuntimeError('%s body left road at %.3f %.3f yaw %.3f' %
                                   (name, px, py, current))
            state = self.client.get_state()
            if state == actionlib.GoalStatus.SUCCEEDED:
                return 'move_base'
            if state in (actionlib.GoalStatus.ABORTED,
                         actionlib.GoalStatus.REJECTED,
                         actionlib.GoalStatus.LOST):
                if state == actionlib.GoalStatus.ABORTED and self.finish_near_goal(
                        name, x, y, yaw):
                    return 'guarded_yaw_refinement'
                distance = math.hypot(px-x, py-y)
                heading = math.atan2(y-py, x-px)
                if (state == actionlib.GoalStatus.ABORTED and
                        not recovered_heading and .15 < distance < 1.3 and
                        abs(angle_error(heading, current)) > .25):
                    rospy.logwarn('[sq4 nav] %s DWA stalled %.3f m from goal; '
                                  'turning safely toward route and retrying' %
                                  (name, distance))
                    self.guarded_turn(heading)
                    recovered_heading = True
                    self.client.send_goal(self.goal(x, y, yaw))
                    deadline = time.time() + self.goal_timeout
                    continue
                raise RuntimeError('%s move_base state %s' % (name, state))
            time.sleep(.2)
        self.client.cancel_goal()
        raise RuntimeError('%s move_base timeout' % name)

    def wait_for_green(self):
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
            elif state == 'yellow':
                green_count = 0
                if announced != 'yellow':
                    self.pub_voice.publish(String(data=u'识别到黄灯，继续等待'.encode('utf8')))
                    announced = 'yellow'
            else:
                green_count = 0
            time.sleep(.2)
        raise RuntimeError('no fresh visual red-to-green transition')

    def capture(self, index, name):
        message = self.frame if name in FRONT_CAMERA else self.task_frame
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
            handle.write(json.dumps({'records': self.records,
                                     'planned_count': len(self.route),
                                     'road_samples': self.road_samples,
                                     'outside_samples': self.outside_samples},
                                    ensure_ascii=False, indent=2).encode('utf8'))

    def run(self):
        self.wait_server()
        for index in range(self.start_index, min(self.end_index, len(self.route))+1):
            name, x, y, yaw = self.route[index-1]
            started = time.time()
            try:
                completion = self.navigate(name.encode('utf8'), x, y, yaw)
                self.pub_cur.publish(String(data=name.encode('utf8')))
                if name in LIGHTS:
                    self.wait_for_green()
                image_path = '' if name.startswith(u'过路') else self.capture(index, name)
                if image_path:
                    event = {'task_id': name, 'index': index, 'image': image_path,
                             'task_type': TASK_KIND[name],
                             'stamp': rospy.Time.now().to_sec()}
                    self.pub_observation.publish(String(data=json.dumps(
                        event, ensure_ascii=False).encode('utf8')))
                if not name.startswith(u'过路'):
                    self.pub_res.publish(String(data=(name+u' 已到达观察位').encode('utf8')))
                record = {'index': index, 'name': name, 'target': [x,y,yaw],
                          'elapsed_s': round(time.time()-started, 1),
                          'status': 'success', 'image': image_path,
                          'completion': completion}
                try:
                    px, py, pa = self.odom_pose()
                    record['odom'] = [round(px, 3), round(py, 3), round(pa, 3)]
                    record['xy_error_m'] = round(math.hypot(px-x, py-y), 3)
                    record['yaw_error_rad'] = round(abs(angle_error(yaw, pa)), 3)
                except RuntimeError:
                    pass
                rospy.loginfo('[sq4 nav] %d %s reached' % (index, name.encode('utf8')))
            except Exception as exc:
                self.client.cancel_goal()
                reason = str(exc)
                if isinstance(reason, str):
                    reason = reason.decode('utf8', 'replace')
                rospy.logerr('[sq4 nav] goal %d %s failed: %s' %
                             (index, name.encode('utf8'), str(exc)))
                record = {'index': index, 'name': name, 'target': [x,y,yaw],
                          'elapsed_s': round(time.time()-started, 1),
                          'status': 'failed', 'reason': reason}
                self.records.append(record)
                self.save()
                raise
            self.records.append(record)
            self.save()


if __name__ == '__main__':
    try:
        Patrol().run()
    except (RuntimeError, ValueError) as exc:
        rospy.logerr('[sq4 nav] %s' % exc)
        raise
