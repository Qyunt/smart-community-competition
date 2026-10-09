#!/usr/bin/env bash
set -e
task_pid_file="$HOME/sq_community_ws_20261008/acceptance/launch.pid"
if [ -f "$task_pid_file" ]; then
  task_pid=$(cat "$task_pid_file")
  if [ -r "/proc/$task_pid/cmdline" ] && tr '\0' ' ' < "/proc/$task_pid/cmdline" | grep -q 'roslaunch.*sq_autonomous_4p2.launch'; then
    kill -INT "$task_pid"
    for attempt in $(seq 1 20); do
      if ! kill -0 "$task_pid" 2>/dev/null; then break; fi
      sleep 1
    done
  fi
fi
