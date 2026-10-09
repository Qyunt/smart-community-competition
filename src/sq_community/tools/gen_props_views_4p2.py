#!/usr/bin/env python3
"""Export the active observation poses rather than obsolete independent QA poses."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
m=json.loads((P/'docs/scene_manifest_4p2.json').read_text(encoding='utf-8'))
v=json.loads((P/'docs/final_layout_validation.json').read_text(encoding='utf-8'))
views=[]
for t in m['task_points']:
    name=t['id'];wide=name.startswith('BUILDING_') or name.startswith('SIGN_') or name.startswith('EBIKES_') or name=='RETURN'
    views.append({'id':name,'robot_pose_xy_yaw':t['world_xy_m']+[t['yaw_rad']],
                  'camera':'/task_camera/image_raw' if wide else '/camera/rgb/image_raw',
                  'purpose':t['purpose'],'target':t['target'],'wired_into_patrol':True})
(P/'config/props_observation_views_4p2.json').write_text(json.dumps({
    'purpose':'Active final-layout observation points; camera runtime QA required',
    'views':views,'nominal_portrait_frustum_coverage':v['portrait_frustum_coverage'],
    'coverage_limit':v['limit']},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Exported',len(views),'active views')
