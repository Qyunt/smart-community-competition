#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(root,'route/task_points_4p2.csv'),'rb') as f:
    rows = list(csv.DictReader(line.lstrip('\xef\xbb\xbf') for line in f))
def kind(name):
    for prefix,value in [('TL_','traffic_light'),('PEOPLE_','people'),('SIGN_','sign'),('BUILDING_D','temperature'),('BUILDING_','fire'),('BINS','bins'),('STATION','gauges'),('CAR_','plate'),('EBIKES','ebikes')]:
        if name.startswith(prefix):return value
    return 'parking'
TASK_KIND = {r['task_id']:kind(r['task_id']) for r in rows}
FRONT_CAMERA = set(k for k,v in TASK_KIND.items() if v in ('traffic_light','people','plate','gauges','bins'))
