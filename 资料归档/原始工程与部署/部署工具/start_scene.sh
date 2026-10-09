#!/usr/bin/env bash
set -e
source "/home/qyunt/sq_community_ws_20261008/software_render_env.sh"
task_ws="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH="$task_ws/src/sq_community/models:${GAZEBO_MODEL_PATH:-}"
roslaunch sq_community sq_community_4p2.launch "$@"
