#!/usr/bin/env python3
import csv,json,shutil,subprocess,sys
from pathlib import Path
p=Path.home()/'sq_community_ws_20261008/src/sq_community'
b=Path.home()/'sq_community_ws_20261008/acceptance/stop_line_fix_20261008_backup'
b.mkdir(exist_ok=False)
paths=['scripts/sq_patrol_4p2.py','tools/gen_scene_4p2.py','route/task_points_4p2.csv','route/sq_route_patrol_4p2.csv','docs/scene_manifest_4p2.json']
for name in paths:
    dst=b/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(str(p/name),str(dst))
s=(p/'scripts/sq_patrol_4p2.py').read_text()
anchor='def load_route(path):'
addition='''def on_stop_line(x, y, yaw):
    # Conservative body projection, including the full 16 mm line thickness.
    ex = abs(math.cos(yaw))*.167 + abs(math.sin(yaw))*.1515
    ey = abs(math.sin(yaw))*.167 + abs(math.cos(yaw))*.1515
    return ((x-ex <= .508 and x+ex >= .492 and y+ey >= 1.5 and y-ey <= 2.1)
            or (y-ey <= -.842 and y+ey >= -.858 and x+ex >= -.3 and x-ex <= .3))


'''
assert anchor in s and 'def on_stop_line' not in s
s=s.replace(anchor,addition+anchor,1)
s=s.replace('''                _, _, yaw = self.check_road()
                error = angle_error(target, yaw)
                if abs(error) < .055:''','''                x, y, yaw = self.check_road()
                error = angle_error(target, yaw)
                if abs(error) >= .055 and on_stop_line(x, y, yaw):
                    raise RuntimeError('rotation would overlap a stop line')
                if abs(error) < .055:''',1)
(p/'scripts/sq_patrol_4p2.py').write_text(s)
s=(p/'tools/gen_scene_4p2.py').read_text()
assert '("BUILDING_C", 10, 6, 0,' in s
(p/'tools/gen_scene_4p2.py').write_text(s.replace('("BUILDING_C", 10, 6, 0,','("BUILDING_C", 10, 4, 0,',1))
f=p/'route/task_points_4p2.csv'
with f.open(encoding='utf-8-sig',newline='') as h: rows=list(csv.DictReader(h)); fields=list(rows[0])
for r in rows:
    if r['task_id']=='BUILDING_C': r['grid_y']='4'; r['world_y']='-1.200' if 'world_y' in r else r.get('world_y','')
# Coordinate columns are named x_m/y_m in this project; locate explicitly.
for r in rows:
    if r['task_id']=='BUILDING_C':
        for key in fields:
            if r[key]=='-0.800': r[key]='-1.200'
        r.pop('world_y',None) if 'world_y' not in fields else None
with f.open('w',encoding='utf-8-sig',newline='') as h:
    w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
f=p/'docs/scene_manifest_4p2.json'; m=json.loads(f.read_text())
for t in m['task_points']:
    if t['id']=='BUILDING_C':t['grid_xy']=[10,4];t['world_xy_m']=[0.0,-1.2]
f.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
subprocess.check_call([sys.executable,str(p/'tools/gen_route_4p2.py')])
subprocess.check_call([sys.executable,str(p/'tools/verify_scene_4p2.py')])
subprocess.check_call(['/usr/bin/python','-m','py_compile',str(p/'scripts/sq_patrol_4p2.py')])
print('STOP_LINE_FIX_INSTALLED')