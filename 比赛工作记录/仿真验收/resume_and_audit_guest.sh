#!/usr/bin/env bash
source /opt/ros/melodic/setup.bash
source "$HOME/sq_community_ws_20261008/devel/setup.bash"
rosservice call /gazebo/unpause_physics
python - <<'PY' > /tmp/sq_light_timeline.txt
import os
p=os.path.expanduser('~/.ros/log/latest/rosout.log')
lines=[s for s in open(p) if '[sq4 lights]' in s]
print(''.join(lines[-28:]))
PY
