#!/usr/bin/env bash
exec > /tmp/sq_update_progress.txt 2>&1
date -Is
ps -eo pid,ppid,etimes,comm,args | grep -E 'apt|dpkg|unattended|dependency_guest|postinst|systemctl' | grep -v grep
echo '=== RECENT PACKAGE CONFIGURATION ==='
tail -n 20 /var/log/dpkg.log
echo '=== UNATTENDED UPDATE ==='
tail -n 15 /var/log/unattended-upgrades/unattended-upgrades.log
echo '=== ROS PACKAGE SOURCES ==='
cat /etc/apt/sources.list.d/ros-latest.list
