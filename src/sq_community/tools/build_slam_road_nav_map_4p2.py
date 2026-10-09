#!/usr/bin/env python3
"""Add surveyed road boundaries to the measured 4.2 m GMapping map.

The source SLAM map remains unchanged.  This derived map gives move_base
virtual no-go cells at road edges that are only painted in the Gazebo scene
and therefore invisible to lidar.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "maps/sq_slam_4p2.pgm"
DEST = ROOT / "maps/sq_slam_road_nav_4p2.pgm"
YAML = ROOT / "maps/sq_slam_road_nav_4p2.yaml"
EVIDENCE = ROOT / "maps/sq_slam_road_nav_4p2_evidence.json"
ROADS = [(-2.1, 2.1, 1.5, 2.1), (-2.1, -1.5, -1.5, 1.5),
         (-1.5, .3, .3, .9), (-.3, .3, -1.5, .9),
         (-2.1, 1.5, -2.1, -1.5), (.9, 1.5, -1.5, 1.5)]
WIDTH = HEIGHT = 92
RESOLUTION = .05
ORIGIN = -2.3


def main():
    raw = SOURCE.read_bytes()
    header = b"P5\n92 92\n255\n"
    if not raw.startswith(header) or len(raw) != len(header) + WIDTH * HEIGHT:
        raise ValueError("Unexpected SLAM map dimensions or encoding")
    pixels = bytearray(raw[len(header):])
    marked = 0
    for row in range(HEIGHT):
        y = ORIGIN + (HEIGHT - row - .5) * RESOLUTION
        for col in range(WIDTH):
            x = ORIGIN + (col + .5) * RESOLUTION
            if not any(x0 <= x <= x1 and y0 <= y <= y1
                       for x0, x1, y0, y1 in ROADS):
                offset = row * WIDTH + col
                if pixels[offset] != 0:
                    marked += 1
                pixels[offset] = 0
    result = header + pixels
    DEST.write_bytes(result)
    YAML.write_text("image: sq_slam_road_nav_4p2.pgm\n"
                    "resolution: 0.050000\n"
                    "origin: [-2.300000, -2.300000, 0.000000]\n"
                    "negate: 0\noccupied_thresh: 0.65\n"
                    "free_thresh: 0.196\n", encoding="utf8")
    EVIDENCE.write_text(json.dumps({
        "source": SOURCE.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "derived_sha256": hashlib.sha256(result).hexdigest(),
        "method": "Retain each GMapping pixel inside the surveyed roads; mark other cells occupied for navigation only",
        "added_no_go_pixels": marked,
        "source_pixels_unchanged_inside_roads": True,
        "road_rectangles_xyxy_m": ROADS,
    }, indent=2) + "\n", encoding="utf8")
    print("derived navigation map:", DEST)
    print("new no-go cells:", marked)


if __name__ == "__main__":
    main()
