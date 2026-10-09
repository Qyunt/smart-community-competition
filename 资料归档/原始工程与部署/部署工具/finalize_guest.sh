#!/usr/bin/env bash
set -e
task_ws="$HOME/sq_community_ws_20261008"
cp /tmp/sq_stop_preview.sh "$task_ws/stop_preview.sh"
for task_mode in mapping navigation; do
  if [ "$task_mode" = mapping ]; then task_launch=sq_mapping_run_4p2.launch; else task_launch=sq_autonomous_nav_4p2.launch; fi
  cat > "$task_ws/start_${task_mode}.sh" <<SH
#!/usr/bin/env bash
set -e
source /opt/ros/melodic/setup.bash
source "$task_ws/devel/setup.bash"
export TURTLEBOT3_MODEL=waffle
export GAZEBO_MODEL_PATH="$task_ws/src/sq_community/models:\${GAZEBO_MODEL_PATH:-}"
roslaunch sq_community $task_launch "\$@"
SH
done
chmod u+x "$task_ws"/start_*.sh "$task_ws/stop_preview.sh"
task_desktop=$(xdg-user-dir DESKTOP)
if [ -d "$task_desktop" ]; then
  for task_mode in scene patrol; do
    if [ "$task_mode" = scene ]; then task_label='智慧社区-查看场景'; else task_label='智慧社区-里程计巡检'; fi
    task_shortcut="$task_desktop/sq_community_${task_mode}_20261008.desktop"
    if [ ! -e "$task_shortcut" ]; then
      cat > "$task_shortcut" <<SH
[Desktop Entry]
Type=Application
Name=$task_label
Comment=4.2m 智慧社区仿真工程
Exec=gnome-terminal -- bash -lc '$task_ws/start_${task_mode}.sh; exec bash'
Icon=applications-engineering
Terminal=false
Categories=Education;Science;
SH
      chmod u+x "$task_shortcut"
      gio set "$task_shortcut" metadata::trusted true 2>/dev/null || true
    fi
  done
fi
echo 'FINALIZE_COMPLETE'
