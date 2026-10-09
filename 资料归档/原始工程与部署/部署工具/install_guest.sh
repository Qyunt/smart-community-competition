#!/usr/bin/env bash
# Install the provided source into a separate workspace. Do not overwrite another workspace.
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
task_log="$HOME/sq_community_deploy_20261008.log"
exec > >(tee "$task_log") 2>&1
trap 'result=$?; echo "INSTALL_EXIT=$result"; exit "$result"' EXIT
echo "WORKSPACE=$task_ws"
echo "USER=$(id -un)"
date -Is
if [ ! -f /opt/ros/melodic/setup.bash ]; then
  echo 'ROS Melodic is missing. Install the environment before continuing.'
  exit 20
fi
if [ -e "$task_ws" ]; then
  echo 'Target already exists; refusing to overwrite it.'
  exit 21
fi
mkdir -p "$task_ws"
python3 - "$task_ws" <<'PY'
import pathlib, sys, zipfile
root = pathlib.Path(sys.argv[1]).resolve()
with zipfile.ZipFile('/tmp/smart_community_source.zip') as archive:
    for item in archive.infolist():
        target = (root / item.filename).resolve()
        if root != target and root not in target.parents:
            raise ValueError('Unsafe archive path')
    archive.extractall(str(root))
PY
source /opt/ros/melodic/setup.bash
export TURTLEBOT3_MODEL=waffle
find "$task_ws/src" -type f \( -name '*.py' -o -name '*.sh' \) -exec chmod u+x {} +
cd "$task_ws"
catkin_make -j2 -l2
source devel/setup.bash
rospack find sq_community
python3 src/sq_community/tools/verify_scene_4p2.py
python3 src/sq_community/tools/verify_map_4p2.py
python3 src/sq_community/tools/verify_props_3d.py
cat > "$task_ws/start_scene.sh" <<'SH'
#!/usr/bin/env bash
set -e
task_ws="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH="$task_ws/src/sq_community/models:${GAZEBO_MODEL_PATH:-}"
roslaunch sq_community sq_community_4p2.launch "$@"
SH
cat > "$task_ws/start_patrol.sh" <<'SH'
#!/usr/bin/env bash
set -e
task_ws="$(cd "$(dirname "$0")" && pwd)"
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH="$task_ws/src/sq_community/models:${GAZEBO_MODEL_PATH:-}"
# The external OCR model service is not part of the ZIP. Enable it explicitly after setup.
roslaunch sq_community sq_autonomous_4p2.launch enable_ocr:=false enable_voice:=false "$@"
SH
chmod u+x "$task_ws/start_scene.sh" "$task_ws/start_patrol.sh"
echo 'INSTALL_COMPLETE'
echo "Start scene: bash $task_ws/start_scene.sh"
echo "Start patrol: bash $task_ws/start_patrol.sh"
