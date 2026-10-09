#!/usr/bin/env bash
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
task_run="$task_ws/acceptance/patrol_20261009_final_segment"
mkdir "$task_run"
mkdir "$task_run/frames"
exec > "$task_run/runner.log" 2>&1
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
if rosnode list | grep -E '^/sq_patrol' >/dev/null; then echo 'Patrol active';exit 42;fi
echo RUNNING > "$task_run/status.txt"
rosrun sq_community sq_signal_vision_4p2.py _min_brightness_upper:=90 > "$task_run/signal_vision.log" 2>&1 &
task_signal_pid=$!
trap 'kill -INT "$task_signal_pid" 2>/dev/null || true' EXIT
sleep 2
set +e
rosrun sq_community sq_patrol_4p2.py _end_index:=4 _report_file:="$task_run/report.json" _capture_dir:="$task_run/frames" > "$task_run/patrol.log" 2>&1
task_result=$?
set -e
echo "PROCESS_EXIT=$task_result" > "$task_run/status.txt"
echo FINISHED >> "$task_run/status.txt"
python - "$task_run" <<'PY'
import json,sys
root=sys.argv[1];r=json.load(open(root+'/report.json'))
result={'success':len(r['records'])==4 and all(x['status']=='success' for x in r['records']),'scope':'first four goals of final 41-goal route; not a full-run claim','successful':sum(x['status']=='success' for x in r['records']),'outside_samples':r['outside_samples'],'records':r['records']}
json.dump(result,open(root+'/summary.json','w'),indent=2)
PY
if [ "$task_result" -ne 0 ]; then exit "$task_result";fi
python - <<'PY'
import rospy,rosnode,math
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState,GetModelState
from tf.transformations import quaternion_from_euler
rospy.init_node('sq_reset_after_segment_test',anonymous=True)
if any(x.startswith('/sq_patrol') for x in rosnode.get_node_names()):raise RuntimeError('Patrol still active')
s=ModelState();s.model_name='sq_mecanum_334';s.reference_frame='world';s.pose.position.x=1.8;s.pose.position.y=1.8
s.pose.position.z=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)('sq_mecanum_334','world').pose.position.z
q=quaternion_from_euler(0,0,math.pi);s.pose.orientation.x=q[0];s.pose.orientation.y=q[1];s.pose.orientation.z=q[2];s.pose.orientation.w=q[3]
r=rospy.ServiceProxy('/gazebo/set_model_state',SetModelState)(s)
if not r.success:raise RuntimeError(r.status_message)
print('TEST_COMPLETE_ROBOT_RESET_TO_START')
PY