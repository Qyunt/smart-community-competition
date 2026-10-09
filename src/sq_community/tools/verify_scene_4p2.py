#!/usr/bin/env python3
"""Static validation for the 4.2 m engineering scene."""

from collections import deque
import csv
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


PKG = Path(__file__).resolve().parents[1]
manifest = json.loads((PKG / "docs/scene_manifest_4p2.json").read_text(encoding="utf-8"))
world = ET.parse(PKG / "worlds/sq_community_4p2.world")
assert world.getroot().tag == "sdf"
model_names = {m.get("name") for m in world.findall(".//world/model")}
model_names.update(n.text for n in world.findall(".//world/include/name"))
for light in ("sq4_tl_upper", "sq4_tl_lower"):
    assert light in model_names
    assert not any(light + "_" + color in model_names for color in ("red", "green", "yellow"))
assert len([n for n in model_names if n.startswith("sq4_tl_")]) == 2
assert manifest["arena_m"] == [4.2, 4.2]
assert manifest["road_width_m"] == .6
assert manifest["robot_target_m"] == [.334, .303]

roads = set()
for entry in manifest["roads_cells_half_open"]:
    x0, x1, y0, y1 = entry["bounds"]
    assert 0 <= x0 < x1 <= 21 and 0 <= y0 < y1 <= 21
    assert x1 - x0 == 3 or y1 - y0 == 3
    roads.update((x, y) for x in range(x0, x1) for y in range(y0, y1))

start = {(x, y) for x in range(18, 21) for y in range(18, 21)}
traversable = roads | start
stack = deque([next(iter(traversable))])
seen = {stack[0]}
while stack:
    x, y = stack.popleft()
    for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if neighbor in traversable and neighbor not in seen:
            seen.add(neighbor)
            stack.append(neighbor)
assert seen == traversable, "road network has disconnected cells"

tasks = manifest["task_points"]
assert len(tasks) >= 15
for task in tasks:
    gx, gy = task["grid_xy"]
    assert (gx, gy) in traversable, task["id"]
    wx, wy = task["world_xy_m"]
    assert abs(wx - (-2 + .2 * gx)) < 1e-6
    assert abs(wy - (-2 + .2 * gy)) < 1e-6
    assert task["target"] in model_names, task["id"]

upper = next(t for t in tasks if t["id"] == "TL_UP_WAIT")
lower = next(t for t in tasks if t["id"] == "TL_LOW_WAIT")
# The 334 mm body must remain before each red-light stop line.
assert upper["world_xy_m"][0] + 2.1 - .167 > manifest["stop_lines_physical_m"]["upper_x"]
assert lower["world_xy_m"][1] + 2.1 - .167 > manifest["stop_lines_physical_m"]["lower_y"]

with (PKG / "route/task_points_4p2.csv").open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == len(tasks)
assert {r["task_id"] for r in rows} == {t["id"] for t in tasks}
task_ids = [r["task_id"] for r in rows]
assert task_ids.index("BUILDING_C") < task_ids.index("TL_LOW_WAIT")
assert task_ids.index("BINS_LOW") < task_ids.index("BINS_HIGH")

# The planned patrol file must use the new metre-scale coordinates and remain
# on the road centre lines. This is a geometric check, not a move_base test.
with (PKG / "route/sq_route_patrol_4p2.csv").open(encoding="utf-8", newline="") as f:
    patrol_rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
assert [r["名称"] for r in patrol_rows if not r["名称"].startswith("过路")] == task_ids
centre = ({(x, 19) for x in range(1, 20)} | {(1, y) for y in range(1, 20)} |
          {(x, 13) for x in range(1, 11)} | {(10, y) for y in range(1, 14)} |
          {(x, 1) for x in range(1, 17)} | {(16, y) for y in range(1, 20)})
prev = (19, 19)
for row in patrol_rows:
    x = (float(row["x"]) + 2.0) / .2
    y = (float(row["y"]) + 2.0) / .2
    node = (round(x), round(y))
    assert abs(x - node[0]) < 1e-5 and abs(y - node[1]) < 1e-5, row["名称"]
    assert node in centre, row["名称"]
    assert node[0] == prev[0] or node[1] == prev[1], row["名称"]
    assert abs(node[0] - prev[0]) + abs(node[1] - prev[1]) <= 18, row["名称"]
    if node[0] == prev[0]:
        assert all((node[0], yy) in centre for yy in range(min(node[1], prev[1]), max(node[1], prev[1]) + 1))
    else:
        assert all((xx, node[1]) in centre for xx in range(min(node[0], prev[0]), max(node[0], prev[0]) + 1))
    prev = node

light_model = ET.parse(PKG / "models/sq_traffic_light_4p2/model.sdf")
light_links = {link.get("name") for link in light_model.findall(".//model/link")}
assert {"front_red", "front_yellow", "front_green"} <= light_links
assert all(float(link.findtext("pose").split()[2]) == 0 for link in
           light_model.findall(".//model/link") if link.get("name").startswith("front_"))
for path in (PKG / "launch/sq_community_4p2.launch", PKG / "urdf/sq_mecanum_334.urdf.xacro"):
    ET.parse(path)
robot_xml = (PKG / "urdf/sq_mecanum_334.urdf.xacro").read_text(encoding="ascii")
assert robot_xml.count("<xacro:sq_mecanum_wheel id=") == 4
assert "libgazebo_ros_planar_move.so" in robot_xml

for label, cols, fires in (("A", 3, 3), ("B", 3, 5), ("C", 3, 2), ("D", 3, 0)):
    building = next(m for m in world.findall(".//world/model") if m.get("name") == "sq4_building_" + label)
    names = [link.get("name") for link in building.findall("link")]
    assert len([name for name in names if name.startswith("window_f") and name.endswith("_glass")]) == 3 * cols
    assert len([name for name in names if name.startswith("side_north_") and name.endswith("_glass")]) == 6
    assert len([name for name in names if name.startswith("side_south_") and name.endswith("_glass")]) == 6
    assert len([name for name in names if name.startswith("rear_f") and name.endswith("_glass")]) == 3 * cols
    scripts = [entry.text for entry in building.findall(".//script/name")]
    assert scripts.count("SQ_win_fire") == fires
    assert scripts.count("SQ_win_hot") == (1 if label == "D" else 0)

textures = PKG / "models/sq_competition_assets/materials/textures"
assets = manifest["asset_manifest"]
for stem in assets["materials"]:
    assert (textures / (stem + ".png")).exists(), stem
plates = {p["kind"]: p["number"] for p in assets["plates"]}
assert set(plates) == {"blue", "yellow", "green", "white"}
for kind in ("blue", "yellow"):
    assert re.fullmatch(r"[\u4e00-\u9fff][A-Z]·[A-HJ-NP-Z0-9]{5}", plates[kind])
    assert sum(c.isalpha() for c in plates[kind].split("·", 1)[1]) <= 2
assert re.fullmatch(r"[\u4e00-\u9fff][A-Z]·[DF][0-9]{5}", plates["green"])
assert re.fullmatch(r"[\u4e00-\u9fff][A-Z]·[0-9]{4}警", plates["white"])
assert len([o for o in manifest["objects"] if o["type"] == "person"]) == 18
assert len([o for o in manifest["objects"] if o["type"] == "car_plate_board"]) == 3
assert len([o for o in manifest["objects"] if o["type"] == "traffic_light"]) == 2

print("OK: connected", len(traversable), "cells;", len(tasks), "task points;",
      len(patrol_rows), "planned patrol goals;", len(manifest["objects"]), "objects;",
      len(assets["materials"]), "asset textures")
