#!/usr/bin/env bash
set -e
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
python /tmp/sq_setup_stop_line_test.py > "$HOME/sq_community_ws_20261008/acceptance/stop_line_test_setup.log" 2>&1
