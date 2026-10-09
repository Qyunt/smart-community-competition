#!/usr/bin/env bash
set -e
task_pkg="$HOME/sq_community_ws_20261008/src/sq_community"
task_backup="$HOME/sq_community_ws_20261008/acceptance/signal_fix_20261008_backup"
if [ ! -e "$task_backup/sq_patrol_4p2.py" ]; then
  cp -p "$task_pkg/scripts/sq_patrol_4p2.py" "$task_backup/"
fi
cp /tmp/sq_patrol_fixed.py "$task_pkg/scripts/sq_patrol_4p2.py"
chmod u+x "$task_pkg/scripts/sq_patrol_4p2.py"
python -m py_compile "$task_pkg/scripts/sq_patrol_4p2.py"
