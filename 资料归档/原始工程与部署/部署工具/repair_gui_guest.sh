#!/usr/bin/env bash
set -e
task_ws="$HOME/sq_community_ws_20261008"
task_backup="$task_ws/acceptance/gui_fix_20261008_backup"
mkdir -p "$task_backup"
cp /tmp/sq_software_render_env.sh "$task_ws/software_render_env.sh"
for task_script in "$task_ws"/start_*.sh; do
  if ! grep -q 'source .*software_render_env.sh' "$task_script"; then
    cp -p "$task_script" "$task_backup/$(basename "$task_script")"
    python3 - "$task_script" "$task_ws/software_render_env.sh" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
text=p.read_text()
text=text.replace('set -e\n','set -e\nsource "'+sys.argv[2]+'"\n',1)
p.write_text(text)
PY
  fi
  bash -n "$task_script"
done
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
source "$task_ws/software_render_env.sh"
export GAZEBO_MODEL_PATH="$task_ws/src/sq_community/models:${GAZEBO_MODEL_PATH:-}"
task_session_pid=$(pgrep -u "$(id -u)" -x gnome-session-b | head -n 1)
export DISPLAY=$(tr '\0' '\n' < "/proc/$task_session_pid/environ" | sed -n 's/^DISPLAY=//p' | head -n 1)
export XAUTHORITY=$(tr '\0' '\n' < "/proc/$task_session_pid/environ" | sed -n 's/^XAUTHORITY=//p' | head -n 1)
if pgrep -u "$(id -u)" -x gzclient >/dev/null; then
  echo 'GUI_ALREADY_RUNNING'
  exit 31
fi
if ! pgrep -u "$(id -u)" -x gzserver >/dev/null; then
  echo 'No running Gazebo server; launch the corrected start_scene.sh first.'
  exit 32
fi
nohup gzclient > "$task_ws/acceptance/gui_software.log" 2>&1 < /dev/null &
echo "$!" > "$task_ws/acceptance/gui_software.pid"
echo 'SOFTWARE_GUI_STARTED'
