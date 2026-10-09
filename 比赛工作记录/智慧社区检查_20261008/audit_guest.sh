#!/usr/bin/env bash
set -e
task_ws="$HOME/sq_community_ws_20261008"
task_out="$task_ws/acceptance/audit_20261008"
mkdir -p "$task_out"
exec > "$task_out/audit.txt" 2>&1
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
echo '=== ENVIRONMENT ==='
date -Is
free -m
df -h "$HOME"
ps -eo pid,pcpu,pmem,etimes,comm,args --sort=-pcpu | head -n 18
echo '=== DEPENDENCIES ==='
for pkg in gmapping amcl move_base dwa_local_planner cv_bridge gazebo_ros xacro; do
  rospack find "$pkg" || true
done
command -v spd-say || true
python3 - <<'PY'
import importlib.util
for name in ['easyocr','ultralytics','torch','cv2','numpy','PIL']:
    try:
        spec=importlib.util.find_spec(name)
        print(name, 'PRESENT' if spec else 'MISSING')
    except Exception as exc:
        print(name,str(exc))
PY
echo '=== LAUNCH SCRIPTS ==='
for task_script in "$task_ws"/start_*.sh "$task_ws/software_render_env.sh"; do
  echo "FILE=$task_script"
  cat "$task_script"
done
echo '=== ASSET AND SOURCE HASHES ==='
find "$task_ws/src/sq_community" -type f \( -name '*.py' -o -name '*.launch' -o -name '*.xacro' -o -name '*.world' -o -name '*.pgm' -o -name '*.yaml' -o -name '*evidence.json' \) -print0 | sort -z | xargs -0 sha256sum > "$task_out/source_hashes.txt"
echo '=== SAVED ACCEPTANCE FILES ==='
find "$task_ws/acceptance" -maxdepth 2 -type f -printf '%P %s bytes\n'
for task_report in /tmp/sq4_patrol_4p2.json /tmp/sq4_patrol_nav.json /tmp/sq4_plate_results.jsonl; do
  if [ -f "$task_report" ]; then
    echo "FILE=$task_report"
    tail -n 15 "$task_report"
  else echo "NOT_FOUND=$task_report"; fi
done
echo '=== LIVE ROS ==='
if rosnode list >/dev/null 2>&1; then
  rosnode list
  python /tmp/sq_audit_live.py
else
  echo 'ROS_MASTER_NOT_RUNNING'
fi
echo '=== OCR SERVICE PROBES ==='
python3 - <<'PY'
import urllib.request
for url in ['http://127.0.0.1:8765/health','http://192.168.80.1:8765/health']:
    try:
        r=urllib.request.urlopen(url,timeout=2)
        print(url,r.status,r.read(300).decode('utf-8','replace'))
    except Exception as exc:
        print(url,str(exc))
PY
echo 'AUDIT_FINISHED'
tar -czf /tmp/sq_audit_results.tar.gz -C "$task_out" .
