#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "CONFIGURE_EXIT=$?"' EXIT
echo '=== Configuring qyunt shell environment ==='
test -e "$HOME/.bashrc.before-ros-20260917" || cp -a "$HOME/.bashrc" "$HOME/.bashrc.before-ros-20260917"
grep -qxF 'source /opt/ros/melodic/setup.bash' "$HOME/.bashrc" || echo 'source /opt/ros/melodic/setup.bash' >> "$HOME/.bashrc"
grep -qxF 'export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml' "$HOME/.bashrc" || echo 'export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml' >> "$HOME/.bashrc"
export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml
echo '=== Updating dependency data for Melodic ==='
rosdep update --rosdistro melodic --include-eol-distros
set +u
source /opt/ros/melodic/setup.bash
set -u
echo '=== Creating and building catkin workspace ==='
mkdir -p "$HOME/catkin_ws/src"
cd "$HOME/catkin_ws"
catkin_make
grep -qxF 'source ~/catkin_ws/devel/setup.bash' "$HOME/.bashrc" || echo 'source ~/catkin_ws/devel/setup.bash' >> "$HOME/.bashrc"
echo '=== User configuration finished ==='
