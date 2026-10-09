#!/usr/bin/env bash
set -eo pipefail
task_ws="$HOME/sq_community_ws_20261008"
task_out="$task_ws/acceptance/final_layout_20261008"
mkdir -p "$task_out"
exec > "$task_out/install.log" 2>&1
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
if rosnode list | grep -E '^/sq_patrol' >/dev/null; then echo 'Patrol still active'; exit 42; fi
if [ -f "$task_out/source_before.tar.gz" ]; then echo 'Already installed; refusing to replace backup';exit 43;fi
tar -czf "$task_out/source_before.tar.gz" -C "$task_ws/src" sq_community
python - <<'PY'
import os,signal,subprocess,time
for line in subprocess.check_output(['ps','-eo','pid=,args=']).splitlines():
    fields=line.strip().split(None,1)
    if len(fields)!=2:continue
    pid=int(fields[0]);cmd=fields[1]
    if 'roslaunch sq_community sq_community_4p2.launch' in cmd or cmd=='gzclient':
        print('Stopping prior scene process',pid,cmd)
        os.kill(pid,signal.SIGINT)
time.sleep(5)
PY
tar -xzf /tmp/sq_final_layout_patch.tar.gz -C "$task_ws/src/sq_community"
chmod +x "$task_ws/src/sq_community/scripts/"sq_*4p2.py
python -m py_compile "$task_ws/src/sq_community/scripts/sq_patrol_4p2.py" "$task_ws/src/sq_community/scripts/sq_patrol_nav_4p2.py" "$task_ws/src/sq_community/scripts/sq_task_plan_4p2.py" "$task_ws/src/sq_community/scripts/sq_signal_vision_4p2.py"
python3 "$task_ws/src/sq_community/tools/verify_scene_4p2.py"
python3 "$task_ws/src/sq_community/tools/verify_map_4p2.py"
cd "$task_ws"
catkin_make -j2 -l2
echo INSTALL_COMPLETE
source "$task_ws/software_render_env.sh"
export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"
nohup roslaunch sq_community sq_community_4p2.launch > "$task_out/scene.log" 2>&1 < /dev/null &
echo $! > "$task_out/scene.pid"
echo SCENE_STARTED
