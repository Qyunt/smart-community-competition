#!/usr/bin/env python3
"""Training-reference person standees and procedural electric mopeds.

Default people follow training p5: independent 150 x 50 x 5 mm boards.
Legacy volumetric person code is retained only for recovery, not the formal scene.
"""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

PKG = Path(__file__).resolve().parents[1]
TAU = 2 * math.pi


def add(a, b): return tuple(x+y for x, y in zip(a, b))
def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def mul(a, k): return tuple(x*k for x in a)
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a): return mul(a, 1/max(1e-12, math.sqrt(dot(a, a))))


class Mesh:
    def __init__(self): self.faces = []
    def tri(self, a, b, c, color):
        if dot(cross(sub(b,a),sub(c,a)),cross(sub(b,a),sub(c,a))) > 1e-22:
            self.faces.append((a,b,c,tuple(color)))
    def quad(self, a,b,c,d,color):
        self.tri(a,b,c,color); self.tri(a,c,d,color)
    def box(self, center, size, color):
        x,y,z=center; a,b,c=[v/2 for v in size]
        v=[(x+dx*a,y+dy*b,z+dz*c) for dx,dy,dz in
           [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.quad(*(v[i] for i in ids),color)
    def ellipsoid(self, center, radius, color, rings=12, sectors=24):
        def p(i,j):
            a=math.pi*i/rings; b=TAU*j/sectors
            return add(center,(radius[0]*math.sin(a)*math.cos(b),radius[1]*math.sin(a)*math.sin(b),radius[2]*math.cos(a)))
        for i in range(rings):
            for j in range(sectors):
                self.quad(p(i,j),p(i+1,j),p(i+1,j+1),p(i,j+1),color)
    def tube(self, a,b,radius,color,ends=False,sectors=16,radius_end=None):
        axis=unit(sub(b,a)); temp=(0,0,1) if abs(axis[2])<.9 else (1,0,0)
        u=unit(cross(axis,temp)); v=cross(axis,u)
        r2=radius if radius_end is None else radius_end
        def p(c,r,j): return add(c,add(mul(u,r*math.cos(TAU*j/sectors)),mul(v,r*math.sin(TAU*j/sectors))))
        for j in range(sectors):
            pa,pb,pc,pd=p(a,radius,j),p(a,radius,j+1),p(b,r2,j+1),p(b,r2,j)
            self.quad(pa,pb,pc,pd,color)
            self.tri(a,pb,pa,color); self.tri(b,pd,pc,color)
        if ends:
            self.ellipsoid(a,(radius,)*3,color,8,16)
            self.ellipsoid(b,(r2,)*3,color,8,16)
    def wheel_ring(self,c,major,minor,color,start=0,end=TAU):
        # Wheel axle is Y; the circular tread is in the X/Z plane.
        segments=36; sides=8
        def p(i,j):
            a=start+(end-start)*i/segments; b=TAU*j/sides
            r=major+minor*math.cos(b)
            return add(c,(r*math.cos(a),minor*math.sin(b),r*math.sin(a)))
        for i in range(segments):
            for j in range(sides):self.quad(p(i,j),p(i,j+1),p(i+1,j+1),p(i+1,j),color)
    def bounds(self):
        pts=[p for f in self.faces for p in f[:3]]
        return [min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]
    def normalize(self, size):
        lo,hi=self.bounds(); mid=[(lo[i]+hi[i])/2 for i in range(2)]+[lo[2]]
        scale=[size[i]/(hi[i]-lo[i]) for i in range(3)]
        self.faces=[tuple(tuple((p[i]-mid[i])*scale[i] for i in range(3)) for p in f[:3])+(f[3],) for f in self.faces]
    def write(self,path):
        groups={}
        for *pts,color in self.faces:groups.setdefault(color,[]).append(pts)
        root=ET.Element('COLLADA',xmlns='http://www.collada.org/2005/11/COLLADASchema',version='1.4.1')
        asset=ET.SubElement(root,'asset'); ET.SubElement(asset,'unit',name='meter',meter='1');ET.SubElement(asset,'up_axis').text='Z_UP'
        effects=ET.SubElement(root,'library_effects'); materials=ET.SubElement(root,'library_materials')
        geometries=ET.SubElement(root,'library_geometries'); scenes=ET.SubElement(root,'library_visual_scenes')
        scene=ET.SubElement(scenes,'visual_scene',id='Scene',name='Scene')
        for index,(color,faces) in enumerate(groups.items()):
            key='part%d'%index; mat='mat%d'%index; eff=ET.SubElement(effects,'effect',id=mat+'fx')
            common=ET.SubElement(eff,'profile_COMMON'); technique=ET.SubElement(common,'technique',sid='common'); shader=ET.SubElement(technique,'phong')
            for prop,values in [('ambient',tuple(v*.65 for v in color[:3])+(1,)),('diffuse',color),('specular',(.16,.16,.16,1))]:
                ET.SubElement(ET.SubElement(shader,prop),'color').text=' '.join(map(str,values))
            ET.SubElement(ET.SubElement(shader,'shininess'),'float').text='22'
            material=ET.SubElement(materials,'material',id=mat,name=mat);ET.SubElement(material,'instance_effect',url='#'+mat+'fx')
            geom=ET.SubElement(geometries,'geometry',id=key); mesh=ET.SubElement(geom,'mesh')
            positions=[p for face in faces for p in face]
            normals=[unit(cross(sub(face[1],face[0]),sub(face[2],face[0]))) for face in faces for _ in range(3)]
            for suffix,values in [('pos',positions),('norm',normals)]:
                sid=key+suffix;source=ET.SubElement(mesh,'source',id=sid)
                ET.SubElement(source,'float_array',id=sid+'array',count=str(len(values)*3)).text=' '.join('%.7f'%v for p in values for v in p)
                accessor=ET.SubElement(ET.SubElement(source,'technique_common'),'accessor',source='#'+sid+'array',count=str(len(values)),stride='3')
                for axis in 'XYZ':ET.SubElement(accessor,'param',name=axis,type='float')
            vertices=ET.SubElement(mesh,'vertices',id=key+'verts');ET.SubElement(vertices,'input',semantic='POSITION',source='#'+key+'pos')
            tri=ET.SubElement(mesh,'triangles',material=mat,count=str(len(faces)))
            ET.SubElement(tri,'input',semantic='VERTEX',source='#'+key+'verts',offset='0')
            ET.SubElement(tri,'input',semantic='NORMAL',source='#'+key+'norm',offset='1')
            ET.SubElement(tri,'p').text=' '.join('%d %d'%(i,i) for i in range(len(positions)))
            node=ET.SubElement(scene,'node',id=key+'node'); instance=ET.SubElement(node,'instance_geometry',url='#'+key)
            tc=ET.SubElement(ET.SubElement(instance,'bind_material'),'technique_common')
            ET.SubElement(tc,'instance_material',symbol=mat,target='#'+mat)
        ET.SubElement(ET.SubElement(root,'scene'),'instance_visual_scene',url='#Scene')
        path.parent.mkdir(parents=True,exist_ok=True)
        ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)


DARK=(.035,.045,.055,1); SILVER=(.52,.58,.61,1); WHITE=(.89,.91,.9,1)
BLUE=(.08,.23,.43,1); NAVY=(.035,.075,.13,1); BROWN=(.19,.105,.06,1)
PROFILES=[
 ('gardener',(.18,.34,.38,1),(.25,.27,.23,1),'hat'),
 ('business_woman',NAVY,NAVY,'longhair'),
 ('artist',(.13,.28,.42,1),BLUE,'apron'),
 ('construction_worker',(.97,.39,.035,1),(.24,.22,.17,1),'helmet'),
 ('police_officer',(.12,.32,.56,1),NAVY,'cap'),
 ('hooded_outsider',(.055,.067,.08,1),DARK,'hood'),
 ('traveler',(.96,.35,.055,1),(.15,.3,.28,1),'backpack'),
 ('skater',DARK,(.42,.29,.16,1),'cap'),
 ('business_woman_black',DARK,DARK,'longhair'),
 ('student_woman',(.18,.43,.19,1),NAVY,'longhair'),
 ('cook',(.23,.53,.53,1),NAVY,'apron'),
 ('doctor',WHITE,(.13,.43,.4,1),'coat'),
 ('polo_man',(.55,.075,.06,1),(.48,.4,.26,1),'short'),
 ('elder',(.3,.21,.15,1),(.21,.17,.14,1),'greyhair'),
 ('waiter',NAVY,NAVY,'vest'),
 ('vest_outsider',(.06,.09,.12,1),(.15,.17,.14,1),'vest'),
 ('guitar_student',(.16,.32,.39,1),(.2,.25,.28,1),'guitar'),
 ('professor',(.14,.18,.2,1),(.19,.2,.21,1),'glasses'),
]


def person_mesh(index):
    role,shirt,pants,style=PROFILES[index-1]; mesh=Mesh()
    skin=[(.69,.44,.29,1),(.83,.62,.47,1),(.91,.72,.58,1)][index%3]
    hair=(.32,.32,.31,1) if style=='greyhair' else BROWN if index%3==0 else DARK
    female=index in (2,3,9,10)
    # Separate legs, articulated arms, neck and head give true volume from all views.
    for side in (-1,1):
        stride=.0025*side if index%3==0 else 0
        hip=(0,side*.008,.073); knee=(stride,side*.0085,.042); ankle=(-stride,side*.009,.009)
        mesh.tube(hip,knee,.0066,pants,True,radius_end=.0049)
        mesh.tube(knee,ankle,.0049,pants,True,radius_end=.0037)
        mesh.ellipsoid((.002-stride,side*.009,.005),(.010,.005,.005),DARK)
    mesh.ellipsoid((0,0,.075),(.0085,.013,.010),pants)
    mesh.ellipsoid((0,0,.096),(.0088,.015,.024),shirt)
    if style in ('coat','apron'):
        mesh.box((.006,0,.083),(.006,.024,.035),WHITE if style=='coat' else BLUE)
    if style=='vest':mesh.box((.0088,0,.105),(.0018,.008,.025),WHITE if index==15 else DARK)
    if style in ('helmet','cap'):
        mesh.box((.0088,0,.094),(.0015,.026,.004),(.85,.87,.72,1))
    if role.startswith('business') or role=='professor':
        mesh.box((.009,0,.104),(.002,.008,.024),WHITE)
        mesh.box((.0105,0,.103),(.001,.002,.019),(.35,.09,.06,1))
    for side in (-1,1):
        shoulder=(0,side*.015,.111)
        elbow=(.003 if index%2 else -.001,side*.020,.092)
        wrist=(.012,side*.012,.087) if index%4==0 else (.002,side*.020,.075)
        mesh.tube(shoulder,elbow,.0055,shirt,True,radius_end=.0042)
        mesh.tube(elbow,wrist,.0042,skin if index in (8,13,16) else shirt,True,radius_end=.0032)
        mesh.ellipsoid(wrist,(.0038,.0033,.0048),skin)
    mesh.tube((0,0,.114),(0,0,.124),.0043,skin)
    mesh.ellipsoid((0,0,.135),(.010,.009,.013),skin)
    # Back hair, top cap, and small face geometry; faces point in local +X.
    mesh.ellipsoid((-.005,0,.138),(.0065,.0095,.011),hair)
    mesh.ellipsoid((-.001,0,.144),(.009,.0093,.0045),hair)
    if female:mesh.ellipsoid((-.007,0,.126),(.004,.010,.012),hair)
    if style=='hood':
        mesh.ellipsoid((-.004,0,.134),(.010,.012,.015),shirt)
        mesh.ellipsoid((.0055,0,.135),(.005,.007,.009),skin)
        mesh.box((.0095,0,.129),(.002,.014,.008),DARK)
    if style in ('hat','helmet','cap'):
        color=(.98,.64,.045,1) if style=='helmet' else (.51,.43,.27,1) if style=='hat' else BLUE if index==5 else DARK
        mesh.ellipsoid((-.001,0,.147),(.0115,.011,.005),color)
        mesh.ellipsoid((.002,0,.144),(.014 if style=='hat' else .012,.014 if style=='hat' else .010,.0014),color)
    for side in (-1,1):
        mesh.ellipsoid((.0092,side*.0037,.137),(.0013,.0013,.0014),DARK,8,12)
        mesh.ellipsoid((0,side*.009,.134),(.002,.0018,.003),skin,8,12)
    mesh.ellipsoid((.010,0,.133),(.0025,.0018,.0023),skin,8,12)
    mesh.box((.0098,0,.1285),(.0008,.005,.0008),(.36,.16,.12,1))
    if style in ('glasses','greyhair'):
        for side in (-1,1):
            for dz in (-.002,.002):mesh.box((.0103,side*.004,.137+dz),(.0008,.006,.0007),DARK)
            for dy in (-.003,.003):mesh.box((.0103,side*.004+dy,.137),(.0008,.0007,.004),DARK)
        mesh.box((.0103,0,.137),(.0008,.002,.0007),DARK)
    if style in ('backpack','guitar'):
        mesh.ellipsoid((-.012,0,.097),(.006,.012,.020),(.19,.24,.21,1))
        for side in (-1,1):mesh.box((.008,side*.011,.1),(.002,.002,.030),DARK)
    if style=='guitar':
        mesh.ellipsoid((-.017,0,.089),(.004,.013,.017),DARK)
        mesh.tube((-.018,0,.100),(-.018,.003,.14),.003,DARK)
    if index in (7,10,14,18):
        mesh.box((.014,0,.083),(.004,.023,.016),(.2,.45,.32,1) if index==18 else (.77,.72,.56,1))
    if index==1:mesh.tube((.01,-.021,.026),(.01,-.021,.084),.0015,SILVER)
    if index==3:mesh.ellipsoid((.016,-.014,.08),(.003,.012,.008),(.55,.32,.13,1))
    if index==8:mesh.box((.002,-.024,.045),(.004,.008,.065),(.19,.2,.21,1))
    mesh.normalize((.033,.05,.15))
    return mesh


def ebike_mesh(color):
    m=Mesh(); rubber=(.025,.029,.033,1)
    for x in (-.060,.060):
        c=(x,0,.028)
        m.wheel_ring(c,.0235,.0045,rubber)
        m.wheel_ring(c,.0187,.0017,SILVER)
        m.tube((x,-.009,.028),(x,.009,.028),.009,DARK if x<0 else SILVER)
        for j in range(8):
            a=TAU*j/8
            m.tube(c,(x+.019*math.cos(a),0,.028+.019*math.sin(a)),.0008,SILVER,sectors=8)
        m.wheel_ring((x,0,.028),.030,.0028,color,.18,math.pi-.18)
    # Step-through chassis, battery, rear suspension and footboard.
    m.box((-.004,0,.043),(.07,.035,.010),color)
    m.box((.004,0,.050),(.057,.03,.004),DARK)
    m.ellipsoid((-.035,0,.061),(.03,.020,.015),color)
    m.box((-.028,0,.07),(.042,.032,.014),color)
    m.ellipsoid((-.032,0,.084),(.033,.019,.007),DARK)
    m.tube((-.057,-.014,.03),(-.024,-.014,.070),.0025,SILVER)
    m.tube((-.057,.014,.03),(-.024,.014,.070),.0025,SILVER)
    # Front fork and steering column form a continuous load path.
    for side in (-1,1):m.tube((.060,side*.009,.028),(.045,side*.009,.084),.0023,SILVER)
    m.tube((.019,0,.047),(.043,0,.094),.008,color,True,radius_end=.006)
    m.tube((.042,0,.079),(.047,0,.108),.0026,SILVER)
    m.tube((.047,-.031,.108),(.047,.031,.108),.0022,SILVER)
    for side in (-1,1):
        m.tube((.047,side*.023,.108),(.047,side*.036,.108),.003,rubber)
        m.tube((.047,side*.024,.109),(.047,side*.030,.128),.0009,SILVER,sectors=8)
        m.ellipsoid((.047,side*.03,.129),(.002,.006,.003),SILVER)
    m.box((.056,0,.094),(.012,.022,.015),color)
    m.ellipsoid((.063,0,.095),(.002,.008,.004),(.96,.93,.76,1))
    m.box((-.065,0,.070),(.004,.021,.008),(.65,.025,.018,1))
    m.tube((-.07,-.016,.083),(-.077,-.016,.083),.0018,SILVER)
    m.tube((-.077,-.016,.083),(-.077,.016,.083),.0018,SILVER)
    for side in (-1,1):
        m.tube((-.052,side*.016,.066),(-.077,side*.016,.083),.0018,SILVER)
        m.tube((-.052,side*.016,.083),(-.077,side*.016,.083),.0018,SILVER)
    # Central stand contacts ground while parked; no unsupported floating body.
    for side in (-1,1):m.tube((-.015,side*.01,.043),(-.025,side*.025,.002),.0018,DARK)
    m.normalize((.18,.075,.13))
    return m


# Physical coordinates measured from the arena lower-left; front points +X.
# Alternating depths and deliberately different yaw angles avoid a single row.
PEOPLE=[
 (.85,3.24,75), (1.03,3.43,110), (1.18,3.17,165), (1.32,3.39,90),
 (1.47,3.22,20), (1.65,3.35,100), (.97,3.07,260), (1.42,3.07,205), (1.68,3.10,140),
 (.82,2.13,85), (1.00,2.20,35), (1.17,2.09,120), (1.34,2.18,95),
 (1.51,2.10,180), (1.67,2.20,270), (.94,1.96,105), (1.30,1.93,65), (1.63,1.94,230),
]
BIKE_COLORS=[(.12,.37,.52,1),(.58,.13,.09,1),(.76,.77,.70,1),(.10,.28,.21,1)]


def ebike_placements():
    rows=[]
    for i in range(10):
        rows.append({'id':'sq4_ebike_%02d'%(i+1),'physical_xy_m':[3.83+(i%3-1)*.016,1.94+i*.162],
                     'yaw_deg':[176,183,178,186,174][i%5], 'roll_deg':90 if i==8 else -90 if i==9 else 0,
                     'zone':'parking','fallen':i>=8,'illegal_parking':False,'color_index':i%4})
    for i,(x,y,yaw) in enumerate([(2.03,3.27,110),(2.31,3.37,165)],11):
        rows.append({'id':'sq4_ebike_%02d'%i,'physical_xy_m':[x,y], 'yaw_deg':yaw,'roll_deg':0,
                     'zone':'A','fallen':False,'illegal_parking':True,'color_index':i%4})
    return rows


def mesh_model(name,x,y,yaw,uri,box,z=.004,roll=0):
    # The same rigid transform applies to visual and collision, including falls.
    return ("<model name='%s'><static>true</static><pose>%.6f %.6f %.6f %.8f 0 %.8f</pose>"
            "<link name='body'><visual name='body_visual'><geometry><mesh><uri>%s</uri></mesh></geometry></visual>"
            "<collision name='body_collision'><pose>0 0 %.6f 0 0 0</pose><geometry><box><size>%.6f %.6f %.6f</size></box></geometry></collision>"
            "</link></model>")%(name,x-2.1,y-2.1,z,roll,yaw,uri,box[2]/2,*box)


def add_people_models(parts,objects,style='standee'):
    for i,(x,y,angle) in enumerate(PEOPLE,1):
        name='sq4_person_%02d'%i; yaw=math.radians(angle)
        if style=='3d':
            parts.append(mesh_model(name,x,y,yaw,'model://sq_people_3d/meshes/person_%02d.dae'%i,(.033,.05,.15)))
        else:
            # The white backing and printed layer together fit exactly 5 mm.
            # Local +X is the printed front. All boards face the northern observation road.
            parts.append(("<model name='%s'><static>true</static><pose>%.5f %.5f .004 0 0 %.8f</pose>"
                "<link name='panel'>"
                "<visual name='backing'><pose>-.0001 0 .075 0 0 0</pose><geometry><box><size>.0048 .05 .15</size></box></geometry>"
                "<material><lighting>false</lighting><ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse><emissive>1 1 1 1</emissive></material></visual>"
                "<visual name='portrait'><pose>.0024 0 .075 0 0 0</pose><geometry><box><size>.0002 .05 .15</size></box></geometry>"
                "<material><script><uri>model://sq_competition_assets/materials/scripts</uri>"
                "<uri>model://sq_competition_assets/materials/textures</uri><name>SQ4_Person_%02d</name></script></material></visual>"
                "<collision name='panel_collision'><pose>0 0 .075 0 0 0</pose><geometry><box><size>.005 .05 .15</size></box></geometry>"
                "</collision></link></model>")%(name,x-2.1,y-2.1,math.pi/2,i))
        objects.append({'id':name,'type':'person','zone':'A' if i<=9 else 'B','physical_xy_m':[x,y],
                        'yaw_deg':angle if style=='3d' else 90,'is_outsider':i in (6,16),'representation':style,
                        'role_reference':PROFILES[i-1][0],'reference_asset':'person_%02d.png'%i,
                        'dimensions_xyz_m':[.033 if style=='3d' else .005,.05,.15],
                        'placement':'engineered_scattered_positions','source':'superseded assistant approximation; not the formal competition representation' if style=='3d' else 'training p5'})


def add_ebike_models(parts,objects):
    for entry in ebike_placements():
        roll=math.radians(entry['roll_deg']); height=.004 if not entry['fallen'] else .004+.075/2
        x,y=entry['physical_xy_m']; yaw=math.radians(entry['yaw_deg'])
        x-=math.sin(yaw)*math.sin(roll)*.065
        y+=math.cos(yaw)*math.sin(roll)*.065
        uri='model://sq_ebikes_3d/meshes/ebike_%d.dae'%entry['color_index']
        parts.append(mesh_model(entry['id'],x,y,yaw,uri,(.18,.075,.13),height,roll))
        objects.append(dict(entry,type='ebike',dimensions_upright_xyz_m=[.18,.075,.13],
                            placement='engineered_example_not_mandatory_count',source='rules p6: street violations and parking-area upright/fallen states',
                            model_origin_physical_xy_m=[x,y],ground_z_m=height))


def build_meshes(include_legacy_people=False):
    stats=[]
    for index in (range(1,19) if include_legacy_people else []):
        mesh=person_mesh(index);path=PKG/'models/sq_people_3d/meshes'/('person_%02d.dae'%index)
        mesh.write(path);lo,hi=mesh.bounds()
        stats.append({'asset':str(path.relative_to(PKG)).replace('\\','/'),'triangles':len(mesh.faces),'bounds_min':lo,'bounds_max':hi})
    for index,color in enumerate(BIKE_COLORS):
        mesh=ebike_mesh(color);path=PKG/'models/sq_ebikes_3d/meshes'/('ebike_%d.dae'%index)
        mesh.write(path);lo,hi=mesh.bounds()
        stats.append({'asset':str(path.relative_to(PKG)).replace('\\','/'),'triangles':len(mesh.faces),'bounds_min':lo,'bounds_max':hi})
    for name,uri,box in [('sq_people_3d','person_01.dae',(.033,.05,.15)),('sq_ebikes_3d','ebike_0.dae',(.18,.075,.13))]:
        if name=='sq_people_3d' and not include_legacy_people:continue
        folder=PKG/'models'/name
        (folder/'model.config').write_text("<model><name>%s</name><version>1.0</version><sdf version='1.6'>model.sdf</sdf></model>"%name,encoding='utf8')
        (folder/'model.sdf').write_text("<sdf version='1.6'>%s</sdf>"%mesh_model(name,2.1,2.1,0,'model://%s/meshes/%s'%(name,uri),box),encoding='utf8')
    (PKG/'docs/props_3d_meshes.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf8')
    return stats


if __name__=='__main__':
    print('Generated',len(build_meshes()),'mesh assets')
