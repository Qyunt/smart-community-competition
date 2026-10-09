#!/usr/bin/env python3
"""Generate a small, self-contained Gazebo Classic world from the rules sketch.

Coordinates are illustrative. Replace them after measuring the actual venue.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "worlds" / "smart_community.world"


def item(parent, tag, value=None, **attrs):
    element = ET.SubElement(parent, tag, attrs)
    if value is not None:
        element.text = str(value)
    return element


def vector(values):
    return " ".join(str(value) for value in values)


def material(visual, color):
    mat = item(visual, "material")
    item(mat, "ambient", vector((*color, 1)))
    item(mat, "diffuse", vector((*color, 1)))


def primitive(world, name, position, shape, dimensions, color, collision=True):
    model = item(world, "model", name=name)
    item(model, "static", "true")
    item(model, "pose", vector((*position, 0, 0, 0)))
    link = item(model, "link", name="body")
    if collision:
        coll = item(link, "collision", name="collision")
        geometry(coll, shape, dimensions)
    visual = item(link, "visual", name="visual")
    geometry(visual, shape, dimensions)
    material(visual, color)


def geometry(parent, shape, dimensions):
    geom = item(parent, "geometry")
    part = item(geom, shape)
    if shape == "box":
        item(part, "size", vector(dimensions))
    elif shape == "cylinder":
        item(part, "radius", dimensions[0])
        item(part, "length", dimensions[1])
    elif shape == "sphere":
        item(part, "radius", dimensions[0])


def box(world, name, x, y, z, sx, sy, sz, color, collision=True):
    primitive(world, name, (x, y, z), "box", (sx, sy, sz), color, collision)


def cylinder(world, name, x, y, z, radius, length, color, collision=True):
    primitive(world, name, (x, y, z), "cylinder", (radius, length), color, collision)


def sphere(world, name, x, y, z, radius, color, collision=False):
    primitive(world, name, (x, y, z), "sphere", (radius,), color, collision)


def main():
    sdf = ET.Element("sdf", version="1.6")
    world = item(sdf, "world", name="smart_community")
    item(world, "gravity", "0 0 -9.8")
    physics = item(world, "physics", type="ode")
    item(physics, "max_step_size", "0.001")
    item(physics, "real_time_update_rate", "1000")
    scene = item(world, "scene")
    item(scene, "ambient", "0.65 0.65 0.65 1")
    item(scene, "background", "0.85 0.9 0.95 1")
    sun = item(world, "light", name="sun", type="directional")
    item(sun, "pose", "0 0 8 0 0 0")
    item(sun, "diffuse", "0.85 0.85 0.85 1")
    item(sun, "direction", "0.3 -0.3 -1")

    # The outer boundary and tall structures are visible to Burger's 2-D lidar.
    box(world, "ground", 0, 0, -0.03, 7.1, 5.7, 0.06, (0.65, 0.67, 0.67))
    for name, x, y, sx, sy in (
        ("north_wall", 0, 2.8, 7, 0.08),
        ("south_wall", 0, -2.8, 7, 0.08),
        ("west_wall", -3.5, 0, 0.08, 5.6),
        ("east_wall", 3.5, 0, 0.08, 5.6),
    ):
        box(world, name, x, y, 0.22, sx, sy, 0.44, (0.32, 0.36, 0.39))

    # A/B/C stand by the central road; D and a small station are in the west.
    for name, x, y, sx, sy, color in (
        ("building_A", 0.05, 1.25, 0.85, 0.7, (0.55, 0.76, 0.78)),
        ("building_B", 0.05, 0.18, 0.85, 0.7, (0.55, 0.75, 0.67)),
        ("building_C", 0.05, -0.9, 0.85, 0.7, (0.69, 0.75, 0.87)),
        ("building_D", -1.78, -1.53, 1.1, 0.83, (0.78, 0.69, 0.57)),
        ("utility_station", -0.85, -1.65, 0.45, 0.45, (0.93, 0.67, 0.29)),
    ):
        box(world, name, x, y, 0.48, sx, sy, 0.96, color)

    # People are simple colored markers; final visual detection needs real assets.
    for i, (x, y, color) in enumerate((
        (-2.25, 1.42, (0.9, 0.22, 0.25)),
        (-1.94, 1.42, (0.2, 0.45, 0.85)),
        (-1.63, 1.42, (0.92, 0.76, 0.19)),
        (-2.16, 0.58, (0.38, 0.72, 0.39)),
        (-1.82, 0.58, (0.75, 0.29, 0.67)),
    ), 1):
        cylinder(world, "pedestrian_%d_body" % i, x, y, 0.3, 0.065, 0.6, color)
        sphere(world, "pedestrian_%d_head" % i, x, y, 0.68, 0.09, (0.9, 0.75, 0.58))

    # Three parked cars and their plates mark the eastern parking area.
    for i, (y, color) in enumerate((
        (0.83, (0.19, 0.59, 0.74)),
        (-0.1, (0.68, 0.75, 0.78)),
        (-1.03, (0.28, 0.52, 0.72)),
    ), 1):
        box(world, "car_%d_body" % i, 2.65, y, 0.19, 0.55, 0.34, 0.36, color)
        box(world, "car_%d_plate_placeholder" % i, 2.36, y, 0.2,
            0.012, 0.16, 0.08, (0.96, 0.96, 0.85), False)
        box(world, "parking_%d_line" % i, 2.64, y - 0.27, 0.004,
            0.72, 0.018, 0.008, (0.95, 0.95, 0.9), False)

    # Traffic lights by the upper start and the lower intersection.
    for name, x, y in (("north_signal", 1.42, 2.42), ("south_signal", -0.25, -2.4)):
        cylinder(world, name + "_pole", x, y, 0.5, 0.025, 1.0, (0.16, 0.17, 0.18))
        box(world, name + "_housing", x, y, 1.1,
            0.18, 0.11, 0.36, (0.1, 0.11, 0.12), False)
        for bulb, z, color in (
            ("red", 1.21, (0.93, 0.08, 0.08)),
            ("yellow", 1.1, (0.95, 0.73, 0.1)),
            ("green", 0.99, (0.08, 0.78, 0.12)),
        ):
            sphere(world, name + "_" + bulb, x, y - 0.065, z, 0.04, color)

    # Signs and lane paint are visual references; lane paint has no collision.
    cylinder(world, "direction_sign_pole", -2.87, 0.15, 0.4, 0.025, 0.8,
             (0.2, 0.2, 0.2))
    box(world, "direction_sign_panel", -2.87, 0.15, 0.9, 0.32, 0.05, 0.2,
        (0.16, 0.34, 0.73), False)
    for i in range(5):
        box(world, "north_crosswalk_%d" % (i + 1), 0.87 + i * 0.13, 2.08,
            0.004, 0.055, 0.58, 0.008, (0.95, 0.95, 0.91), False)
        box(world, "south_crosswalk_%d" % (i + 1), -0.45 + i * 0.13, -2.19,
            0.004, 0.055, 0.58, 0.008, (0.95, 0.95, 0.91), False)
    for i in range(6):
        box(world, "center_lane_mark_%d" % (i + 1), 1.32,
            -1.6 + i * 0.54, 0.004, 0.025, 0.24, 0.008,
            (0.96, 0.76, 0.17), False)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pretty_xml = minidom.parseString(ET.tostring(sdf, encoding="utf-8"))
    OUTPUT.write_bytes(pretty_xml.toprettyxml(indent="  ", encoding="utf-8"))
    print("Wrote %s (%d models)" % (OUTPUT, len(world.findall("model"))))


if __name__ == "__main__":
    main()
