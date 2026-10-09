#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fixed competition observation tasks for the 4.2 m arena.

The accompanying route CSV contains the surveyed map-frame coordinates and
transit goals. These IDs specify the recognition action at each fixed goal,
so OCR and future YOLO nodes can share the same patrol event contract.
"""

TASK_KIND = {
    'TL_UP_WAIT': 'traffic_light',
    'PEOPLE_A': 'people',
    'SIGN_WEST': 'sign',
    'BUILDING_D': 'temperature',
    'PEOPLE_B': 'people',
    'BUILDING_A': 'fire',
    'BINS': 'bins',
    'TL_LOW_WAIT': 'traffic_light',
    'BUILDING_C': 'fire',
    'STATION_GAUGES': 'gauges',
    'CAR_1': 'plate',
    'CAR_2': 'plate',
    'CAR_3': 'plate',
    'BUILDING_B': 'fire',
    'EBIKES': 'ebikes',
    'RETURN': 'parking',
}

FRONT_CAMERA = set(('TL_UP_WAIT', 'TL_LOW_WAIT', 'CAR_1', 'CAR_2',
                    'CAR_3', 'PEOPLE_A', 'PEOPLE_B', 'STATION_GAUGES'))
