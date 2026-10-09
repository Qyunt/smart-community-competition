#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import json, os, time
import rospy, rosgraph
from sensor_msgs.msg import Image, LaserScan
from nav_msgs.msg import Odometry, OccupancyGrid
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String

out=os.path.expanduser('~/sq_community_ws_20261008/acceptance/audit_20261008')
rospy.init_node('sq_readonly_audit', anonymous=True)
master=rosgraph.Master('/sq_readonly_audit')
result={'sample_wall_s':20,'use_sim_time':rospy.get_param('/use_sim_time',False),
        'nodes':master.getSystemState(), 'topics':master.getPublishedTopics('')}
samples={}
last={}
def observe(topic,msg):
    now=time.time()
    row=samples.setdefault(topic,{'count':0,'first_wall':now})
    row['count']+=1
    row['last_wall']=now
    stamp=msg.clock.to_sec() if isinstance(msg,Clock) else (msg.header.stamp.to_sec() if hasattr(msg,'header') else None)
    if stamp is not None:
        row.setdefault('first_stamp',stamp)
        row['last_stamp']=stamp
    if isinstance(msg,Image):
        row.update(width=msg.width,height=msg.height,encoding=msg.encoding,data_bytes=len(msg.data))
    elif isinstance(msg,LaserScan):
        row.update(rays=len(msg.ranges),frame=msg.header.frame_id)
    elif isinstance(msg,Odometry):
        row.update(x=msg.pose.pose.position.x,y=msg.pose.pose.position.y)
    elif isinstance(msg,OccupancyGrid):
        row.update(width=msg.info.width,height=msg.info.height,resolution=msg.info.resolution)
    elif isinstance(msg,String):
        row['last_value']=msg.data
    last[topic]=msg
types=[('/clock',Clock),('/scan',LaserScan),('/odom',Odometry),
       ('/camera/rgb/image_raw',Image),('/camera/depth/image_raw',Image),
       ('/task_camera/image_raw',Image),('/map',OccupancyGrid),
       ('/sq/vision/traffic_light',String),('/sq/vision/plate',String),
       ('/sq/patrol/observation',String),('/sq/patrol/result',String),('/sq/voice/last',String)]
subs=[rospy.Subscriber(t,cls,lambda m,t=t:observe(t,m),queue_size=1) for t,cls in types]
started=time.time()
while time.time()-started<20 and not rospy.is_shutdown():
    time.sleep(.1)
for t,row in samples.items():
    span=row['last_wall']-row['first_wall']
    row['received_hz_wall']=round((row['count']-1)/span,3) if span else 0
    if 'first_stamp' in row and span:
        row['sim_time_per_wall_time']=round((row['last_stamp']-row['first_stamp'])/span,4)
result['messages']=samples
result['not_observed']=[t for t,_ in types if t not in samples]
try:
    from cv_bridge import CvBridge
    import cv2
    bridge=CvBridge()
    for topic,name in [('/camera/rgb/image_raw','front_now.jpg'),('/task_camera/image_raw','task_now.jpg')]:
        if topic in last:
            frame=bridge.imgmsg_to_cv2(last[topic],'bgr8')
            cv2.imwrite(os.path.join(out,name),frame)
            result[name]={'mean_pixel':round(float(frame.mean()),2),'std_pixel':round(float(frame.std()),2)}
except Exception as exc:
    result['capture_error']=str(exc)
with open(os.path.join(out,'live.json'),'w') as f:
    json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
