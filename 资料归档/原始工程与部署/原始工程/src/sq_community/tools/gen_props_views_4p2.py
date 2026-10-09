#!/usr/bin/env python3
"""Save camera QA poses and check framing; these are not active patrol goals."""
from pathlib import Path
import json, math, itertools

ROOT=Path(__file__).resolve().parents[1]
views=[]
for group,x,y,base,offsets in [('A',-.8,1.87,-math.pi/2,[-.45,0,.45]),
                              ('B',-.8,.67,-math.pi/2,[-.45,0,.45]),
                              ('A_violations',.08,1.89,-math.pi/2,[-.3,0,.3])]:
    for j,angle in enumerate(offsets):
        views.append({'id':group+'_'+str(j+1),'group':group,
                      'robot_pose_xy_yaw':[x,y,base+angle],'camera':'/camera/rgb/image_raw'})
views.append({'id':'A_4','group':'A','robot_pose_xy_yaw':[-.35,1.88,-math.pi/2],
              'camera':'/camera/rgb/image_raw'})
for j,y in enumerate([-.02,.43,.88,1.30]):
    views.append({'id':'parking_'+str(j+1),'group':'parking',
                  'robot_pose_xy_yaw':[1.10,y,0.0],'camera':'/camera/rgb/image_raw'})
roads=[(-2.1,2.1,1.5,2.1),(-2.1,-1.5,-1.5,1.5),(-1.5,.3,.3,.9),
       (-.3,.3,-1.5,.9),(-2.1,1.5,-2.1,-1.5),(.9,1.5,-1.5,1.5)]
for view in views:
    x,y,a=view['robot_pose_xy_yaw']
    for dx,dy in itertools.product([-.167,.167],[-.1515,.1515]):
        px=x+dx*math.cos(a)-dy*math.sin(a);py=y+dx*math.sin(a)+dy*math.cos(a)
        assert any(x0<=px<=x1 and y0<=py<=y1 for x0,x1,y0,y1 in roads),view['id']
report=json.loads((ROOT/'docs/props_3d_validation.json').read_text())
coverage={};f=640/math.tan(1.3439/2)
for obj in report['geometry']:
    lo,hi=obj['world_physical_aabb'];expected=[]
    index=int(obj['id'][-2:])
    group=('A' if index<=9 else 'B') if obj['id'].startswith('sq4_person_') else ('parking' if index<=10 else 'A_violations')
    for view in views:
        if view['group']!=group:continue
        rx,ry,a=view['robot_pose_xy_yaw'];cx=rx+.156*math.cos(a);cy=ry+.156*math.sin(a)
        uv=[]
        for px,py,pz in itertools.product(*[(lo[i],hi[i]) for i in range(3)]):
            dx=px-2.1-cx;dy=py-2.1-cy;depth=dx*math.cos(a)+dy*math.sin(a)
            if depth<=0:break
            right=dx*math.sin(a)-dy*math.cos(a)
            uv.append((640+f*right/depth,360-f*(pz-.161)/depth))
        if len(uv)==8 and all(8<u<1272 and 8<v<712 for u,v in uv):expected.append(view['id'])
    coverage[obj['id']]=expected
missing=[k for k,v in coverage.items() if not v]
assert not missing,('not fully framed',missing)
(ROOT/'config/props_observation_views_4p2.json').write_text(json.dumps({
    'purpose':'Visual QA and future recognition sampling; NOT wired into patrol',
    'views':views,'nominal_projection_coverage':coverage,
    'coverage_limit':'Frustum containment only; actual image inspection is required for occlusion and recognition'},indent=2)+'\n')
print('PASS: all 30 props fully inside at least one camera frustum; all 14 QA poses keep the body inside roads.')
