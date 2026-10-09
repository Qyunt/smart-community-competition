#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
python /tmp/sq_record_stop_lines_fixed.py > "$HOME/sq_community_ws_20261008/acceptance/patrol_20261008_03/stop_line_recorder.log" 2>&1
