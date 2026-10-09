#!/usr/bin/env bash
set -uo pipefail
echo '=== OS ==='
lsb_release -ds
id -un
echo '=== REQUIRED PACKAGES ==='
dpkg-query -W -f='${Package}\t${Status}\t${Version}\n' ros-melodic-desktop-full ros-melodic-turtlesim python-rosdep python-rosinstall python-rosinstall-generator python-wstool build-essential
echo '=== APT SOURCE AND KEY ==='
cat /etc/apt/sources.list.d/ros-latest.list
gpg --with-colons --import-options show-only --dry-run --import /usr/share/keyrings/ros-archive-keyring.gpg 2>/dev/null | grep -E '^(pub|fpr):'
echo '=== ROSDEP SOURCES AND CACHE ==='
cat /etc/ros/rosdep/sources.list.d/20-default.list
find "$HOME/.ros/rosdep/sources.cache" -maxdepth 1 -type f -printf '%f %TY-%Tm-%Td %TH:%TM\n' 2>/dev/null
echo '=== PERSISTENT SHELL SETTINGS ==='
grep -nE '(^source .*ros|^source .*catkin|^export ROSDISTRO_INDEX_URL)' "$HOME/.bashrc"
echo '=== FRESH INTERACTIVE SHELL CHECK ==='
bash -ic 'echo ROS_DISTRO=$ROS_DISTRO; rosversion -d; command -v roscore rosrun; rospack find turtlesim; rosdep resolve roscpp --rosdistro melodic' </dev/null
echo '=== CURRENT ROS/TURTLESIM PROCESSES ==='
ps -eo pid,comm,args | grep -E '(roscore|rosmaster|turtlesim_node|turtle_teleop_key)' | grep -v grep || true
echo '=== ROS RUN LOG EVIDENCE ==='
find "$HOME/.ros/log" -maxdepth 2 -type f -printf '%P\n' 2>/dev/null | head -n 70
echo '=== LOG FILES MENTIONING TURTLESIM ==='
grep -rIlE '(turtlesim_node|turtle_teleop_key|/turtle1/pose)' "$HOME/.ros/log" "$HOME/roscore-verification.log" "$HOME/ros-topic-verification.log" 2>/dev/null || true
echo '=== SAVED HISTORY COUNTS (NO COMMAND CONTENTS) ==='
for name in roscore turtlesim_node turtle_teleop_key; do
    count=$(grep -cF "$name" "$HOME/.bash_history" 2>/dev/null || true)
    echo "$name: ${count:-0}"
done
echo '=== EXISTING TEST LOG ==='
tail -n 18 "$HOME/roscore-verification.log" 2>/dev/null
echo '=== WORKSPACE ==='
test -f "$HOME/catkin_ws/devel/setup.bash" && echo CATKIN_WORKSPACE_BUILT
echo 'AUDIT_FINISHED'
