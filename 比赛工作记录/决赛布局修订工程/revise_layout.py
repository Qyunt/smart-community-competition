from pathlib import Path
import re

P = Path(__file__).parent / 'src/sq_community'
f = P/'tools/gen_scene_4p2.py'
s = f.read_text(encoding='utf-8')
s = s.replace('("building_C", (12, 15, 3, 9)', '("building_C", (12, 15, 8, 10)')
s = s.replace('("building_D", (3, 6, 3, 8)', '("building_D", (3, 6, 3, 8)')
s = s.replace('    ("station", (6, 9, 3, 8),', '    ("bins", (12, 15, 3, 8), (0.79, 0.85, 0.79, 1)),\n    ("station", (6, 9, 3, 8),')
tasks = '''TASKS = [
    ("TL_UP_WAIT", 14, 19, math.pi, "sq4_tl_upper", "light", "first upper red-to-green gate"),
    ("PEOPLE_A_TOP_R", 7, 19, -math.pi/2, "sq4_person_03", "people", "A north-facing portraits, right view"),
    ("PEOPLE_A_TOP_L", 4, 19, -math.pi/2, "sq4_person_01", "people", "A north-facing portraits, left view"),
    ("PEOPLE_A_WEST_N", 1, 17, 0, "sq4_person_08", "people", "A west-facing portraits, north view"),
    ("PEOPLE_A_WEST_S", 1, 15, 0, "sq4_person_07", "people", "A west-facing portraits, south view"),
    ("SIGN_WEST", 1, 12, 0, "sq4_sign_speed30", "sign", "west roadside sign"),
    ("PEOPLE_B_WEST_N", 1, 11, 0, "sq4_person_15", "people", "B west-facing portraits, north view"),
    ("PEOPLE_B_WEST_S", 1, 9, 0, "sq4_person_14", "people", "B west-facing portraits, south view"),
    ("BUILDING_D", 1, 5, 0, "sq4_building_D", "win_hot", "D west facade and temperature target"),
    ("STATION_GAUGES", 7, 1, math.pi/2, "sq4_station", "gauges", "station south-facing gauges"),
    ("CAR_1", 16, 1, 0, "sq4_car_1", "plate_blue", "west-facing bay 1 plate"),
    ("CAR_2", 16, 4, 0, "sq4_car_2", "plate_yellow", "west-facing bay 2 plate"),
    ("CAR_3", 16, 7, 0, "sq4_car_3", "plate_green", "west-facing bay 3 plate"),
    ("BINS_LOW", 16, 4, math.pi, "sq4_bin_kitchen", "bins", "lower two east-facing bins"),
    ("BINS_HIGH", 16, 6, math.pi, "sq4_bin_hazard", "bins", "upper two east-facing bins"),
    ("BUILDING_B", 16, 10, math.pi, "sq4_building_B", "win_fire", "B east facade"),
    ("EBIKES_LOW", 16, 12, 0, "sq4_ebike_01", "ebikes", "lower e-bike parking"),
    ("EBIKES_HIGH", 16, 15, 0, "sq4_ebike_07", "ebikes", "upper e-bike parking"),
    ("TL_UP_WAIT_2", 14, 19, math.pi, "sq4_tl_upper", "light", "second upper red-to-green gate"),
    ("PEOPLE_A_SOUTH_L", 4, 13, math.pi/2, "sq4_person_04", "people", "A south-facing portraits, left view"),
    ("PEOPLE_B_NORTH_L", 4, 13, -math.pi/2, "sq4_person_10", "people", "B north-facing portraits, left view"),
    ("PEOPLE_A_SOUTH_R", 7, 13, math.pi/2, "sq4_person_06", "people", "A south-facing portraits, right view"),
    ("PEOPLE_B_NORTH_R", 7, 13, -math.pi/2, "sq4_person_12", "people", "B north-facing portraits, right view"),
    ("BUILDING_A", 8, 13, 0, "sq4_building_A", "win_fire", "A west facade"),
    ("PEOPLE_B_EAST", 10, 11, math.pi, "sq4_person_18", "people", "B east-facing portraits"),
    ("BUILDING_C", 10, 10, -.71883, "sq4_building_C", "win_fire", "C facade above signal wait; no stop-line overlap"),
    ("TL_LOW_WAIT", 10, 9, -math.pi/2, "sq4_tl_lower", "light", "lower red-to-green gate"),
    ("RETURN", 19, 19, math.pi, "sq4_zone_start_finish", "none", "finish via start-finish access"),
]'''
# Bins must be observed in northbound order; keep tasks along the directed east lane.
tasks = tasks.replace('    ("BINS_LOW", 16, 4,', '    ("BINS_LOW", 16, 7,').replace('    ("BINS_HIGH", 16, 6,', '    ("BINS_HIGH", 16, 8,')
s = re.sub(r'TASKS = \[.*?\n\]', tasks, s, count=1, flags=re.S)
s = s.replace('("A", 2.7, 2.7, .58, .58', '("A", 2.7, 2.75, .50, .38')
s = s.replace('("B", 2.7, 2.1, .58, .58', '("B", 2.7, 2.15, .50, .38')
s = s.replace('("C", 2.7, 1.2, .58, 1.16', '("C", 2.7, 1.75, .50, .34')
s = s.replace('cols = 4 if label == "C" else 3', 'cols = 3')
s = s.replace('"C": {(1, 1), (2, 3)}', '"C": {(1, 0), (2, 2)}')
s = s.replace('    bins = [\n', '    bins = [\n', 1)
start = s.index('    bins = [', s.index('def add_station_and_bins'))
end = s.index('\n\n\ndef add_cars', start)
s = s[:start] + '''    # Rule diagram: four bins below C, north-south row, fronts facing east.
    bins = [("hazard", 1.41, True, "correct", (.72,.16,.18,1)),
            ("recycle", 1.19, False, "none", (.13,.42,.69,1)),
            ("other", .97, False, "none", (.38,.40,.42,1)),
            ("kitchen", .75, True, "wrong", (.71,.55,.16,1))]
    for typ, y, opened, load, color in bins:
        name = "sq4_bin_" + typ
        links = [box_link("body", .11, .12, .17, color, collision=True, lz=.085),
                 box_link("front", .003, .10, .12, script="SQ_bin_" + typ, old=True, lx=.057, lz=.085)]
        if opened:
            links.append(box_link("open_lid", .10, .12, .012, (.12,.17,.18,1), lx=.03,lz=.18,lyaw=.25))
        parts.append(model(name, 2.7, y, links))
        objects.append({"id":name,"type":"bin","category":typ,"open":opened,"load":load,
                        "physical_xy_m":[2.7,y],"front":"east","placement":"estimated_from_rule_p3"})
''' + s[end:]
s = s.replace('("speed30", .69, 3.52, math.pi / 2)', '("speed30", .69, 2.5, math.pi)')
# Diagram start/finish subdivision is paint only, not a wall.
s = s.replace('    for j in range(3):\n        y0 = j * .6', '    parts.append(rectangle("sq4_start_finish_divider", (3.6,4.2,3.895,3.905), (.98,.98,.96,1), .006))\n    for j in range(3):\n        y0 = j * .6')
s = s.replace('"building_C": "#a9dcb4",', '"building_C": "#a9dcb4", "bins": "#d5e4d5",')
s = s.replace('                 "station": "站房",', '                 "station": "站房", "bins": "垃圾桶",')
# Keep the schematic plan tall enough for the expanded observation list.
s = s.replace("viewBox='0 0 1060 650'", "viewBox='0 0 1200 1050'").replace("width='1060' height='650'", "width='1200' height='1050'")
s = s.replace('"No', '"No')
# Add actual object anchors and material-facing arrows to the engineering plan.
anchor = '    parts.append("<text x=\'70\' y=\'608\''
idx = s.index(anchor)
addition = '''    objects = json.loads((PKG / "docs/scene_manifest_4p2.json").read_text(encoding="utf-8"))["objects"]
    for obj in objects:
        x, y = obj["physical_xy_m"]
        if obj["type"] in ("building","station","bin","person","ebike","car_plate_board","traffic_light"):
            radius = 3 if obj["type"] == "person" else 5
            parts.append("<circle cx='%.1f' cy='%.1f' r='%d' fill='#b53c35'><title>%s</title></circle>" % (sx(x),sy(y),radius,escape(obj["id"])))
            angle = obj.get("yaw_deg", {"west":180,"east":0,"north":90,"south":270}.get(obj.get("front",obj.get("face","")),180 if obj["type"]=="car_plate_board" else 270))
            dx, dy = .10*math.cos(math.radians(angle)), .10*math.sin(math.radians(angle))
            parts.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#d59113' stroke-width='2'/>" % (sx(x),sy(y),sx(x+dx),sy(y+dy)))
    route = list(csv.DictReader(line for line in (PKG / "route/sq_route_patrol_4p2.csv").read_text(encoding="utf-8").splitlines() if not line.startswith("#")))
    path = " ".join("%.1f,%.1f"%(sx(float(r["x"])+2.1),sy(float(r["y"])+2.1)) for r in route)
    parts.append("<polyline points='%s' fill='none' stroke='#247cc2' stroke-opacity='.6' stroke-width='2'/>"%path)
'''
s = s[:idx]+addition+s[idx:]
# Route must precede SVG creation so it is generated from current coordinates.
s = s.replace('    make_svg()\n    print', '    from gen_route_4p2 import main as route_main\n    route_main()\n    make_svg()\n    print')
f.write_text(s, encoding='utf-8')

f = P/'tools/scene_props_3d.py';s=f.read_text(encoding='utf-8')
s=re.sub(r'PEOPLE=\[.*?\n\]', '''PEOPLE=[
 (.85,3.15,90),(1.25,3.18,90),(1.65,3.15,90),
 (1.00,3.50,270),(1.40,3.48,270),(1.70,3.45,270),
 (.95,3.25,180),(1.25,3.35,180),(1.60,3.30,180),
 (.85,1.85,90),(1.25,1.90,90),(1.65,1.85,90),
 (.90,2.25,180),(1.20,2.00,180),(1.60,2.15,180),
 (.90,2.35,0),(1.25,2.30,0),(1.60,2.35,0),
]''',s,count=1,flags=re.S)
s=s.replace('math.pi/2,i))','yaw,i))').replace("'yaw_deg':angle if style=='3d' else 90", "'yaw_deg':angle")
s=s.replace('All boards face the northern observation road.', 'Fronts follow the north/west/south or north/west/east rule arrows.')
s=s.replace('build_meshes()', 'build_meshes()')
f.write_text(s,encoding='utf-8')

# The task contract derives from the generated observation table, including repeated gates.
(P/'scripts/sq_task_plan_4p2.py').write_text('''#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(root,'route/task_points_4p2.csv'),'rb') as f:
    rows = list(csv.DictReader(f))
def kind(name):
    for prefix,value in [('TL_','traffic_light'),('PEOPLE_','people'),('SIGN_','sign'),('BUILDING_D','temperature'),('BUILDING_','fire'),('BINS','bins'),('STATION','gauges'),('CAR_','plate'),('EBIKES','ebikes')]:
        if name.startswith(prefix):return value
    return 'parking'
TASK_KIND = {r['task_id']:kind(r['task_id']) for r in rows}
FRONT_CAMERA = set(k for k,v in TASK_KIND.items() if v in ('traffic_light','people','plate','gauges','bins','ebikes'))
''',encoding='utf-8')
for name in ['sq_patrol_4p2.py','sq_patrol_nav_4p2.py']:
    f=P/'scripts'/name;s=f.read_text(encoding='utf-8')
    s=s.replace("LIGHTS = ('TL_UP_WAIT', 'TL_LOW_WAIT')", "LIGHTS = ('TL_UP_WAIT', 'TL_UP_WAIT_2', 'TL_LOW_WAIT')")
    if name=='sq_patrol_4p2.py':
        s=s.replace("        self.start_index =", "        self.max_linear = float(rospy.get_param('~max_linear', .15))\n        self.max_angular = float(rospy.get_param('~max_angular', .70))\n        self.start_index =",1)
        s=s.replace('clamp(1.8*error, .38)','clamp(1.8*error, self.max_angular)').replace('clamp(1.3*ex, .085), clamp(1.3*ey, .085)','clamp(1.3*ex, self.max_linear), clamp(1.3*ey, self.max_linear)')
    f.write_text(s,encoding='utf-8')
f=P/'scripts/sq_signal_vision_4p2.py';s=f.read_text(encoding='utf-8')
s=s.replace("        self.site = message.data if message.data in BOXES else ''", "        name = 'TL_UP_WAIT' if message.data.startswith('TL_UP_WAIT') else message.data\n        self.site = name if name in BOXES else ''")
f.write_text(s,encoding='utf-8')
print('Scene source revised')
