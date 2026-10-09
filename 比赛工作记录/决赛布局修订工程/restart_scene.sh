#!/usr/bin/env bash
set -e
task_ws="$HOME/sq_community_ws_20261008"
task_out="$task_ws/acceptance/final_layout_20261008"
exec > "$task_out/restart.log" 2>&1
python - <<'PY'
import os,signal,subprocess,time
pids=[]
for line in subprocess.check_output(['ps','-eo','pid=,args=']).splitlines():
    fields=line.strip().split(None,1)
    if len(fields)==2 and 'roslaunch sq_community sq_community_4p2.launch' in fields[1]:
        pid=int(fields[0]);pids.append(pid);os.kill(pid,signal.SIGINT)
for attempt in range(40):
    active=[]
    for pid in pids:
        try:
            row=open('/proc/%d/stat'%pid).read().split()
            if row[2]!='Z':active.append(pid)
        except IOError:pass
    if not active:break
    time.sleep(1)
if active:raise RuntimeError('Previous scene has not stopped')
PY
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
source "$task_ws/software_render_env.sh"
export DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority"
nohup roslaunch sq_community sq_community_4p2.launch > "$task_out/scene_retry.log" 2>&1 < /dev/null &
echo $! > "$task_out/scene.pid"
echo RESTARTED