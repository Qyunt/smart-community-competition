#!/usr/bin/env python
from __future__ import print_function
import json,math,os,time
import rospy
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from tf.transformations import euler_from_quaternion

root=os.path.expanduser('~/sq_community_ws_20261008/acceptance/patrol_20261008_final05')
rospy.init_node('sq_stop_line_acceptance',anonymous=True)
data={'odom':None,'light':'unknown','command':Twist()}
def update(key,msg): data[key]=msg.data if key=='light' else msg
subs=[rospy.Subscriber('/odom',Odometry,lambda m:update('odom',m),queue_size=1),
      rospy.Subscriber('/sq/traffic_light/state',String,lambda m:update('light',m),queue_size=1),
      rospy.Subscriber('/cmd_vel',Twist,lambda m:update('command',m),queue_size=1)]
stream=open(os.path.join(root,'stop_line_samples.jsonl'),'ab',0)
deadline=time.time()+1800
while time.time()<deadline and not rospy.is_shutdown():
    msg=data['odom']
    if msg is not None:
        p,q=msg.pose.pose.position,msg.pose.pose.orientation
        yaw=euler_from_quaternion([q.x,q.y,q.z,q.w])[2]
        ex=abs(math.cos(yaw))*.167+abs(math.sin(yaw))*.1515
        ey=abs(math.sin(yaw))*.167+abs(math.cos(yaw))*.1515
        lines=[]
        if p.x-ex<=.508 and p.x+ex>=.492 and p.y+ey>=1.5 and p.y-ey<=2.1: lines.append('upper')
        if p.y-ey<=-.842 and p.y+ey>=-.858 and p.x+ex>=-.3 and p.x-ex<=.3: lines.append('lower')
        cmd=data['command']
        moving=abs(cmd.linear.x)+abs(cmd.linear.y)+abs(cmd.angular.z)>1e-3
        if lines:
            row={'sim_time':rospy.Time.now().to_sec(),'pose':[p.x,p.y,yaw],
                 'lines':lines,'light':data['light'],'moving':moving,
                 'source':'acceptance-only simulator light state; never supplied to patrol'}
            stream.write(json.dumps(row).encode('utf8')+b'\n')
    if os.path.isfile(os.path.join(root,'status.txt')) and 'FINISHED' in open(os.path.join(root,'status.txt')).read(): break
    time.sleep(.1)
stream.close()
