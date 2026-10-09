#!/usr/bin/env python3
"""Check geometric map and the 334 x 303 mm robot at planned goals."""

import csv
import json
import math
from pathlib import Path


PKG = Path(__file__).resolve().parents[1]
metadata = json.loads((PKG / "docs/map_manifest_4p2.json").read_text(encoding="utf-8"))
pgm = (PKG / "maps/sq_community_4p2.pgm").read_bytes()
magic, dims, max_value, pixels = pgm.split(b"\n", 3)
assert magic == b"P5" and max_value == b"255"
width, height = map(int, dims.split())
assert [width, height] == metadata["size_pixels"]
assert len(pixels) == width * height
resolution = metadata["resolution_m"]
ox, oy = metadata["origin_xy_m"]
occupied = []
for row in range(height):
    for col in range(width):
        if pixels[row * width + col] == 0:
            occupied.append((ox + (col + .5) * resolution,
                             oy + (height - row - .5) * resolution))
assert len(occupied) == metadata["occupied_pixels"]

with (PKG / "route/sq_route_patrol_4p2.csv").open(encoding="utf-8", newline="") as stream:
    goals = list(csv.DictReader(line for line in stream if not line.startswith("#")))
for goal in goals:
    x, y, yaw = float(goal["x"]), float(goal["y"]), float(goal["yaw"])
    near = ((px - x, py - y) for px, py in occupied
            if abs(px - x) <= .31 and abs(py - y) <= .31)
    for dx, dy in near:
        local_x = dx * math.cos(yaw) + dy * math.sin(yaw)
        local_y = -dx * math.sin(yaw) + dy * math.cos(yaw)
        assert abs(local_x) > .167 or abs(local_y) > .1515, (goal["名称"], x, y, dx, dy)

print("OK: map", width, "x", height, ";", len(occupied),
      "occupied pixels;", len(goals), "goals clear for 0.334 x 0.303 m body")
