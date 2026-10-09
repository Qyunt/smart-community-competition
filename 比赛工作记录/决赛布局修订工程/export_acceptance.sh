#!/usr/bin/env bash
set -e
cd "$HOME/sq_community_ws_20261008/acceptance"
tar --exclude='final_layout_20261008/source_before.tar.gz' -czf /tmp/sq_final_acceptance.tar.gz patrol_20261008_final05 patrol_20261009_final_segment final_layout_20261008