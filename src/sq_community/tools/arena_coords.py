#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Coordinate helpers for the 4.2 m arena; compatible with Python 2 and 3."""
from __future__ import print_function

import math

CELL_M = 0.2
COUNT = 21
LOWER_BOUND_M = -2.1
UPPER_BOUND_M = 2.1
CENTER_0_M = -2.0


def _check_index(value):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < COUNT:
        raise ValueError("grid index must be an integer in 0..20: %r" % (value,))


def cell_bounds(index):
    """Return inclusive lower and exclusive upper edge for a cell."""
    _check_index(index)
    low = LOWER_BOUND_M + index * CELL_M
    return (low, low + CELL_M)


def grid_to_world(x, y):
    """Map cell indices to their centers in Gazebo metres."""
    _check_index(x)
    _check_index(y)
    return (CENTER_0_M + x * CELL_M,
            CENTER_0_M + y * CELL_M)


def world_to_grid(x_m, y_m):
    """Return the indices of the cells containing a Gazebo position."""
    result = []
    for value in (x_m, y_m):
        if math.isinf(value) or math.isnan(value):
            raise ValueError("world position must be finite")
        if not LOWER_BOUND_M <= value < UPPER_BOUND_M:
            raise ValueError("world position is outside the arena: %r" % (value,))
        result.append(int(math.floor((value - LOWER_BOUND_M) / CELL_M)))
    return tuple(result)


def start_bounds():
    """Return x and y bounds of the known 3 by 3 start area."""
    return (cell_bounds(18)[0], cell_bounds(20)[1],
            cell_bounds(18)[0], cell_bounds(20)[1])


if __name__ == "__main__":
    for gx in range(COUNT):
        for gy in range(COUNT):
            assert world_to_grid(*grid_to_world(gx, gy)) == (gx, gy)
    assert grid_to_world(0, 0) == (-2.0, -2.0)
    assert grid_to_world(20, 20) == (2.0, 2.0)
    assert all(abs(a - b) < 1e-9 for a, b in zip(start_bounds(), (1.5, 2.1, 1.5, 2.1)))
    print("441 cell centers verified; start x/y in [1.5, 2.1] m")
