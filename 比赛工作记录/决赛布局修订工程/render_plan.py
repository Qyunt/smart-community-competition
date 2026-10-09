from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json,math
P=Path(__file__).parent/'src/sq_community'
m=json.loads((P/'docs/scene_manifest_4p2.json').read_text(encoding='utf-8'))
im=Image.new('RGB',(1160,1200),'#ffffff');d=ImageDraw.Draw(im)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
f=font(15);small=font(12);title=font(24)
d.text((28,15),'按决赛示意图修订：场景、朝向与观察点',font=title,fill='#1f3343')
d.text((28,53),'坐标原点为场地中心；物料精确坐标按比例估算。',font=f,fill='#566777')
scale=126;pad=30;top=90
def xy(x,y):return (pad+x*scale,top+(4.2-y)*scale)
def rect(bounds,fill,outline=None):
    x0,x1,y0,y1=bounds;d.rectangle([xy(x0,y1),xy(x1,y0)],fill=fill,outline=outline,width=2)
rect((0,4.2,0,4.2),'#f5f6f7','#223342')
for z in m['zones_cells_half_open']:
    x0,x1,y0,y1=[v*.2 for v in z['bounds']];rect((x0,x1,y0,y1),'#e2e9db','#9ca992')
for r in m['roads_cells_half_open']:
    x0,x1,y0,y1=[v*.2 for v in r['bounds']];rect((x0,x1,y0,y1),'#d2d9df')
def arrow(x,y,a,length=.13,color='#d28d20'):
    u,v=xy(x,y);ex,ey=xy(x+length*math.cos(a),y+length*math.sin(a));d.line((u,v,ex,ey),fill=color,width=2)
    for delta in (-.55,.55):
        hx,hy=xy(x+length*math.cos(a)-.06*math.cos(a+delta),y+length*math.sin(a)-.06*math.sin(a+delta));d.line((ex,ey,hx,hy),fill=color,width=2)
# Floor arrows are intentionally absent; heading constraints live in the route.
specs={'A':(.50,.38),'B':(.50,.38),'C':(.50,.34),'D':(.58,.95)}
for obj in m['objects']:
    x,y=obj['physical_xy_m'];u,v=xy(x,y);typ=obj['type']
    if typ=='building':
        sx,sy=specs[obj['label']];rect((x-sx/2,x+sx/2,y-sy/2,y+sy/2),'#b2d8bc','#477a60');d.text((u-20,v-9),'楼'+obj['label'],font=f,fill='#163d2b');arrow(x,y-sy/2-.04,0 if obj['front']=='east' else math.pi)
    elif typ=='station':rect((x-.275,x+.275,y-.4,y+.4),'#f5d69b','#ac894f');d.text((u-16,v-10),'站房',font=f,fill='#695016');arrow(x,y-.43,-math.pi/2)
    elif typ=='bin':
        color={'hazard':'#d65e59','recycle':'#5496c8','other':'#9a9a9a','kitchen':'#d7b75b'}[obj['category']]
        rect((x-.055,x+.055,y-.06,y+.06),color,'#575757');arrow(x+.075,y,0)
    elif typ=='person':
        d.ellipse((u-3,v-3,u+3,v+3),fill='#c35354');arrow(x,y,math.radians(obj['yaw_deg']),.10)
    elif typ=='car_plate_board':
        rect((x-.08,x+.08,y-.17,y+.17),'#93bfd1','#326079');d.text((u-19,v-7),'车'+str(obj['bay']),font=small,fill='#1c4559');arrow(x-.13,y,math.pi)
    elif typ=='ebike':
        d.line((u-8,v,u+8,v),fill='#2b6872',width=4);arrow(x,y,math.radians(obj['yaw_deg']),.1)
    elif typ=='traffic_light':
        d.rectangle((u-8,v-8,u+8,v+8),fill='#444444');d.ellipse((u-3,v-6,u+3,v),fill='#cb332e');arrow(x,y,0 if obj['face']=='east' else math.pi/2)
    elif typ=='traffic_sign':d.ellipse((u-5,v-5,u+5,v+5),fill='#dfb9b9',outline='#934745')
rect((2.592,2.608,3.6,4.2),'#ffffff')
rect((1.8,2.4,1.242,1.258),'#ffffff')
for j in range(5):
    offset=(j-2)*.11
    rect((1.81,2.39,3.9+offset-.024,3.9+offset+.024),'#ffffff')
    rect((2.1+offset-.024,2.1+offset+.024,.61,1.19),'#ffffff')
d.text(xy(3.62,4.16),'起点',font=f,fill='#334438');d.text(xy(3.62,3.86),'终点',font=f,fill='#334438')
groups={}
for i,t in enumerate(m['task_points'],1):groups.setdefault(tuple(t['world_xy_m']),[]).append(i)
for (x,y),ids in groups.items():
    u,v=xy(x+2.1,y+2.1);d.ellipse((u-5,v-5,u+5,v+5),fill='#12589b',outline='white');d.text((u+6,v-7),'/'.join(map(str,ids)),font=small,fill='#15487b')
d.text((615,86),'观察点：世界坐标（米）与朝向',font=font(19),fill='#1b3347')
for i,t in enumerate(m['task_points'],1):
    x,y=t['world_xy_m'];deg=round(math.degrees(t['yaw_rad']))
    d.text((615,118+(i-1)*32),'%02d %-22s'%(i,t['id']),font=small,fill='#20476a')
    d.text((880,118+(i-1)*32),'(% .1f,% .1f) %4d°'%(x,y,deg),font=small,fill='#384a55')
lines=['场景地板不画箭头；橙箭头仅在本图标明物料正面。',
       '蓝点：任务观察位；同一点可转向拍摄多个目标。',
       '垃圾桶：C 楼下方纵向四桶，朝右侧道路。',
       '人群：A 北/西/南朝向，B 北/西/东朝向。',
       '路线：两个上方等灯点、一个下方等灯点。',
       '所有拍照和转向点均避开停止线。',
       '静态净空按 334×303 毫米车身检查。',
       '实际遮挡、识别效果另看巡检照片与验收报告。']
for j,line in enumerate(lines):d.text((30,660+j*31),line,font=f,fill='#455967')
im.save(P/'docs/决赛场景与观察点.png')
print('Plan rendered')
