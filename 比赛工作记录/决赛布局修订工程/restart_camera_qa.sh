#!/usr/bin/env bash
set -e
kill -TERM 10631 10572 2>/dev/null || true
/bin/bash /tmp/sq_restart_final_scene.sh
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
export PYTHONPATH="$HOME/sq_community_ws_20261008/src/sq_community/scripts:$PYTHONPATH"
python - <<'PY'
import rospy
from sensor_msgs.msg import Image
rospy.init_node('sq_wait_final_scene',anonymous=True)
rospy.wait_for_message('/task_camera/image_raw',Image,timeout=120)
PY
python /tmp/sq_final_camera_qa.py > "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/camera_qa.log" 2>&1