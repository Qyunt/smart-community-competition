#!/usr/bin/env python
import os,time,json,rospy,cv2
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
rospy.init_node('sq_front_view_capture',anonymous=True)
frames=[]
def on_image(m):
    frames[:]=[m]
sub=rospy.Subscriber('/camera/rgb/image_raw',Image,on_image,queue_size=1)
deadline=time.time()+15
while time.time()<deadline:
    if frames and (rospy.Time.now()-frames[0].header.stamp).to_sec()<.5: break
    time.sleep(.1)
if not frames: raise RuntimeError('No camera frames')
root=os.path.expanduser('~/sq_community_ws_20261008/acceptance/patrol_20261008_02')
cv2.imwrite(os.path.join(root,'front_view.jpg'),CvBridge().imgmsg_to_cv2(frames[0],'bgr8'))
