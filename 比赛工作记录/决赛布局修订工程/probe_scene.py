#!/usr/bin/env python
from __future__ import print_function
import os,json,time,math
import rospy
from gazebo_msgs.srv import GetModelState,GetWorldProperties
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from cv_bridge import CvBridge
import cv2
from sq_task_plan_4p2 import TASK_KIND

rospy.init_node('sq_final_layout_probe',anonymous=True)
root=os.path.expanduser('~/sq_community_ws_20261008')
out=root+'/acceptance/final_layout_20261008'
rospy.wait_for_service('/gazebo/get_model_state',timeout=30)
get=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
m=json.load(open(root+'/src/sq_community/docs/scene_manifest_4p2.json'))
diffs=[]
for obj in m['objects']:
    r=get(obj['id'],'world')
    expected=obj.get('model_origin_physical_xy_m',obj['physical_xy_m'])
    err=math.hypot(r.pose.position.x+2.1-expected[0],r.pose.position.y+2.1-expected[1])
    if not r.success or err>.005:diffs.append({'id':obj['id'],'error_m':err,'success':r.success})
messages={}
subs=[rospy.Subscriber(t,Image,lambda msg,t=t:messages.update({t:msg}),queue_size=1) for t in ('/camera/rgb/image_raw','/task_camera/image_raw')]
deadline=time.time()+30
while time.time()<deadline and len(messages)<2:time.sleep(.2)
time.sleep(2)
frames={}
bridge=CvBridge()
for t,msg in messages.items():
    image=bridge.imgmsg_to_cv2(msg,'bgr8');name='front_start.jpg' if '/rgb/' in t else 'task_start.jpg'
    cv2.imwrite(out+'/'+name,image)
    frames[t]={'shape':[msg.width,msg.height],'age_sim_s':(rospy.Time.now()-msg.header.stamp).to_sec(),'mean':float(image.mean()),'std':float(image.std())}
odom=rospy.wait_for_message('/odom',Odometry,timeout=10)
result={'scene_anchor_mismatches':diffs,'task_contract_count':len(TASK_KIND),'camera_frames':frames,
        'robot_start_odom':[odom.pose.pose.position.x,odom.pose.pose.position.y],
        'models':len(rospy.ServiceProxy('/gazebo/get_world_properties',GetWorldProperties)().model_names)}
json.dump(result,open(out+'/probe.json','w'),indent=2)
print(json.dumps(result,indent=2))
if diffs or len(frames)!=2:raise RuntimeError('Scene or camera probe failed')
