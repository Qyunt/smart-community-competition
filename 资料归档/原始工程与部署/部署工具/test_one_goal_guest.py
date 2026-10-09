#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import json, math, os, time
import actionlib, cv2, rospy
from actionlib_msgs.msg import GoalStatus
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image

rospy.init_node('sq_install_one_goal_check', anonymous=True)
root=os.path.expanduser('~/sq_community_ws_20261008/acceptance')
start=rospy.wait_for_message('/odom', Odometry, timeout=30)
client=actionlib.SimpleActionClient('move_base', MoveBaseAction)
if not client.wait_for_server(rospy.Duration(10)):
    raise RuntimeError('move_base action server unavailable')
goal=MoveBaseGoal()
goal.target_pose.header.frame_id='map'
goal.target_pose.header.stamp=rospy.Time.now()
goal.target_pose.pose.position.x=1.0
goal.target_pose.pose.position.y=1.8
goal.target_pose.pose.orientation.z=1.0
goal.target_pose.pose.orientation.w=0.0
started=time.time()
client.send_goal(goal)
state=client.get_state()
while time.time()-started<120:
    state=client.get_state()
    if state in (GoalStatus.SUCCEEDED,GoalStatus.ABORTED,GoalStatus.REJECTED,GoalStatus.LOST):
        break
    time.sleep(.2)
if state!=GoalStatus.SUCCEEDED:
    client.cancel_goal()
    pub=rospy.Publisher('/cmd_vel',Twist,queue_size=1)
    time.sleep(.3)
    pub.publish(Twist())
end=rospy.wait_for_message('/odom',Odometry,timeout=15)
result={'goal':[1.0,1.8,math.pi],'action_state':state,
        'action_text':client.get_goal_status_text(),
        'success':state==GoalStatus.SUCCEEDED,'elapsed_wall_s':round(time.time()-started,2),
        'odom_start':[start.pose.pose.position.x,start.pose.pose.position.y],
        'odom_end':[end.pose.pose.position.x,end.pose.pose.position.y]}
bridge=CvBridge()
for topic,name in [('/camera/rgb/image_raw','front_camera.png'),('/task_camera/image_raw','task_camera.png')]:
    try:
        frame=rospy.wait_for_message(topic,Image,timeout=20)
        cv2.imwrite(os.path.join(root,name),bridge.imgmsg_to_cv2(frame,'bgr8'))
    except Exception as exc:
        result[name]=str(exc)
with open(os.path.join(root,'one_goal.json'),'w') as f:
    json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
