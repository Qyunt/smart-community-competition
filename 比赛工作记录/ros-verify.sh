#!/usr/bin/env bash
set -Eeuo pipefail
set +u
source /opt/ros/melodic/setup.bash
source "$HOME/catkin_ws/devel/setup.bash"
set -u
export ROS_MASTER_URI=http://127.0.0.1:11319
export ROS_HOSTNAME=127.0.0.1
echo '=== Versions and dependencies ==='
rosversion -d
rosversion roscpp
rosdep resolve roscpp --rosdistro melodic
command -v roscore rviz gazebo catkin_make
echo '=== Starting isolated ROS master for a real topic exchange ==='
roscore -p 11319 > "$HOME/roscore-verification.log" 2>&1 &
master_pid=$!
pub_pid=''
cleanup() {
    result=$?
    if [ -n "$pub_pid" ]; then kill -INT "$pub_pid" 2>/dev/null || true; fi
    kill -INT "$master_pid" 2>/dev/null || true
    wait "$master_pid" 2>/dev/null || true
    echo "VERIFY_EXIT=$result"
}
trap cleanup EXIT
ready=0
for i in $(seq 1 30); do
    if rosnode list >/dev/null 2>&1; then ready=1; break; fi
    sleep 1
done
test "$ready" = 1
rosnode list
rostopic pub -r 2 /codex_install_check std_msgs/String 'data: ROS_Melodic_OK' > "$HOME/ros-topic-verification.log" 2>&1 &
pub_pid=$!
received=$(timeout 20 rostopic echo -n 1 /codex_install_check)
echo "$received"
echo "$received" | grep -q ROS_Melodic_OK
echo '=== Installation and pub/sub verification passed ==='
