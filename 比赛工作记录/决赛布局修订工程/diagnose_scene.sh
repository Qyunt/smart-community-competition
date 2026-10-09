#!/usr/bin/env bash
exec > /tmp/sq_layout_diag.txt 2>&1
ps -eo pid,ppid,etime,comm,args | grep -E 'gzserver|gzclient|roslaunch|rosmaster|traffic_light' | grep -v grep
ss -ltnp | grep -E '11345|11311'
find "$HOME/.ros/log" -name 'gazebo-1.log' -mmin -15 -exec tail -n 30 {} \;
find "$HOME/.gazebo" -maxdepth 2 -name '*.log' -mmin -15 -exec tail -n 20 {} \;