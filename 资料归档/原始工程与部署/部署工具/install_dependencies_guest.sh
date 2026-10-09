#!/usr/bin/env bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
exec > /tmp/sq_dependency_install.log 2>&1
for task_attempt in $(seq 1 120); do
  if ! fuser /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/lib/apt/lists/lock >/dev/null 2>&1; then
    break
  fi
  if [ "$task_attempt" = 1 ]; then echo 'Waiting for the existing system package update to finish.'; fi
  sleep 2
done
apt-get install -y ros-melodic-dwa-local-planner
echo 'DEPENDENCIES_COMPLETE'
