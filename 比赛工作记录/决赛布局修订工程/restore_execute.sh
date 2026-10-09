#!/usr/bin/env bash
set -e
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
chmod +x "$HOME/sq_community_ws_20261008/src/sq_community/scripts/"*.py
if ! rosnode list | grep -E '^/sq_traffic_light_4p2$' >/dev/null; then
  nohup rosrun sq_community traffic_light_controller_4p2.py __name:=sq_traffic_light_4p2 > "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/signal_resume.log" 2>&1 < /dev/null &
fi