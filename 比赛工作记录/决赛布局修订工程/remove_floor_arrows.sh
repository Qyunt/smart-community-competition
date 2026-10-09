#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
python /tmp/sq_remove_floor_arrows.py > "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/remove_arrows.log" 2>&1
