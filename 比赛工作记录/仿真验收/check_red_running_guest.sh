#!/usr/bin/env bash
exec > /tmp/sq_red_running_check.txt 2>&1
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
rosservice call /gazebo/pause_physics
rosservice call /gazebo/get_model_state "model_name: 'sq_mecanum_334'
relative_entity_name: 'world'"
rostopic echo -n 1 /sq/patrol/current
rostopic echo -n 1 /sq/traffic_light/state
tail -n 8 "$HOME/sq_community_ws_20261008/acceptance/patrol_20261008_02/events.jsonl"
