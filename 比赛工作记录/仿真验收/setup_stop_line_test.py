#!/usr/bin/env python
from __future__ import print_function
import math,os,time,json
import rospy
from gazebo_msgs.srv import GetModelState,SetModelState
from gazebo_msgs.msg import ModelState
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_srvs.srv import Empty
rospy.init_node('sq_stop_line_test_setup',anonymous=True)
if any('/sq_patrol' in x for x in __import__('rosnode').get_node_names()): raise RuntimeError('Patrol still active')
state=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)('sq_mecanum_334','world')
if not state.success: raise RuntimeError(state.status_message)
rospy.ServiceProxy('/gazebo/pause_physics',Empty)()
model=ModelState();model.model_name='sq_mecanum_334';model.reference_frame='world'
model.pose=state.pose;model.pose.position.x=0;model.pose.position.y=0
model.pose.orientation.x=0;model.pose.orientation.y=0
model.pose.orientation.z=math.sin(-math.pi/4);model.pose.orientation.w=math.cos(-math.pi/4)
try:
    result=rospy.ServiceProxy('/gazebo/set_model_state',SetModelState)(model)
    if not result.success:raise RuntimeError(result.status_message)
finally:rospy.ServiceProxy('/gazebo/unpause_physics',Empty)()
pub=rospy.Publisher('/cmd_vel',Twist,queue_size=1)
time.sleep(.5)
for i in range(3):pub.publish(Twist());time.sleep(.1)
odom=rospy.wait_for_message('/odom',Odometry,timeout=10)
p=odom.pose.pose.position
print(json.dumps({'test_setup':'controlled initial pose at BINS for local regression; not a complete competition lap','odom':[p.x,p.y,p.z]}))
if math.hypot(p.x,p.y)>.05:raise RuntimeError('Odometry did not follow test initialization')