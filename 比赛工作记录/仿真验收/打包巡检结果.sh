#!/usr/bin/env bash
set -e
task_ws="$HOME/sq_community_ws_20261008"
task_root="$task_ws/acceptance"
tar -czf /tmp/sq_patrol_acceptance_20261008.tar.gz -C "$task_root" \
 patrol_20261008_01 patrol_20261008_02 patrol_20261008_03 \
 signal_fix_20261008_backup stop_line_fix_20261008_backup \
 return_to_start.log stop_line_fix_install.log stop_line_test_setup.log
 tar -czf /tmp/sq_repaired_source_20261008.tar.gz -C "$task_ws/src/sq_community" \
 scripts/sq_signal_vision_4p2.py scripts/sq_patrol_4p2.py \
 tools/gen_scene_4p2.py route/task_points_4p2.csv route/sq_route_patrol_4p2.csv \
 docs/scene_manifest_4p2.json launch