#!/usr/bin/env bash
exec > /tmp/sq_gui_diagnosis.txt 2>&1
date -Is
ps -eo pid,ppid,etimes,comm,args | grep -E 'roslaunch|gzserver|gzclient|gnome-session' | grep -v grep
echo '=== GUI LOGS ==='
task_log_dir=$(readlink -f "$HOME/.ros/log/latest")
echo "$task_log_dir"
for task_log in "$task_log_dir"/gazebo_gui*.log; do
  [ -f "$task_log" ] && tail -n 60 "$task_log"
done
echo '=== OGRE LOG ==='
tail -n 25 "$HOME/.gazebo/ogre.log" 2>/dev/null
echo '=== SOFTWARE DRIVER ==='
find /usr/lib -name swrast_dri.so -print 2>/dev/null
task_session_pid=$(pgrep -u "$(id -u)" -x gnome-session-b | head -n 1)
if [ -n "$task_session_pid" ]; then
  tr '\0' '\n' < "/proc/$task_session_pid/environ" | grep -E '^(DISPLAY|XAUTHORITY)='
fi
