#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
task_run="${1:-patrol_20261008_01}"
python /tmp/sq_record_patrol.py "$task_run" > "$HOME/sq_community_ws_20261008/acceptance/$task_run/recorder.log" 2>&1
