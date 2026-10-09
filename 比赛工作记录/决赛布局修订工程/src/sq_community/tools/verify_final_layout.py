#!/usr/bin/env python3
"""Independent layout/route/nominal camera checks; does not claim recognition."""
import ast,csv,json,math
from pathlib import Path
from gen_route_4p2 import edges

P=Path(__file__).resolve().parents[1]
m=json.loads((P/'docs/scene_manifest_4p2.json').read_text(encoding='utf-8'))
o={x['id']:x for x in m['objects']}
bins=[x for x in m['objects'] if x['type']=='bin']
assert len(bins)==4 and all(x['front']=='east' for x in bins)
assert all(abs(x['physical_xy_m'][0]-2.7)<1e-8 for x in bins)
assert max(x['physical_xy_m'][1] for x in bins)<o['sq4_building_C']['physical_xy_m'][1]-.17
assert [x['category'] for x in sorted(bins,key=lambda b:-b['physical_xy_m'][1])]==['hazard','recycle','other','kitchen']
assert [o['sq4_building_'+x]['front'] for x in 'ABCD']==['west','east','west','west']
assert o['sq4_station']['front']=='south'
assert set(x['yaw_deg'] for x in m['objects'] if x['type']=='person' and x['zone']=='A')=={90,180,270}
assert set(x['yaw_deg'] for x in m['objects'] if x['type']=='person' and x['zone']=='B')=={0,90,180}

source=ast.parse((P/'scripts/sq_patrol_4p2.py').read_text(encoding='utf-8'))
defs=[node for node in source.body if isinstance(node,ast.FunctionDef) and node.name in ('road_safe','on_stop_line')]
env={'math':math,'ROADS':[(-2.1,2.1,1.5,2.1),(-2.1,-1.5,-1.5,1.5),(-1.5,.3,.3,.9),(-.3,.3,-1.5,.9),(-2.1,1.5,-2.1,-1.5),(.9,1.5,-1.5,1.5)]}
exec(compile(ast.Module(body=defs,type_ignores=[]),'<geometry>','exec'),env)
with (P/'route/sq_route_patrol_4p2.csv').open(encoding='utf-8') as f:r=list(csv.DictReader(line for line in f if not line.startswith('#')))
prev=(1.8,1.8);length=0;crossings={'upper':0,'lower':0};gate=None
for row in r:
    x,y,yaw=float(row['x']),float(row['y']),float(row['yaw']);name=row['名称']
    dx,dy=x-prev[0],y-prev[1];length+=math.hypot(dx,dy)
    assert abs(dx)<1e-6 or abs(dy)<1e-6
    old=(round((prev[0]+2)/.2),round((prev[1]+2)/.2));new=(round((x+2)/.2),round((y+2)/.2))
    cx,cy=old
    while (cx,cy)!=new:
        nxt=(cx+(1 if new[0]>cx else -1 if new[0]<cx else 0),cy+(1 if new[1]>cy else -1 if new[1]<cy else 0))
        assert nxt in edges((cx,cy)) or (name=='RETURN' and cy==19 and 16<=cx<19 and nxt==(cx+1,cy)),(name,(cx,cy),nxt)
        cx,cy=nxt
    if prev[0]>.5 and x<.5 and y>1.5:
        assert gate=='upper';crossings['upper']+=1;gate=None
    if prev[1]>-.85 and y<-.85 and abs(x)<.01:
        assert gate=='lower';crossings['lower']+=1;gate=None
    if name.startswith('TL_UP_WAIT'):gate='upper'
    if name=='TL_LOW_WAIT':gate='lower'
    if abs(dx)+abs(dy)>1e-6:
        heading=math.atan2(dy,dx)
        for i in range(101):
            xx=prev[0]+dx*i/100;yy=prev[1]+dy*i/100
            assert env['road_safe'](xx,yy,heading),(name,xx,yy,'drive')
    for i in range(73):
        a=i*math.pi/36
        assert env['road_safe'](x,y,a),(name,'rotation clearance',a)
    if not name.startswith('过路'):assert not env['on_stop_line'](x,y,yaw),(name,'observation overlaps bar')
    prev=(x,y)
assert crossings=={'upper':2,'lower':1}

# Portrait framing: front camera at .156 m forward, height .159 m, 1280x720.
coverage={}
views=[t for t in m['task_points'] if t['id'].startswith('PEOPLE_')]
focal=640/math.tan(1.3439/2)
for obj in m['objects']:
    if obj['type']!='person':continue
    ox,oy=obj['physical_xy_m'];normal=math.radians(obj['yaw_deg']);available=[]
    for t in views:
        if not t['id'].startswith('PEOPLE_'+obj['zone']+'_'):continue
        rx,ry=t['world_xy_m'];a=t['yaw_rad'];cx=rx+2.1+.156*math.cos(a);cy=ry+2.1+.156*math.sin(a)
        if (cx-ox)*math.cos(normal)+(cy-oy)*math.sin(normal)<=0:continue
        projected=[]
        for side in (-.025,.025):
            px=ox-side*math.sin(normal);py=oy+side*math.cos(normal)
            for z in (.004,.154):
                dx,dy=px-cx,py-cy;depth=dx*math.cos(a)+dy*math.sin(a)
                if depth<=0:break
                right=dx*math.sin(a)-dy*math.cos(a)
                projected.append((640+focal*right/depth,360-focal*(z-.159)/depth))
        if len(projected)==4 and all(3<u<1277 and 3<v<717 for u,v in projected):available.append(t['id'])
    coverage[obj['id']]=available
result={'layout':'rules p3 topology and orientations; engineering coordinates','route_length_m':round(length,2),
        'goals':len(r),'observation_tasks':len(m['task_points']),'gated_crossings':crossings,
        'road_and_turn_clearance':'pass for 334x303 mm body','portrait_frustum_coverage':coverage,
        'portraits_without_complete_nominal_front_view':[k for k,v in coverage.items() if not v],
        'limit':'Framing does not prove occlusion-free images, detection or recognition; runtime camera inspection required.'}
(P/'docs/final_layout_validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='portrait_frustum_coverage'},ensure_ascii=False,indent=2))
assert not result['portraits_without_complete_nominal_front_view']

# All mopeds must fit at least one assigned wide-camera view after mount revision.
g=json.loads((P/'docs/props_3d_validation.json').read_text(encoding='utf-8'))
geometry={x['id']:x['world_physical_aabb'] for x in g['geometry']}
bike_coverage={}
for obj in m['objects']:
    if obj['type']!='ebike':continue
    lo,hi=geometry[obj['id']];available=[]
    for t in m['task_points']:
        if not t['id'].startswith('EBIKES_'):continue
        if (t['id']=='EBIKES_A') != (obj['zone']=='A'):continue
        a=t['yaw_rad'];rx,ry=t['world_xy_m'];cx=rx+2.1+.154*math.cos(a)-.100*math.sin(a);cy=ry+2.1+.154*math.sin(a)+.100*math.cos(a)
        projected=[];focal_w=640/math.tan(2.44346/2)
        for px in (lo[0],hi[0]):
            for py in (lo[1],hi[1]):
                for pz in (lo[2],hi[2]):
                    dx,dy=px-cx,py-cy;forward=dx*math.cos(a)+dy*math.sin(a);dz=pz-.211
                    depth=forward*math.cos(.14)+dz*math.sin(.14)
                    up=dz*math.cos(.14)-forward*math.sin(.14);right=dx*math.sin(a)-dy*math.cos(a)
                    if depth<=0:continue
                    projected.append((640+focal_w*right/depth,360-focal_w*up/depth))
        if len(projected)==8 and all(3<u<1277 and 3<v<717 for u,v in projected):available.append(t['id'])
    bike_coverage[obj['id']]=available
result['ebike_wide_frustum_coverage']=bike_coverage
result['ebikes_without_complete_nominal_view']=[k for k,v in bike_coverage.items() if not v]
(P/'docs/final_layout_validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Mopeds without complete nominal wide view:',result['ebikes_without_complete_nominal_view'])
assert not result['ebikes_without_complete_nominal_view']
