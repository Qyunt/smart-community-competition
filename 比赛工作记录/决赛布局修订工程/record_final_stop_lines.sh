#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
python /tmp/sq_record_final_stop_lines.py > "$HOME/sq_community_ws_20261008/acceptance/patrol_20261008_final05/stop_line_recorder.log" 2>&1
