#!/usr/bin/env python3
"""Plan a 4.2 m patrol route on road centre lines from task_points_4p2.csv.

This creates waypoints for the existing sq_patrol.py parser. It does not
certify a navigable map, traffic-light compliance, or vision results.
"""

from collections import deque
import csv
import math
from pathlib import Path


PKG = Path(__file__).resolve().parents[1]
TASKS = PKG / "route/task_points_4p2.csv"
OUT = PKG / "route/sq_route_patrol_4p2.csv"


def road_centre_nodes():
    lines = (
        ((x, 19) for x in range(1, 20)),     # top road and start region
        ((1, y) for y in range(1, 20)),       # west road
        ((x, 13) for x in range(1, 11)),     # west-to-central connector
        ((10, y) for y in range(1, 14)),     # central road
        ((x, 1) for x in range(1, 17)),      # bottom road
        ((16, y) for y in range(1, 20)),     # east road
    )
    return {node for line in lines for node in line}


def shortest_path(start, goal, nodes):
    queue = deque([start])
    prev = {start: None}
    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            break
        for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if neighbor in nodes and neighbor not in prev:
                prev[neighbor] = (x, y)
                queue.append(neighbor)
    if goal not in prev:
        raise ValueError("disconnected centre-line route: %s -> %s" % (start, goal))
    path = []
    here = goal
    while here is not None:
        path.append(here)
        here = prev[here]
    return list(reversed(path))


def select_transits(path, max_cells=4):
    """Keep every turn and at most 0.8 m between successive route goals."""
    picked = []
    last = 0
    for i in range(1, len(path) - 1):
        incoming = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
        outgoing = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
        if incoming != outgoing or i - last >= max_cells:
            picked.append(i)
            last = i
    return picked


def world(index):
    return -2.0 + 0.2 * index


def main():
    with TASKS.open(encoding="utf-8-sig", newline="") as stream:
        tasks = list(csv.DictReader(stream))
    nodes = road_centre_nodes()
    current = (19, 19)
    rows = []
    counter = 0
    for task in tasks:
        goal = (int(task["grid_x"]), int(task["grid_y"]))
        if goal not in nodes:
            raise ValueError("task is off road centre line: " + task["task_id"])
        path = shortest_path(current, goal, nodes)
        for index in select_transits(path):
            counter += 1
            x, y = path[index]
            nx, ny = path[index + 1]
            yaw = math.atan2(ny - y, nx - x)
            rows.append(("过路%02d" % counter, world(x), world(y), yaw, ""))
        if task["task_id"] == "CAR_2":
            # Turn on the broad bottom-road junction before travelling north
            # beside the narrow parking frontage.  The camera-facing CAR_1
            # yaw is east, while this segment travels north.
            counter += 1
            rows.append(("过路%02d" % counter, world(current[0]),
                         world(current[1]), math.pi / 2, ""))
        rows.append((task["task_id"], world(goal[0]), world(goal[1]), float(task["yaw_rad"]),
                     "到达观察位，识别结果待视觉节点确认" if task["task_id"] != "RETURN" else "返回起终点"))
        current = goal
    with OUT.open("w", encoding="utf-8", newline="") as stream:
        stream.write("# Planned 4.2 m centre-line route; 33-goal odom/LiDAR patrol and camera signal gating were tested in Gazebo.\n")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("名称", "x", "y", "yaw", "播报"))
        for name, x, y, yaw, message in rows:
            writer.writerow((name, "%.3f" % x, "%.3f" % y, "%.5f" % yaw, message))
    print("planned route", len(tasks), "observation points,", counter,
          "transit points,", len(rows), "total goals")


if __name__ == "__main__":
    main()
