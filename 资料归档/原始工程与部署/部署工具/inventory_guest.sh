#!/usr/bin/env bash
# ROS Melodic environment scripts expect unset variables to expand normally.
exec > /tmp/sq_guest_inventory.txt 2>&1
echo '=== SYSTEM ==='
id
cat /etc/os-release
df -h "$HOME"
echo '=== ROS / GAZEBO ==='
ls -d /opt/ros/* 2>/dev/null
if [ -f /opt/ros/melodic/setup.bash ]; then
  source /opt/ros/melodic/setup.bash
  command -v catkin_make
  rosversion -d
  for pkg in gazebo_ros gazebo_plugins gmapping move_base amcl cv_bridge xacro; do
    rospack find "$pkg" || true
  done
fi
gazebo --version 2>/dev/null
python --version 2>&1
python3 --version 2>&1
echo '=== CURRENT WORKSPACES AND SESSION ==='
find "$HOME" -maxdepth 3 -name .catkin_workspace -print 2>/dev/null
printenv DISPLAY XAUTHORITY
ls -l "$HOME/.Xauthority" 2>/dev/null
ps -eo pid,comm,args | grep -E 'rosmaster|roslaunch|gzserver|gzclient|gnome-session' | grep -v grep
echo '=== HOST NETWORK ==='
ip -4 addr
ip route
