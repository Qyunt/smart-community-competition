#!/usr/bin/env python3
"""Rasterize the actual 4.2 m SDF collision geometry into a ROS PGM map.

This is a deterministic geometric map for navigation development. It must be
validated against live laser observations before being treated as a localized
SLAM result.
"""

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


PKG = Path(__file__).resolve().parents[1]
WORLD = PKG / "worlds/sq_community_4p2.world"
OUT_PGM = PKG / "maps/sq_community_4p2.pgm"
OUT_YAML = PKG / "maps/sq_community_4p2.yaml"
OUT_MANIFEST = PKG / "docs/map_manifest_4p2.json"
RES = 0.05
ORIGIN = -2.3
SIDE = 4.6
WIDTH = HEIGHT = round(SIDE / RES)


def parse_pose(element):
    values = [float(v) for v in (element.findtext("pose") or "0 0 0 0 0 0").split()]
    if len(values) != 6:
        raise ValueError("SDF pose requires six values")
    return values


def shape_from_collision(model, collision):
    mx, my, mz, _, _, myaw = parse_pose(model)
    cx, cy, cz, _, _, cyaw = parse_pose(collision)
    x = mx + cx * math.cos(myaw) - cy * math.sin(myaw)
    y = my + cx * math.sin(myaw) + cy * math.cos(myaw)
    z = mz + cz
    geom = collision.find("geometry")
    box = geom.find("box")
    if box is not None:
        sx, sy, sz = [float(v) for v in box.findtext("size").split()]
        if z + sz / 2 <= .035:
            return None
        return {"model": model.get("name"), "kind": "box", "x": x, "y": y,
                "sx": sx, "sy": sy, "yaw": myaw + cyaw, "top": z + sz / 2}
    cylinder = geom.find("cylinder")
    if cylinder is not None:
        radius = float(cylinder.findtext("radius"))
        length = float(cylinder.findtext("length"))
        if z + length / 2 <= .035:
            return None
        return {"model": model.get("name"), "kind": "cylinder", "x": x,
                "y": y, "radius": radius, "top": z + length / 2}
    raise ValueError("unsupported collision geometry: " + model.get("name"))


def hit(shape, x, y):
    dx, dy = x - shape["x"], y - shape["y"]
    pad = RES / 2
    if shape["kind"] == "cylinder":
        return dx * dx + dy * dy <= (shape["radius"] + pad) ** 2
    yaw = shape["yaw"]
    lx = dx * math.cos(yaw) + dy * math.sin(yaw)
    ly = -dx * math.sin(yaw) + dy * math.cos(yaw)
    return abs(lx) <= shape["sx"] / 2 + pad and abs(ly) <= shape["sy"] / 2 + pad


def main():
    root = ET.parse(WORLD).getroot()
    shapes = []
    for model in root.findall(".//world/model"):
        for collision in model.findall(".//link/collision"):
            shape = shape_from_collision(model, collision)
            if shape is not None:
                shapes.append(shape)
    assert shapes and any(s["model"] == "sq4_boundary_north" for s in shapes)

    # PGM is top row first; ROS map origin is the lower-left image pixel.
    data = bytearray()
    occupied = 0
    for row in range(HEIGHT - 1, -1, -1):
        y = ORIGIN + (row + .5) * RES
        for col in range(WIDTH):
            x = ORIGIN + (col + .5) * RES
            blocked = abs(x) >= 2.1 or abs(y) >= 2.1 or any(hit(s, x, y) for s in shapes)
            data.append(0 if blocked else 254)
            occupied += bool(blocked)
    OUT_PGM.write_bytes(("P5\n%d %d\n255\n" % (WIDTH, HEIGHT)).encode("ascii") + data)
    OUT_YAML.write_text(
        "image: sq_community_4p2.pgm\nresolution: 0.05\norigin: [-2.3, -2.3, 0.0]\n"
        "negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n", encoding="utf-8")
    OUT_MANIFEST.write_text(json.dumps({
        "source": "SDF collision geometry of sq_community_4p2.world",
        "status": "geometric prior; live localization and drive test required",
        "resolution_m": RES, "origin_xy_m": [ORIGIN, ORIGIN],
        "size_pixels": [WIDTH, HEIGHT], "collision_shapes": len(shapes),
        "occupied_pixels": occupied, "free_pixels": WIDTH * HEIGHT - occupied,
        "collision_models": sorted({s["model"] for s in shapes}),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("map", WIDTH, "x", HEIGHT, "shapes", len(shapes),
          "occupied", occupied, "free", WIDTH * HEIGHT - occupied)


if __name__ == "__main__":
    main()
