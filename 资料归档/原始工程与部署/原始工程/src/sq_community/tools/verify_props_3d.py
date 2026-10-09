#!/usr/bin/env python3
"""Check actual exported geometry, placement, contact and source variants."""
import itertools
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
world=ET.parse(ROOT/'worlds/sq_community_4p2.world')
models={m.get('name'):m for m in world.findall('.//world/model')}
manifest=json.loads((ROOT/'docs/scene_manifest_4p2.json').read_text(encoding='utf8'))
people=[o for o in manifest['objects'] if o['type']=='person']
bikes=[o for o in manifest['objects'] if o['type']=='ebike']
assert len(people)==18 and sum(p['is_outsider'] for p in people)==2
assert sum(p['zone']=='A' for p in people)==9
assert sum(p['zone']=='B' for p in people)==9
assert all(p['representation']=='standee' and p['yaw_deg']==90 for p in people)
assert len(set(p['physical_xy_m'][1] for p in people))>=12
assert len(bikes)==12
assert sum(b['zone']=='parking' and not b['fallen'] for b in bikes)==8
assert sum(b['zone']=='parking' and b['fallen'] for b in bikes)==2
assert sum(b['illegal_parking'] and b['zone']=='A' for b in bikes)==2

def vertices(uri):
    path=ROOT/'models'/uri[len('model://'):]
    doc=ET.parse(path); points=[]
    for source in doc.findall('.//c:source',NS):
        if not source.get('id','').endswith('pos'):continue
        data=list(map(float,source.find('c:float_array',NS).text.split()))
        points.extend(zip(data[::3],data[1::3],data[2::3]))
    assert points and len(points)>3000,uri
    return points

boxes=[]; report=[]
for obj in people+bikes:
    model=models[obj['id']]; p=list(map(float,model.findtext('pose').split()))
    x,y,z,r,pitch,yaw=p;assert pitch==0
    if obj['type']=='person':
        assert model.findtext('static')=='true'
        assert model.find('.//visual/geometry/mesh') is None
        assert list(map(float,model.findtext('.//collision/geometry/box/size').split()))==[.005,.05,.15]
        assert list(map(float,model.findtext('.//collision/pose').split()))==[0,0,.075,0,0,0]
        points=[]
        for visual in model.findall('.//visual'):
            size=list(map(float,visual.findtext('geometry/box/size').split()))
            pose=list(map(float,visual.findtext('pose').split()))
            assert pose[3:]==[0,0,0]
            points.extend(tuple(pose[i]+q[i] for i in range(3)) for q in itertools.product(*[(-d/2,d/2) for d in size]))
        portrait=model.find(".//visual[@name='portrait']")
        assert portrait.findtext('material/script/name')=='SQ4_Person_'+obj['id'][-2:]
        assert (ROOT/'models/sq_competition_assets/materials/textures'/obj['reference_asset']).is_file()
    else:
        uri=model.findtext('.//visual/geometry/mesh/uri');points=vertices(uri)
    lo=[min(q[i] for q in points) for i in range(3)];hi=[max(q[i] for q in points) for i in range(3)]
    expected=obj['dimensions_xyz_m'] if obj['type']=='person' else obj['dimensions_upright_xyz_m']
    assert all(abs(hi[i]-lo[i]-expected[i])<1e-6 for i in range(3)),obj['id']
    transformed=[]
    for vx,vy,vz in itertools.product(*[(lo[i],hi[i]) for i in range(3)]):
        ty=vy*math.cos(r)-vz*math.sin(r);tz=vy*math.sin(r)+vz*math.cos(r)
        transformed.append((x+vx*math.cos(yaw)-ty*math.sin(yaw)+2.1,y+vx*math.sin(yaw)+ty*math.cos(yaw)+2.1,z+tz))
    bmin=[min(q[i] for q in transformed) for i in range(3)];bmax=[max(q[i] for q in transformed) for i in range(3)]
    assert abs(bmin[2]-.004)<1e-6,('ground',obj['id'],bmin[2])
    if obj['type']=='person':zone=(.6,1.8,3.,3.6) if obj['zone']=='A' else (.6,1.8,1.6,2.4)
    else:zone=(3.6,4.2,1.8,3.6) if obj['zone']=='parking' else (1.8,3.0,3.,3.6)
    assert zone[0]<=bmin[0] and bmax[0]<=zone[1] and zone[2]<=bmin[1] and bmax[1]<=zone[3],('zone',obj['id'],bmin,bmax)
    boxes.append((obj['id'],bmin,bmax))
    report.append({'id':obj['id'],'mesh_size_m':expected,'world_physical_aabb':[bmin,bmax],'ground_clearance_m':bmin[2]-.004})
for (an,al,ah),(bn,bl,bh) in itertools.combinations(boxes,2):
    assert not all(min(ah[i],bh[i])-max(al[i],bl[i])>0 for i in range(2)),('overlap',an,bn)
boards=ET.parse(ROOT/'worlds/sq_community_4p2_standees.world')
boards=[m for m in boards.findall('.//world/model') if m.get('name','').startswith('sq4_person_')]
assert len(boards)==18
for model in boards:
    assert list(map(float,model.findtext('.//collision/geometry/box/size').split()))==[.005,.05,.15]
    assert model.find('.//visual/material/script/name') is not None
assert (ROOT/'worlds/sq_community_4p2.world').read_bytes()==(ROOT/'worlds/sq_community_4p2_standees.world').read_bytes()
result={'passed':True,'people':18,'residents':16,'outsiders':2,'parking_upright':8,'parking_fallen':2,'street_A_violations':2,
        'checks':['actual visual and collision dimensions','18 independent textured standees','north-facing portrait sides','ground contact','zone containment','pairwise conservative AABB separation','standee alternative dimensions'],
        'geometry':report}
(ROOT/'docs/props_3d_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print('PASS: 18 training-reference 150 x 50 x 5 mm standees; 12 mopeds; ground contact, no overlaps, all props inside assigned zones; compliant standee alternative.')
