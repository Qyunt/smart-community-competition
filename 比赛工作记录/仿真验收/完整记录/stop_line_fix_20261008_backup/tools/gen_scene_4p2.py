#!/usr/bin/env python3
"""Generate the planned 4.2 m competition world, manifest, plan and task points.

The source diagram fixes topology, dimensions and named zones but does not
dimension every prop.  Assumed positions here are engineering placements,
recorded as such in the manifest.  The old 10.0 x 7.2 m world is untouched.
"""

import csv
import json
import math
from pathlib import Path
from xml.sax.saxutils import escape
from scene_props_3d import add_people_models, add_ebike_models, build_meshes


PKG = Path(__file__).resolve().parents[1]
CELL = 0.2
FIELD = 4.2

ROADS = [
    ("top", (0, 18, 18, 21)),
    ("west", (0, 3, 3, 18)),
    ("connector", (3, 12, 12, 15)),
    ("central", (9, 12, 3, 15)),
    ("bottom", (0, 18, 0, 3)),
    ("east", (15, 18, 3, 18)),
]
ZONES = [
    ("start_finish", (18, 21, 18, 21), (0.90, 0.57, 0.21, 1)),
    ("a_people", (3, 9, 15, 18), (0.94, 0.78, 0.42, 1)),
    ("a_street", (9, 15, 15, 18), (0.95, 0.84, 0.53, 1)),
    ("b_people", (3, 9, 8, 12), (0.96, 0.80, 0.47, 1)),
    ("building_A", (12, 15, 12, 15), (0.55, 0.82, 0.62, 1)),
    ("building_B", (12, 15, 9, 12), (0.55, 0.82, 0.62, 1)),
    ("building_C", (12, 15, 3, 9), (0.55, 0.82, 0.62, 1)),
    ("building_D", (3, 6, 3, 8), (0.55, 0.82, 0.62, 1)),
    ("station", (6, 9, 3, 8), (0.55, 0.82, 0.62, 1)),
    ("ebike_parking", (18, 21, 9, 18), (0.45, 0.71, 0.93, 1)),
    ("car_parking", (18, 21, 0, 9), (0.45, 0.71, 0.93, 1)),
]
TASKS = [
    # The first two observation points stay east/north of their stop lines.
    ("TL_UP_WAIT", 14, 19, math.pi, "sq4_tl_upper", "light_red/green/yellow", "upper signal and stop line"),
    ("PEOPLE_A", 6, 19, -math.pi / 2, "sq4_person_01", "person_01..09", "A-zone count and outsiders"),
    ("SIGN_WEST", 1, 14, 0, "sq4_sign_speed30", "sign_speed30", "road sign"),
    ("BUILDING_D", 1, 6, 0, "sq4_building_D", "win_hot", "D building heat"),
    ("PEOPLE_B", 6, 13, -math.pi / 2, "sq4_person_10", "person_10..18", "B-zone count"),
    ("BUILDING_A", 8, 13, 0, "sq4_building_A", "win_fire", "A building fires"),
    ("BINS", 10, 10, math.pi, "sq4_bin_recycle", "bin_recycle/hazard/kitchen/other", "bin state"),
    ("TL_LOW_WAIT", 10, 9, -math.pi / 2, "sq4_tl_lower", "light_red/green/yellow", "lower signal and stop line"),
    ("BUILDING_C", 10, 6, 0, "sq4_building_C", "win_fire", "C building fires"),
    ("STATION_GAUGES", 7, 1, math.pi / 2, "sq4_station", "gauge_1/2", "station readings"),
    ("CAR_1", 16, 1, 0, "sq4_car_1", "plate_blue", "car plate bay 1"),
    ("CAR_2", 16, 4, 0, "sq4_car_2", "plate_yellow", "car plate bay 2"),
    ("CAR_3", 16, 7, 0, "sq4_car_3", "plate_green", "car plate bay 3"),
    ("BUILDING_B", 16, 10, math.pi, "sq4_building_B", "win_fire", "B building fires"),
    ("EBIKES", 16, 13, 0, "sq4_ebike_01", "upright/fallen", "e-bike parking states"),
    ("RETURN", 19, 19, math.pi, "sq4_zone_start_finish", "none", "return to start/finish zone"),
]


def m(cell):
    return cell * CELL


def w(physical):
    return physical - FIELD / 2


def cell_world(index):
    return w((index + 0.5) * CELL)


def rgba(color):
    return " ".join("%.4f" % x for x in color)


def pose(x, y, z=0, yaw=0):
    return "%.4f %.4f %.4f 0 0 %.5f" % (w(x), w(y), z, yaw)


def material(color=None, script=None, old=False):
    if script:
        base = "model://sq_textures/materials" if old else "model://sq_competition_assets/materials"
        return ("<material><script><uri>%s/scripts</uri><uri>%s/textures</uri><name>%s</name></script>"
                "<ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse></material>") % (base, base, script)
    return "<material><ambient>%s</ambient><diffuse>%s</diffuse></material>" % (rgba(color), rgba(color))


def box_link(name, sx, sy, sz, color=None, script=None, old=False, collision=False, lx=0, ly=0, lz=0, lyaw=0):
    geom = "<geometry><box><size>%.4f %.4f %.4f</size></box></geometry>" % (sx, sy, sz)
    local = "<pose>%.4f %.4f %.4f 0 0 %.5f</pose>" % (lx, ly, lz, lyaw)
    col = "<collision name='%s_col'>%s%s</collision>" % (name, local, geom) if collision else ""
    return "<link name='%s'>%s<visual name='%s_vis'>%s%s%s</visual>%s</link>" % (
        name, "", name, local, geom, material(color, script, old), col)


def cylinder_link(name, radius, length, color, lx=0, ly=0, lz=0, collision=False):
    geom = "<geometry><cylinder><radius>%.4f</radius><length>%.4f</length></cylinder></geometry>" % (radius, length)
    local = "<pose>%.4f %.4f %.4f 0 0 0</pose>" % (lx, ly, lz)
    col = "<collision name='%s_col'>%s%s</collision>" % (name, local, geom) if collision else ""
    return "<link name='%s'><visual name='%s_vis'>%s%s%s</visual>%s</link>" % (
        name, name, local, geom, material(color), col)


def model(name, x, y, links, z=0, yaw=0):
    return "<model name='%s'><static>true</static><pose>%s</pose>%s</model>" % (
        escape(name), pose(x, y, z, yaw), "".join(links))


def rectangle(name, bounds, color, height=0.002, collision=False):
    x0, x1, y0, y1 = bounds
    x, y = (x0 + x1) / 2, (y0 + y1) / 2
    return model(name, x, y, [box_link("surface", x1 - x0, y1 - y0, height, color, collision=collision, lz=height / 2)])


def billboard(name, x, y, width, height, script, yaw, old=False, collision=False, thickness=0.005):
    return model(name, x, y, [box_link("panel", thickness, width, height, script=script, old=old,
                                     collision=collision, lz=height / 2)], yaw=yaw)


def add_floor_and_roads(parts):
    parts.append(model("sq4_floor", 2.1, 2.1, [box_link("floor", 4.2, 4.2, 0.03, (0.53, 0.55, 0.58, 1), collision=True, lz=-0.015)]))
    for name, bounds in ROADS:
        x0, x1, y0, y1 = bounds
        parts.append(rectangle("sq4_road_" + name, (m(x0), m(x1), m(y0), m(y1)), (0.21, 0.24, 0.29, 1), .003))
    for name, bounds, color in ZONES:
        x0, x1, y0, y1 = bounds
        parts.append(rectangle("sq4_zone_" + name, (m(x0), m(x1), m(y0), m(y1)), color, .0035))
    # Boundary walls are outside the 4.2 m driving surface, leaving exact lane widths.
    for name, x, y, sx, sy in (
        ("north", 2.1, 4.22, 4.24, .04), ("south", 2.1, -.02, 4.24, .04),
        ("west", -.02, 2.1, .04, 4.24), ("east", 4.22, 2.1, .04, 4.24),
    ):
        # Keep the wall above the robot's 0.202 m laser plane so AMCL sees
        # the same perimeter that the generated 2-D map marks occupied.
        parts.append(model("sq4_boundary_" + name, x, y, [box_link("wall", sx, sy, .26, (.30, .33, .36, 1), collision=True, lz=.13)]))


def add_markings(parts):
    # Two marked crossings remain within the 0.6 m road; marks have no collision.
    for name, cx, cy, axis in (("upper", 2.1, 3.9, "x"), ("lower", 2.1, 0.9, "y")):
        for j in range(5):
            offset = (j - 2) * .11
            if axis == "x":
                b = (cx - .29, cx + .29, cy + offset - .024, cy + offset + .024)
            else:
                b = (cx + offset - .024, cx + offset + .024, cy - .29, cy + .29)
            parts.append(rectangle("sq4_crossing_%s_%d" % (name, j), b, (.96, .96, .92, 1), .005))
    # A westbound robot stops with its front east of x=2.6; a southbound one
    # stops with its front north of y=1.25.
    parts.append(rectangle("sq4_stop_upper", (2.592, 2.608, 3.6, 4.2), (.98, .98, .96, 1), .006))
    parts.append(rectangle("sq4_stop_lower", (1.8, 2.4, 1.242, 1.258), (.98, .98, .96, 1), .006))
    # Start region outline, with no impassable divider between start and finish.
    for n, b in enumerate(((3.6, 4.2, 3.6, 3.61), (3.6, 4.2, 4.19, 4.2),
                           (3.6, 3.61, 3.6, 4.2), (4.19, 4.2, 3.6, 4.2))):
        parts.append(rectangle("sq4_start_outline_%d" % n, b, (.99, .99, .99, 1), .007))
    for j in range(3):
        y0 = j * .6
        parts.append(rectangle("sq4_car_bay_%d" % (j + 1), (3.6, 4.2, y0, y0 + .6), (.37, .65, .90, 1), .004))
        parts.append(rectangle("sq4_car_bay_line_%d" % (j + 1), (3.6, 4.2, y0, y0 + .01), (.96, .97, .97, 1), .006))


def add_people(parts, objects, style="standee"):
    add_people_models(parts, objects, style)


def add_buildings(parts, objects):
    specs = [
        ("A", 2.7, 2.7, .58, .58, .55, "west", 3, False),
        ("B", 2.7, 2.1, .58, .58, .55, "east", 5, False),
        ("C", 2.7, 1.2, .58, 1.16, .55, "west", 2, False),
        ("D", .9, 1.1, .58, .95, .55, "west", 0, True),
    ]
    for label, x, y, sx, sy, sz, face, fires, hot in specs:
        name = "sq4_building_" + label
        links = [box_link("structure", sx, sy, sz, (.69, .75, .77, 1), collision=True, lz=sz / 2)]
        # The task-facing facade has a regular three-storey window grid.
        # The coloured task windows occupy cells within that grid.
        cols = 4 if label == "C" else 3
        spacing = sy / (cols + 0.6)
        ys = [(j - (cols - 1) / 2.0) * spacing for j in range(cols)]
        zs = (.18, .315, .45)
        fire_cells = {"A": {(1, 0), (2, 1), (2, 2)},
                      "B": {(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)},
                      "C": {(1, 1), (2, 3)}, "D": set()}[label]
        assert len(fire_cells) == fires
        fx = sx / 2 + .003 if face == "east" else -sx / 2 - .003
        outward = 1 if face == "east" else -1
        links.append(box_link("nameplate", .005, .20, .045, script="SQ_bldg_" + label,
                              old=True, lx=fx + outward * .003, lz=.515))
        links.append(box_link("entry_door", .006, .115, .105, (.16, .23, .28, 1),
                              lx=fx + outward * .003, lz=.063))
        for floor, z in enumerate(zs):
            for col, yy in enumerate(ys):
                key = "window_f%d_c%d" % (floor + 1, col + 1)
                links.append(box_link(key + "_frame", .007, .100, .093,
                                      (.18, .24, .28, 1), lx=fx + outward * .002,
                                      ly=yy, lz=z))
                texture = ("SQ_win_hot" if hot and (floor, col) == (1, 1) else
                           "SQ_win_fire" if (floor, col) in fire_cells else None)
                links.append(box_link(key + "_glass", .007, .078, .072,
                                      (.31, .47, .57, 1) if texture is None else None,
                                      script=texture, old=texture is not None,
                                      lx=fx + outward * .006, ly=yy, lz=z))
        # Exposed side and rear walls also receive aligned windows.  Keep the
        # fire/heat target textures only on the task-facing facade.
        side_cols = 4 if sx > .8 else 2
        side_xs = [(j - (side_cols - 1) / 2.0) * sx / (side_cols + .6)
                   for j in range(side_cols)]
        for side, sign in (("north", 1), ("south", -1)):
            fy = sign * (sy / 2 + .003)
            for floor, z in enumerate(zs):
                for col, xx in enumerate(side_xs):
                    key = "side_%s_f%d_c%d" % (side, floor + 1, col + 1)
                    links.append(box_link(key + "_frame", .100, .007, .093,
                                          (.18, .24, .28, 1), lx=xx, ly=fy + sign * .002, lz=z))
                    links.append(box_link(key + "_glass", .078, .007, .072,
                                          (.31, .47, .57, 1), lx=xx,
                                          ly=fy + sign * .006, lz=z))
        rear_x = -fx
        rear_sign = -outward
        for floor, z in enumerate(zs):
            for col, yy in enumerate(ys):
                key = "rear_f%d_c%d" % (floor + 1, col + 1)
                links.append(box_link(key + "_frame", .007, .100, .093,
                                      (.18, .24, .28, 1), lx=rear_x + rear_sign * .002,
                                      ly=yy, lz=z))
                links.append(box_link(key + "_glass", .007, .078, .072,
                                      (.31, .47, .57, 1), lx=rear_x + rear_sign * .006,
                                      ly=yy, lz=z))
        parts.append(model(name, x, y, links))
        objects.append({"id": name, "type": "building", "label": label, "physical_xy_m": [x, y],
                        "front": face, "floor_count": 3, "window_grid": [3, cols],
                        "side_window_grid": [3, side_cols],
                        "fire_windows": fires, "fire_window_cells": sorted(list(fire_cells)),
                        "hot_window": hot, "hot_window_cell": [1, 1] if hot else None,
                        "placement": "planned_from_schematic"})


def add_station_and_bins(parts, objects):
    links = [box_link("structure", .55, .80, .47, (.68, .73, .72, 1), collision=True, lz=.235)]
    links.append(box_link("station_name", .006, .24, .09, script="SQ_station_plate", old=True,
                          lx=0, ly=-.405, lz=.34, lyaw=-math.pi / 2))
    for j, mat in enumerate(("SQ_gauge_1", "SQ_gauge_2")):
        links.append(box_link("gauge_%d" % (j + 1), .006, .12, .09, script=mat, old=True,
                              lx=(-.12 if j == 0 else .12), ly=-.409, lz=.22, lyaw=-math.pi / 2))
    parts.append(model("sq4_station", 1.5, 1.1, links))
    objects.append({"id": "sq4_station", "type": "station", "physical_xy_m": [1.5, 1.1],
                    "gauges": ["01357", "24680"], "placement": "planned_from_schematic"})
    bins = [
        ("recycle", .96, False, "none"), ("hazard", 1.16, True, "correct"),
        ("kitchen", 1.36, True, "wrong"), ("other", 1.56, False, "none"),
    ]
    for typ, x, opened, load in bins:
        name = "sq4_bin_" + typ
        links = [box_link("body", .11, .12, .17, (.26, .36, .38, 1), collision=True, lz=.085),
                 box_link("front", .003, .10, .12, script="SQ_bin_" + typ, old=True,
                          lx=.057, lz=.085)]
        if opened:
            links.append(box_link("open_lid", .10, .12, .012, (.12, .17, .18, 1),
                                  lx=.03, lz=.18, lyaw=.25))
        parts.append(model(name, x, 1.79, links))
        objects.append({"id": name, "type": "bin", "category": typ, "open": opened,
                        "load": load, "physical_xy_m": [x, 1.79], "placement": "planned_extra_task"})


def add_cars(parts, objects):
    for i, (y, style, number) in enumerate(((.3, "blue", "苏A·31682"),
                                           (.9, "yellow", "苏A·57246"),
                                           (1.5, "green", "苏A·D68125")), 1):
        name = "sq4_car_%d" % i
        rear_material = "SQ4_CarRearLarge" if style == "yellow" else "SQ4_CarRear"
        plate_z = .09 if style == "yellow" else .125
        links = [box_link("car_rear", .0005, .345, .25, script=rear_material, lz=.125),
                 box_link("plate", .0001, .095, .030, script="SQ4_Plate_" + style.title(),
                          lx=.0004, lz=plate_z)]
        # Rear image faces the road to the west.
        parts.append(model(name, 3.88, y, links, yaw=math.pi))
        objects.append({"id": name, "type": "car_plate_board", "bay": i,
                        "physical_xy_m": [3.88, y], "plate": number, "plate_style": style,
                        "vehicle_category": "large_passenger_vehicle" if style == "yellow" else "small_passenger_vehicle",
                        "source": "generated_large_vehicle_and_plate" if style == "yellow" else "supplied_car_cutout_and_generated_plate",
                        "placement": "planned_from_schematic"})


def add_ebikes(parts, objects):
    add_ebike_models(parts, objects)


def add_signs(parts, objects):
    signs = [
        ("speed30", .69, 3.52, math.pi / 2),
        ("crosswalk", 2.48, 3.42, math.pi / 2),
        ("no_straight", .70, 2.03, math.pi),
        ("turn_left", 1.73, 3.05, math.pi),
        ("no_entry", 1.73, 1.70, 0),
        ("turn_right", 3.68, 1.64, math.pi),
    ]
    for typ, x, y, yaw in signs:
        name = "sq4_sign_" + typ
        parts.append(billboard(name, x, y, .12, .12, "SQ_sign_" + typ,
                               yaw, old=True, collision=False))
        objects.append({"id": name, "type": "traffic_sign", "label": typ,
                        "physical_xy_m": [x, y], "placement": "planned_extra_task"})


def make_world(objects, people_style="standee", filename="sq_community_4p2.world"):
    parts = []
    add_floor_and_roads(parts)
    add_markings(parts)
    add_people(parts, objects, people_style)
    add_buildings(parts, objects)
    add_station_and_bins(parts, objects)
    add_cars(parts, objects)
    add_ebikes(parts, objects)
    add_signs(parts, objects)
    for name, x, y, yaw in (("sq4_tl_upper", 1.5, 3.9, 0),
                            ("sq4_tl_lower", 2.1, .9, math.pi / 2)):
        parts.append("<include><name>%s</name><pose>%s</pose><uri>model://sq_traffic_light_4p2</uri></include>" %
                     (name, pose(x, y, 0, yaw)))
        objects.append({"id": name, "type": "traffic_light", "physical_xy_m": [x, y],
                        "face": "east" if yaw == 0 else "north", "cycle_s": {"red": 10, "green": 15, "yellow": 3},
                        "placement": "planned_from_schematic", "inactive_faces": "inside_housing"})
    text = ("<?xml version='1.0' encoding='utf-8'?>\n<sdf version='1.6'>\n"
            "<world name='sq_community_4p2'>\n<include><uri>model://sun</uri></include>\n"
            "<gravity>0 0 -9.8</gravity>\n" + "\n".join(parts) + "\n</world>\n</sdf>\n")
    (PKG / "worlds" / filename).write_text(text, encoding="utf-8")
    return len(parts)


def make_light_models():
    root = PKG / "models/sq_traffic_light_4p2"
    root.mkdir(parents=True, exist_ok=True)
    (root / "model.config").write_text(
        "<model><name>sq_traffic_light_4p2</name><version>2.0</version><sdf version='1.6'>model.sdf</sdf></model>\n",
        encoding="utf-8")
    links = [box_link("housing", .05, .59, .14, (.09, .09, .10, 1), lz=.41)]
    for state in ("red", "green", "yellow"):
        # Inactive panel links sit inside the opaque housing, not below the map.
        hidden = -.05 if state != "red" else 0
        visual = box_link("face", .001, .59, .14,
                          script="SQ4_Light_" + state.title(), lx=.026, lz=.41)
        visual = visual.replace("<link name='face'>", "<link name='front_%s'><pose>%.3f 0 0 0 0 0</pose>" % (state, hidden), 1)
        links.append(visual)
    for side, yy in (("left", -.3075), ("right", .3075)):
        links.append(box_link("leg_" + side, .025, .025, .34, (.08, .08, .09, 1),
                              collision=True, ly=yy, lz=.17))
    sdf = "<?xml version='1.0'?>\n<sdf version='1.6'>%s</sdf>\n" % model("sq_traffic_light_4p2", 2.1, 2.1, links)
    (root / "model.sdf").write_text(sdf, encoding="utf-8")


def make_manifest(objects, model_count):
    asset_manifest = json.loads((PKG / "models/sq_competition_assets/asset_manifest.json").read_text(encoding="utf-8"))
    out = {
        "status": "engineered_layout_from_schematic",
        "authority": {
            "official": "rules PDF p3 for topology/orientation; training PDF pp3,5-8 for dimensions and visual tasks",
            "estimated": "all precise prop anchors, subdivisions and task waypoints, selected by engineering planning",
            "old_scene": "10.0 x 7.2 m manifest and coordinates are excluded",
        },
        "arena_m": [4.2, 4.2],
        "robot_target_m": [.334, .303],
        "robot_height_m": .222,
        "robot_ground_clearance_m": .034,
        "grid": {"count": [21, 21], "cell_m": .2, "cell_centers_world_formula": ["-2.0 + 0.2*x", "-2.0 + 0.2*y"]},
        "start_finish": {"cells_x": [18, 20], "cells_y": [18, 20], "center_world_m": [1.8, 1.8]},
        "road_width_m": .6,
        "roads_cells_half_open": [{"id": name, "bounds": bounds} for name, bounds in ROADS],
        "zones_cells_half_open": [{"id": name, "bounds": bounds} for name, bounds, _ in ZONES],
        "stop_lines_physical_m": {"upper_x": 2.6, "lower_y": 1.25},
        "traffic_cycle_s": {"red": 10, "green": 15, "yellow": 3},
        "objects": objects,
        "task_points": [
            {"id": t[0], "grid_xy": [t[1], t[2]], "world_xy_m": [round(cell_world(t[1]), 3), round(cell_world(t[2]), 3)],
             "yaw_rad": round(t[3], 5), "target": t[4], "asset": t[5], "purpose": t[6],
             "position_source": "engineered_from_schematic"}
            for t in TASKS
        ],
        "asset_manifest": asset_manifest,
        "gazebo_model_count_expected": model_count,
        "limitations": [
            "Prop anchors and counts beyond training specifications are planned placements, not official measured coordinates.",
            "The supplied map does not dimension start/finish subdivisions; both use the 0.6 m upper-right zone without a rigid divider.",
            "Yellow large-vehicle and white police plates are valid category variants; three schematic parking bays display blue, yellow and green, while white is packaged as an exchangeable asset.",
            "Default people are independent 150 x 50 x 5 mm training-reference standees. The *_standees.world file is a compatibility alias. Legacy volumetric people are not used.",
            "Electric mopeds are engineered 180 x 75 x 130 mm models; no official dimension was found. Counts 8 upright + 2 fallen in parking and 2 violations in A are demonstration choices from the rule example, not fixed competition counts.",
            "Person textures preserve the supplied training references. Identity metadata is not a recognition output; actual YOLO accuracy remains untested.",
        ],
    }
    (PKG / "docs/scene_manifest_4p2.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_config():
    config = {
        "status": "planned_engineering_layout",
        "world": "worlds/sq_community_4p2.world",
        "manifest": "docs/scene_manifest_4p2.json",
        "plan": "docs/sq_community_plan_4p2.svg",
        "task_points": "route/task_points_4p2.csv",
        "frame": "gazebo_world_center",
        "arena_m": [4.2, 4.2],
        "grid": {"cell_size_m": .2, "count_x": 21, "count_y": 21,
                 "cell_center_world_m": ["-2.0 + 0.2*x", "-2.0 + 0.2*y"]},
        "start": {"corner": "upper_right", "grid_x": [18, 20], "grid_y": [18, 20],
                  "area_m": [.6, .6], "center_world_m": [1.8, 1.8]},
        "robot_target_m": [.334, .303],
        "lane_target_width_m": .6,
        "road_cells_half_open": [{"id": name, "bounds": bounds} for name, bounds in ROADS],
        "placement_authority": "physical anchors planned from schematic, not measured official coordinates",
    }
    (PKG / "config/arena_4p2.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_csv():
    with (PKG / "route/task_points_4p2.csv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(("task_id", "grid_x", "grid_y", "gazebo_x_m", "gazebo_y_m", "yaw_rad", "model_id", "asset_id", "purpose"))
        for t in TASKS:
            wr.writerow((t[0], t[1], t[2], "%.3f" % cell_world(t[1]), "%.3f" % cell_world(t[2]),
                         "%.5f" % t[3], t[4], t[5], t[6]))


def make_svg():
    scale = 120
    pad = 70

    def sx(x): return pad + x * scale
    def sy(y): return pad + (4.2 - y) * scale

    def rect(x0, x1, y0, y1, fill, stroke="none", sw=0):
        return "<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s' stroke='%s' stroke-width='%s'/>" % (
            sx(x0), sy(y1), (x1 - x0) * scale, (y1 - y0) * scale, fill, stroke, sw)

    colors = {"start_finish": "#e7a35b", "a_people": "#f1d383", "a_street": "#f6dda0",
              "b_people": "#f1d383", "building_A": "#a9dcb4", "building_B": "#a9dcb4",
              "building_C": "#a9dcb4", "building_D": "#a9dcb4", "station": "#a9dcb4",
              "ebike_parking": "#a8d0f4", "car_parking": "#a8d0f4"}
    parts = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1060 650'>",
             "<rect width='1060' height='650' fill='#fff'/>" ,
             "<text x='70' y='38' font-family='Microsoft YaHei' font-size='20' font-weight='bold'>智慧社区 4.2 m 场地工程规划（21×21）</text>",
             rect(0, 4.2, 0, 4.2, "#d8dce0", "#263040", 3)]
    for name, bounds, _ in ZONES:
        x0, x1, y0, y1 = (m(v) for v in bounds)
        parts.append(rect(x0, x1, y0, y1, colors[name], "#445466", 1))
        label = {"start_finish": "起终点", "a_people": "A人群", "a_street": "A街区", "b_people": "B人群",
                 "station": "站房",
                 "car_parking": "汽车位", "ebike_parking": "电动车位"}.get(name, name.replace("building_", "楼宇"))
        parts.append("<text x='%.1f' y='%.1f' text-anchor='middle' font-family='Microsoft YaHei' font-size='12'>%s</text>" %
                     (sx((x0 + x1) / 2), sy((y0 + y1) / 2), escape(label)))
    for name, bounds in ROADS:
        x0, x1, y0, y1 = (m(v) for v in bounds)
        parts.append(rect(x0, x1, y0, y1, "#b5bcc5"))
    for i in range(22):
        c = m(i)
        parts.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#92a0ae' stroke-opacity='.36' stroke-width='.5'/>" %
                     (sx(c), sy(0), sx(c), sy(4.2)))
        parts.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#92a0ae' stroke-opacity='.36' stroke-width='.5'/>" %
                     (sx(0), sy(c), sx(4.2), sy(c)))
    parts.append(rect(2.592, 2.608, 3.6, 4.2, "#fff"))
    parts.append(rect(1.8, 2.4, 1.242, 1.258, "#fff"))
    parts.append("<line x1='604' y1='65' x2='604' y2='575' stroke='#c5ccd5' stroke-width='2'/>")
    parts.append("<text x='630' y='81' font-family='Microsoft YaHei' font-size='16' font-weight='bold'>任务观察位（格心坐标）</text>")
    for number, task in enumerate(TASKS, 1):
        x, y = m(task[1] + .5), m(task[2] + .5)
        parts.append("<circle cx='%.1f' cy='%.1f' r='9' fill='#0b4f9c' stroke='white' stroke-width='1.5'><title>%s</title></circle>" %
                     (sx(x), sy(y), escape(task[0])))
        parts.append("<text x='%.1f' y='%.1f' text-anchor='middle' dominant-baseline='central' fill='white' font-family='Arial' font-size='9' font-weight='bold'>%02d</text>" %
                     (sx(x), sy(y), number))
        parts.append("<text x='630' y='%d' font-family='Consolas,monospace' font-size='13'>%02d  %s  (%d,%d)</text>" %
                     (105 + number * 27, number, escape(task[0]), task[1], task[2]))
    parts.append("<text x='70' y='608' font-family='Microsoft YaHei' font-size='12'>蓝点为规划任务观察位；物料精确坐标由示意图推定，非官方测绘值。</text>")
    parts.append("</svg>")
    (PKG / "docs/sq_community_plan_4p2.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")


def main():
    required = PKG / "models/sq_competition_assets/asset_manifest.json"
    if not required.exists():
        raise SystemExit("Run work/build_assets_4p2.py first: " + str(required))
    for bounds in [r[1] for r in ROADS]:
        x0, x1, y0, y1 = bounds
        assert x1 - x0 == 3 or y1 - y0 == 3, bounds
    objects = []
    build_meshes()
    make_light_models()
    count = make_world(objects)
    make_world([], people_style="standee", filename="sq_community_4p2_standees.world")
    make_manifest(objects, count)
    make_config()
    make_csv()
    make_svg()
    print("generated world models", count, "objects", len(objects), "task points", len(TASKS))


if __name__ == "__main__":
    main()
