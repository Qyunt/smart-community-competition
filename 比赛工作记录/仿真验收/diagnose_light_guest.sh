#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
python /tmp/sq_diagnose_light.py > "$HOME/sq_community_ws_20261008/acceptance/patrol_20261008_01/light_diagnosis.log" 2>&1
