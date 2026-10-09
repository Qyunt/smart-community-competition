#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
trap 'result=$?; echo "INSTALL_EXIT=$result"' EXIT
echo '=== Checking Ubuntu and backing up APT configuration ==='
source /etc/os-release
test "$VERSION_CODENAME" = bionic
backup=/var/backups/codex-ros-20260917
mkdir -p "$backup"
test -e "$backup/sources.list" || cp -a /etc/apt/sources.list "$backup/sources.list"
test -e "$backup/sources.list.d" || cp -a /etc/apt/sources.list.d "$backup/sources.list.d"
wget -q --spider -T 25 https://mirrors.tuna.tsinghua.edu.cn/ubuntu/dists/bionic/Release
sed -i -e 's|http://us.archive.ubuntu.com/ubuntu/|https://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' -e 's|http://security.ubuntu.com/ubuntu|https://mirrors.tuna.tsinghua.edu.cn/ubuntu|g' /etc/apt/sources.list
echo '=== Retrieving and verifying ROS repository key ==='
keyfile=$(mktemp)
export GNUPGHOME=$(mktemp -d)
trap 'result=$?; rm -f "$keyfile"; echo "INSTALL_EXIT=$result"' EXIT
wget -q -T 30 --tries=2 -O "$keyfile" https://raw.githubusercontent.com/ros/rosdistro/master/ros.key || wget -q -T 30 --tries=2 -O "$keyfile" https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.key
gpg --with-colons --import-options show-only --dry-run --import "$keyfile" | grep -q 'fpr:::::::::C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654:'
gpg --import-options show-only --dry-run --import "$keyfile"
gpg --dearmor --batch --yes -o /usr/share/keyrings/ros-archive-keyring.gpg "$keyfile"
chmod 644 /usr/share/keyrings/ros-archive-keyring.gpg
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros/ubuntu/ bionic main' > /etc/apt/sources.list.d/ros-latest.list
echo '=== Updating APT indexes ==='
apt-get -o Acquire::Retries=3 -o Acquire::https::Timeout=45 update
echo '=== Installing ROS Melodic desktop-full and build tools ==='
apt-get -y -o Acquire::Retries=3 -o Acquire::https::Timeout=45 install ros-melodic-desktop-full python-rosdep python-rosinstall python-rosinstall-generator python-wstool build-essential
echo '=== Preparing rosdep configuration ==='
mkdir -p /etc/ros/rosdep/sources.list.d
if [ -e /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    cp -an /etc/ros/rosdep/sources.list.d/20-default.list "$backup/20-default.list"
fi
cat > /etc/ros/rosdep/sources.list.d/20-default.list <<'EOF'
yaml https://mirrors.tuna.tsinghua.edu.cn/rosdistro/rosdep/osx-homebrew.yaml osx
yaml https://mirrors.tuna.tsinghua.edu.cn/rosdistro/rosdep/base.yaml
yaml https://mirrors.tuna.tsinghua.edu.cn/rosdistro/rosdep/python.yaml
yaml https://mirrors.tuna.tsinghua.edu.cn/rosdistro/rosdep/ruby.yaml
EOF
echo '=== Package installation finished ==='
dpkg-query -W ros-melodic-desktop-full ros-melodic-roslaunch ros-melodic-rviz ros-melodic-gazebo-ros python-rosdep
df -h /
