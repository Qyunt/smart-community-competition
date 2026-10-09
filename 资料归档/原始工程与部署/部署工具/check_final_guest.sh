#!/usr/bin/env bash
set -e
exec > /tmp/sq_final_check.txt 2>&1
task_ws="$HOME/sq_community_ws_20261008"
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
rospack find sq_community
rospack find dwa_local_planner
for file in "$task_ws"/start_*.sh "$task_ws/stop_preview.sh"; do
  bash -n "$file"
  echo "SCRIPT_OK=$file"
done
grep 'INSTALL_EXIT=0' "$HOME/sq_community_deploy_20261008.log"
grep 'MOVE_BASE_ACTION_READY\|SMOKE_PASS' "$task_ws/acceptance/smoke.txt"
python - "$task_ws/acceptance/one_goal.json" <<'PY'
import json,sys
result=json.load(open(sys.argv[1]))
assert result['success'] and result['action_state']==3
print('ONE_GOAL_PASS')
PY
ls -l "$task_ws/handover/"
ls -l "$(xdg-user-dir DESKTOP)"/sq_community_*_20261008.desktop
if pgrep -u "$(id -u)" -x gzserver >/dev/null; then
  echo 'PREVIEW_STILL_RUNNING'
  exit 40
fi
echo 'PREVIEW_STOPPED'
echo 'FINAL_CHECK_PASS'
