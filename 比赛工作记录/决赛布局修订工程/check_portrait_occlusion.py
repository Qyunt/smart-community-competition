import json,math
from pathlib import Path
p=Path(__file__).resolve().parent/'src/sq_community/docs'
g=json.loads((p/'props_3d_validation.json').read_text(encoding='utf-8'))
m=json.loads((p/'scene_manifest_4p2.json').read_text(encoding='utf-8'))
r=json.loads((p/'final_layout_validation.json').read_text(encoding='utf-8'))
boxes={x['id']:x['world_physical_aabb'] for x in g['geometry']}
tasks={x['id']:x for x in m['task_points']}
def intersects(a,b,box):
    lo,hi=box;tmin=0;tmax=.999
    for j in range(3):
        delta=b[j]-a[j]
        if abs(delta)<1e-9:
            if not lo[j]<=a[j]<=hi[j]:return False
        else:
            x,y=(lo[j]-a[j])/delta,(hi[j]-a[j])/delta
            tmin=max(tmin,min(x,y));tmax=min(tmax,max(x,y))
            if tmin>tmax:return False
    return True
clear={};blocked={}
for obj in m['objects']:
    if obj['type']!='person':continue
    name=obj['id'];x,y=obj['physical_xy_m'];clear[name]=[];blocked[name]={}
    for view in r['portrait_frustum_coverage'][name]:
        t=tasks[view];a=t['yaw_rad'];rx,ry=t['world_xy_m'];camera=[rx+2.1+.156*math.cos(a),ry+2.1+.156*math.sin(a),.159]
        occluders=[k for k,box in boxes.items() if k!=name and intersects(camera,[x,y,.079],box)]
        if not occluders:clear[name].append(view)
        else:blocked[name][view]=occluders
missing=[k for k,v in clear.items() if not v]
print('Portrait centres without unblocked nominal view:',missing)
for k in missing:print(k,blocked[k])
(p/'portrait_occlusion_review.json').write_text(json.dumps({'method':'centre rays against prop AABBs, not full-pixel visibility or recognition','clear_views':clear,'missing':missing,'blocked':blocked},ensure_ascii=False,indent=2),encoding='utf-8')
