#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
export PYTHONPATH="$HOME/sq_community_ws_20261008/src/sq_community/scripts:$PYTHONPATH"
python /tmp/sq_final_layout_probe.py > "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/probe.log" 2>&1
