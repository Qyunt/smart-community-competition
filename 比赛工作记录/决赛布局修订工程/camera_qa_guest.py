#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import os,json,time,math,sys
import rospy,rosnode,cv2
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import GetModelState,SetModelState
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from tf.transformations import quaternion_from_euler
from sq_task_plan_4p2 import FRONT_CAMERA

rospy.init_node('sq_final_camera_qa',anonymous=True)
if any(x.startswith('/sq_patrol') for x in rosnode.get_node_names()):raise RuntimeError('Controller active; refusing pose fixtures')
root=os.path.expanduser('~/sq_community_ws_20261008')
out=root+'/acceptance/final_layout_20261008/camera_qa'
if not os.path.isdir(out):os.makedirs(out)
tasks=json.load(open(root+'/src/sq_community/docs/scene_manifest_4p2.json'))['task_points']
messages={};bridge=CvBridge()
subs=[rospy.Subscriber(t,Image,lambda msg,t=t:messages.update({t:msg}),queue_size=1) for t in ('/camera/rgb/image_raw','/task_camera/image_raw')]
rospy.wait_for_service('/gazebo/get_model_state',timeout=30)
get=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
set_state=rospy.ServiceProxy('/gazebo/set_model_state',SetModelState)
original=get('sq_mecanum_334','world')
if not original.success:raise RuntimeError(original.status_message)
pub=rospy.Publisher('/cmd_vel',Twist,queue_size=1)
records=[]
def place(x,y,yaw):
    s=ModelState();s.model_name='sq_mecanum_334';s.reference_frame='world'
    s.pose.position.x=x;s.pose.position.y=y;s.pose.position.z=original.pose.position.z
    q=quaternion_from_euler(0,0,yaw)
    s.pose.orientation.x=q[0];s.pose.orientation.y=q[1];s.pose.orientation.z=q[2];s.pose.orientation.w=q[3]
    r=set_state(s)
    if not r.success:raise RuntimeError(r.status_message)
    pub.publish(Twist())
    return rospy.Time.now()
try:
    for index,t in enumerate(tasks,1):
        x,y=t['world_xy_m'];yaw=t['yaw_rad'];stamp=place(x,y,yaw)
        deadline=time.time()+20
        while time.time()<deadline:
            if len(messages)==2 and all((msg.header.stamp-stamp).to_sec()>.4 for msg in messages.values()):break
            time.sleep(.05)
        if time.time()>=deadline:raise RuntimeError('No fresh settled images for '+t['id'])
        paths={}
        for topic,msg in messages.items():
            cam='front' if '/rgb/' in topic else 'wide'
            name='%02d_%s_%s.jpg'%(index,t['id'],cam)
            if not cv2.imwrite(out+'/'+name,bridge.imgmsg_to_cv2(msg,'bgr8')):raise RuntimeError('image write failed')
            paths[cam]=name
        odom=rospy.wait_for_message('/odom',Odometry,timeout=10)
        p=odom.pose.pose.position
        primary='front' if t['id'] in FRONT_CAMERA else 'wide'
        record={'index':index,'task':t['id'],'pose':[x,y,yaw],'odom':[p.x,p.y],
                'primary_camera':primary,'images':paths,'image_setup':'independent camera framing fixture; not autonomous navigation'}
        records.append(record)
        json.dump({'records':records,'planned':len(tasks)},open(out+'/report.json','w'),indent=2)
        print('CAMERA_QA',index,t['id'],primary);sys.stdout.flush()
finally:
    place(1.8,1.8,math.pi)
    pub.publish(Twist())
print('CAMERA_QA_FINISHED')
