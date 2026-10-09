#!/usr/bin/env bash
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
exec > "$task_ws/acceptance/final_layout_20261008/final_delivery.log" 2>&1
tar -xzf /tmp/sq_source_final_install.tar.gz -C "$task_ws/src/sq_community"
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
chmod +x "$task_ws/src/sq_community/scripts/"*.py
python -m py_compile "$task_ws/src/sq_community/scripts/"sq_*4p2.py "$task_ws/src/sq_community/scripts/traffic_light_controller_4p2.py"
python3 "$task_ws/src/sq_community/tools/verify_scene_4p2.py"
python3 "$task_ws/src/sq_community/tools/verify_map_4p2.py"
/bin/bash /tmp/sq_final_layout_probe.sh
rosnode list
pgrep -a gzclient || true
loginctl list-sessions --no-legend || true
echo FINAL_SOURCE_INSTALLED