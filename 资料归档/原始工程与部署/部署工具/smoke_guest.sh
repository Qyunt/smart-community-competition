#!/usr/bin/env bash
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
mkdir -p "$task_ws/acceptance"
exec > "$task_ws/acceptance/smoke.txt" 2>&1
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH="$task_ws/src/sq_community/models:${GAZEBO_MODEL_PATH:-}"
export GAZEBO_MODEL_DATABASE_URI=''
task_session_pid=$(pgrep -u "$(id -u)" -x gnome-session-b | head -n 1)
if [ -n "$task_session_pid" ]; then
  export DISPLAY=$(tr '\0' '\n' < "/proc/$task_session_pid/environ" | sed -n 's/^DISPLAY=//p' | head -n 1)
  export XAUTHORITY=$(tr '\0' '\n' < "/proc/$task_session_pid/environ" | sed -n 's/^XAUTHORITY=//p' | head -n 1)
fi
echo "DISPLAY=${DISPLAY:-}"
echo "XAUTHORITY=${XAUTHORITY:-}"
if rosnode list >/dev/null 2>&1; then
  echo 'An existing ROS master is active; refusing to interfere.'
  exit 30
fi
roslaunch sq_community sq_autonomous_4p2.launch start_patrol:=false enable_ocr:=false enable_voice:=false gui:=true > "$task_ws/acceptance/launch.log" 2>&1 &
task_launch_pid=$!
echo "$task_launch_pid" > "$task_ws/acceptance/launch.pid"
for attempt in $(seq 1 45); do
  if rosservice list 2>/dev/null | grep -q '/gazebo/get_model_state'; then break; fi
  if ! kill -0 "$task_launch_pid" 2>/dev/null; then
    echo 'Launch exited early.'
    tail -n 60 "$task_ws/acceptance/launch.log"
    exit 31
  fi
  sleep 2
done
echo '=== NODES ==='
rosnode list
echo '=== TOPICS ==='
rostopic list
echo '=== SENSOR MESSAGES ==='
python - "$task_ws/acceptance/sensors.json" <<'PY'
from __future__ import print_function
import json, sys, time
import rospy
from sensor_msgs.msg import Image, LaserScan
from nav_msgs.msg import Odometry, OccupancyGrid
from std_msgs.msg import String
rospy.init_node('sq_install_sensor_check', anonymous=True)
rows = {}
def record(topic, msg):
    row = {'received': True, 'wall_time': time.time()}
    if isinstance(msg, Image):
        row.update(width=msg.width, height=msg.height, encoding=msg.encoding, data_bytes=len(msg.data))
    elif isinstance(msg, LaserScan):
        row.update(rays=len(msg.ranges), frame=msg.header.frame_id)
    elif isinstance(msg, Odometry):
        row.update(x=msg.pose.pose.position.x, y=msg.pose.pose.position.y, frame=msg.header.frame_id)
    elif isinstance(msg, OccupancyGrid):
        row.update(width=msg.info.width, height=msg.info.height, resolution=msg.info.resolution)
    elif isinstance(msg, String):
        row.update(value=msg.data)
    rows[topic] = row
topics = [('/scan', LaserScan), ('/odom', Odometry),
          ('/camera/rgb/image_raw', Image), ('/camera/depth/image_raw', Image),
          ('/task_camera/image_raw', Image), ('/map', OccupancyGrid),
          ('/sq/vision/traffic_light', String)]
subs = [rospy.Subscriber(t, cls, lambda m, t=t: record(t, m), queue_size=1) for t,cls in topics]
deadline=time.time()+90
while time.time()<deadline and len(rows)<len(topics):
    time.sleep(.2)
result = {'topics': rows, 'missing': [t for t,_ in topics if t not in rows]}
with open(sys.argv[1], 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
if result['missing']:
    sys.exit(32)
if not rows['/scan']['rays'] or any(not rows[t]['data_bytes'] for t,cls in topics if cls is Image):
    sys.exit(33)
PY
echo '=== GAZEBO ROBOT ==='
rosservice call /gazebo/get_model_state "model_name: 'sq_mecanum_334'
relative_entity_name: 'world'"
echo '=== NAVIGATION ==='
rosnode ping -c 1 /move_base
rosnode ping -c 1 /amcl
timeout 120 python - <<'PY'
import actionlib, rospy
from move_base_msgs.msg import MoveBaseAction
rospy.init_node('sq_install_navigation_check', anonymous=True)
client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
if not client.wait_for_server(rospy.Duration(10)):
    raise RuntimeError('move_base action server is unavailable')
print('MOVE_BASE_ACTION_READY')
PY
echo 'SMOKE_PASS'
echo 'Scene remains running for inspection. Stop only this session using the saved launch PID.'
