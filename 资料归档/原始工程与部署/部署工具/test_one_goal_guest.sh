#!/usr/bin/env bash
set -e
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
python /tmp/sq_test_one_goal.py > "$HOME/sq_community_ws_20261008/acceptance/one_goal.log" 2>&1
