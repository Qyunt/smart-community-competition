#!/usr/bin/env python
from __future__ import print_function
import os,sys,math,time,json
sys.path.insert(0,os.path.expanduser('~/sq_community_ws_20261008/src/sq_community/scripts'))
from sq_patrol_4p2 import Patrol
from geometry_msgs.msg import Twist
import rospy
patrol=Patrol()
deadline=time.time()+20
while (patrol.odom is None or patrol.scan is None) and time.time()<deadline: time.sleep(.1)
try:
    start=patrol.pose()
    if math.hypot(start[0]-.8,start[1]-1.8)>.08: raise RuntimeError('Unexpected recovery position')
    patrol.drive((.8,1.8),(1.8,1.8))
    patrol.rotate(math.pi)
    print(json.dumps({'start':start,'end':patrol.pose(),'reset':'physical odometry/LiDAR guarded drive'}))
finally:
    patrol.stop()
