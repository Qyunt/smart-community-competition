#!/usr/bin/env bash
exec > /tmp/sq_camera_diag.txt 2>&1
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
ps -eo pid,ppid,etime,args | grep -E 'sq_finish|python -|xacro|robot_state|gzserver|sq_final_camera' | grep -v grep
rosnode list
tail -n 25 "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/camera_refresh.log"
tail -n 12 "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/camera_qa.log"