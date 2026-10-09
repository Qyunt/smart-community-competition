#!/usr/bin/env bash
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
task_out="$task_ws/acceptance/final_layout_20261008"
exec > "$task_out/camera_refresh.log" 2>&1
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
if rosnode list | grep -E '^/sq_patrol' >/dev/null; then echo 'Patrol active';exit 42;fi
tar -xzf /tmp/sq_final_layout_final.tar.gz -C "$task_ws/src/sq_community"
python -m py_compile "$task_ws/src/sq_community/scripts/"sq_*4p2.py
python3 "$task_ws/src/sq_community/tools/verify_scene_4p2.py"
python3 "$task_ws/src/sq_community/tools/verify_map_4p2.py"
python - <<'PY'
import rospy,rosnode,subprocess
from gazebo_msgs.srv import DeleteModel
rospy.init_node('sq_refresh_camera_mount',anonymous=True)
description=subprocess.check_output(['/opt/ros/melodic/lib/xacro/xacro',__import__('os').path.expanduser('~/sq_community_ws_20261008/src/sq_community/urdf/sq_mecanum_334.urdf.xacro')])
rospy.set_param('/robot_description',description)
result=rospy.ServiceProxy('/gazebo/delete_model',DeleteModel)('sq_mecanum_334')
if not result.success:raise RuntimeError(result.status_message)
rosnode.kill_nodes(['/robot_state_publisher'])
PY
sleep 2
nohup rosrun robot_state_publisher robot_state_publisher > "$task_out/robot_state.log" 2>&1 < /dev/null &
rosrun gazebo_ros spawn_model -urdf -model sq_mecanum_334 -x 1.8 -y 1.8 -z 0.01 -Y 3.14159265 -param robot_description
sleep 3
export PYTHONPATH="$task_ws/src/sq_community/scripts:$PYTHONPATH"
python /tmp/sq_final_camera_qa.py > "$task_out/camera_qa.log" 2>&1
echo FINAL_REVISION_READY
