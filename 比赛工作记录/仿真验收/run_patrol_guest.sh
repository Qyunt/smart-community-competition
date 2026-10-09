#!/usr/bin/env bash
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
task_run="$task_ws/acceptance/${1:-patrol_20261008_01}"
if [ -e "$task_run" ]; then echo 'Result directory already exists'; exit 41; fi
mkdir -p "$task_run/frames"
exec > "$task_run/runner.log" 2>&1
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
if rosnode list | grep -E '^/sq_patrol(_4p2|_nav_4p2)?$' >/dev/null; then
  echo 'Another patrol controller is active'; exit 42
fi
echo 'RUNNING' > "$task_run/status.txt"
rosrun sq_community sq_signal_vision_4p2.py _min_brightness_upper:=90 > "$task_run/signal_vision.log" 2>&1 &
task_signal_pid=$!
echo "$task_signal_pid" > "$task_run/signal.pid"
trap 'kill -INT "$task_signal_pid" 2>/dev/null || true' EXIT
sleep 2
set +e
rosrun sq_community sq_patrol_4p2.py \
  _report_file:="$task_run/report.json" \
  _capture_dir:="$task_run/frames" > "$task_run/patrol.log" 2>&1
task_result=$?
set -e
echo "PROCESS_EXIT=$task_result" > "$task_run/status.txt"
python - "$task_run" <<'PY'
from __future__ import print_function
import json,os,sys
root=sys.argv[1]
p=os.path.join(root,'report.json')
if not os.path.isfile(p):
    result={'success':False,'reason':'Patrol report not created'}
else:
    r=json.load(open(p))
    records=r['records']
    result={'success':len(records)==r['planned_count'] and all(x['status']=='success' for x in records),
            'planned':r['planned_count'],'recorded':len(records),
            'successful':sum(x['status']=='success' for x in records),
            'failed':[x for x in records if x['status']!='success'],
            'saved_images':sum(bool(x.get('image')) for x in records),
            'road_samples':r['road_samples'],'outside_samples':r['outside_samples']}
with open(os.path.join(root,'summary.json'),'w') as f: json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
PY
echo 'FINISHED' >> "$task_run/status.txt"
