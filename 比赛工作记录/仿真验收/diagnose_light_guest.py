#!/usr/bin/env python
from __future__ import print_function
import json,os,sys,time
import rospy,cv2
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from std_msgs.msg import String
sys.path.insert(0,os.path.expanduser('~/sq_community_ws_20261008/src/sq_community/scripts'))
from sq_signal_vision_4p2 import classify
root=os.path.expanduser('~/sq_community_ws_20261008/acceptance/patrol_20261008_01')
rospy.init_node('sq_light_failure_diagnosis',anonymous=True)
bridge=CvBridge()
frames=[]
for i in range(8):
    frame=rospy.wait_for_message('/camera/rgb/image_raw',Image,timeout=20)
    image=bridge.imgmsg_to_cv2(frame,'bgr8')
    state,scores=classify(image,'TL_UP_WAIT')
    age=(rospy.Time.now()-frame.header.stamp).to_sec()
    row={'state':state,'scores':scores,'image_age_sim_s':age,'wall_time':time.time(),'image_stamp':frame.header.stamp.to_sec()}
    frames.append(row)
    if i in (0,7): cv2.imwrite(os.path.join(root,'light_failure_%d.jpg'%i),image)
    time.sleep(1)
odom=rospy.wait_for_message('/odom',Odometry,timeout=20)
result={'pose':[odom.pose.pose.position.x,odom.pose.pose.position.y],'frames':frames}
with open(os.path.join(root,'light_diagnosis.json'),'w') as f: json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
