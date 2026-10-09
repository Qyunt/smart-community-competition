#!/usr/bin/env bash
set -e
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
rosnode kill /sq_traffic_light_4p2 || true
tar -xzf /tmp/sq_camera_route_fix.tar.gz -C "$HOME/sq_community_ws_20261008/src/sq_community"
chmod +x "$HOME/sq_community_ws_20261008/src/sq_community/scripts/"*.py
if [ -d "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/camera_qa" ]; then
 mv "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/camera_qa" "$HOME/sq_community_ws_20261008/acceptance/final_layout_20261008/camera_qa_before_mount_fix"
fi
/bin/bash /tmp/sq_resume_20261009.sh