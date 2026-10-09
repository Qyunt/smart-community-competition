#!/usr/bin/env bash
exec > /tmp/sq_patrol_discovery.txt 2>&1
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
echo '=== PROCESSES ==='
ps -eo pid,ppid,etimes,comm,args | grep -E 'roslaunch|gzserver|gzclient|sq_patrol|sq_signal' | grep -v grep
echo '=== NODES ==='
rosnode list
echo '=== COMMAND PUBLISHERS ==='
rostopic info /cmd_vel
echo '=== POSE AND SIMULATION RATE ==='
python - <<'PY'
from __future__ import print_function
import json,time,rospy
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
rospy.init_node('sq_patrol_precheck',anonymous=True)
odom=rospy.wait_for_message('/odom',Odometry,timeout=20)
first=rospy.wait_for_message('/clock',Clock,timeout=20)
start=time.time()
time.sleep(5)
last=rospy.wait_for_message('/clock',Clock,timeout=20)
p=odom.pose.pose.position
q=odom.pose.pose.orientation
print(json.dumps({'position':[p.x,p.y],'orientation':[q.x,q.y,q.z,q.w],
                  'real_time_factor':(last.clock-first.clock).to_sec()/(time.time()-start)},indent=2))
PY
