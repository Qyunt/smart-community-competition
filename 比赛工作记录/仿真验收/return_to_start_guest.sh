#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
python /tmp/sq_return_start.py > "$HOME/sq_community_ws_20261008/acceptance/return_to_start.log" 2>&1
