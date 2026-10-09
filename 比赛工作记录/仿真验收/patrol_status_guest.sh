#!/usr/bin/env bash
exec > /tmp/sq_patrol_status.txt 2>&1
task_run="$HOME/sq_community_ws_20261008/acceptance/${1:-patrol_20261008_01}"
cat "$task_run/status.txt"
tail -n 12 "$task_run/patrol.log"
if [ -f "$task_run/summary.json" ]; then cat "$task_run/summary.json"; fi
python - "$task_run/report.json" <<'PY'
from __future__ import print_function
import json,os,sys
if os.path.isfile(sys.argv[1]):
    r=json.load(open(sys.argv[1]))
    print('PROGRESS=%d/%d' % (len(r['records']),r['planned_count']))
    if r['records']: print(json.dumps(r['records'][-1],ensure_ascii=False).encode('utf8'))
PY
