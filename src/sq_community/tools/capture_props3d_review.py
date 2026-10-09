#!/usr/bin/env python2
# Review camera and temporary robot placement are visual QA, not navigation tests.
import copy, json, math, os, time, sys
import rospy, cv2
from cv_bridge import CvBridge
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import GetModelState, SetModelState, SpawnModel, DeleteModel
from geometry_msgs.msg import Pose
from sensor_msgs.msg import Image
from tf.transformations import quaternion_from_euler

OUT=os.environ.get('SQ_REVIEW_OUTPUT','/home/terry/sq4_standee_review_20261002')
if not os.path.isdir(OUT):os.makedirs(OUT)
rospy.init_node('sq4_props3d_review',anonymous=True)
rospy.wait_for_service('/gazebo/spawn_sdf_model',timeout=60)
spawn=rospy.ServiceProxy('/gazebo/spawn_sdf_model',SpawnModel)
delete=rospy.ServiceProxy('/gazebo/delete_model',DeleteModel)
get=rospy.ServiceProxy('/gazebo/get_model_state',GetModelState)
set_state=rospy.ServiceProxy('/gazebo/set_model_state',SetModelState)
bridge=CvBridge();latest={};records=[]
selection=set(sys.argv[1:])
if selection:
    with open(os.path.join(OUT,'capture_manifest.json')) as f:records=[r for r in json.load(f) if r['label'] not in selection]
def callback(message,key):latest[key]=message
for key,topic in [('review','/sq_review/image_raw'),('front','/camera/rgb/image_raw'),('wide','/task_camera/image_raw')]:
    rospy.Subscriber(topic,Image,callback,callback_args=key,queue_size=1)

name='sq4_review_camera'
try:delete(name)
except Exception:pass
xml='''<sdf version="1.6"><model name="sq4_review_camera"><static>true</static><link name="camera_link"><sensor name="review_sensor" type="camera"><always_on>true</always_on><update_rate>5</update_rate><camera><horizontal_fov>1.25</horizontal_fov><image><width>1920</width><height>1080</height><format>R8G8B8</format></image><clip><near>0.005</near><far>20</far></clip></camera><plugin name="review_ros" filename="libgazebo_ros_camera.so"><cameraName>sq_review</cameraName><imageTopicName>/sq_review/image_raw</imageTopicName><cameraInfoTopicName>/sq_review/camera_info</cameraInfoTopicName><frameName>review_camera</frameName></plugin></sensor></link></model></sdf>'''
pose=Pose();pose.position.z=4;pose.orientation.w=1
assert spawn(name,xml,'',pose,'world').success
rospy.sleep(3.0)

def move(model,xyz,rpy):
    state=ModelState();state.model_name=model;state.reference_frame='world'
    state.pose.position.x,state.pose.position.y,state.pose.position.z=xyz
    q=quaternion_from_euler(*rpy)
    state.pose.orientation.x,state.pose.orientation.y,state.pose.orientation.z,state.pose.orientation.w=q
    assert set_state(state).success
    return rospy.Time.now().to_sec()

def save(label,key,after):
    deadline=time.time()+20
    while time.time()<deadline:
        msg=latest.get(key)
        if msg is not None and msg.header.stamp.to_sec()>after+.6:break
        time.sleep(.1)
    else:raise RuntimeError('no fresh frame '+key)
    frame=bridge.imgmsg_to_cv2(msg,'bgr8')
    path=os.path.join(OUT,label+'.png');assert cv2.imwrite(path,frame)
    records.append({'label':label,'topic_camera':key,'stamp':msg.header.stamp.to_sec(),'file':path})
    print('CAPTURED',label,frame.shape)

views=[
 ('01_people_A',(-.84,1.10,1.15),(-.84,1.10,.07)),
 ('02_people_B',(-.85,.83,.49),(-.85,.06,.07)),
 ('03_people_close_front',(-.63,1.45,.23),(-.63,1.18,.075)),
 ('04_people_close_back',(-.63,.72,.27),(-.63,1.2,.085)),
 ('05_ebike_parking',(0.90,.57,1.35),(1.73,.57,.04)),
 ('06_ebike_detail',(1.43,.52,.22),(1.73,.326,.06)),
 ('07_ebike_fallen',(1.43,1.04,.32),(1.73,1.22,.045)),
 ('08_ebike_A_violations',(.08,1.64,.38),(.07,1.21,.065)),
 ('09_scene_overview',(0,0,5.6),(0,0,0)),
]
original=get('sq_mecanum_334','world').pose
try:
    for label,xyz,target in views:
        if selection and label not in selection:continue
        dx,dy,dz=[target[i]-xyz[i] for i in range(3)]
        yaw=math.atan2(dy,dx) if math.hypot(dx,dy)>.001 else math.pi/2
        pitch=math.atan2(-dz,math.hypot(dx,dy))
        stamp=move(name,xyz,(0,pitch,yaw));save(label,'review',stamp)
    for label,x,y,yaw in [('people_A',-.8,1.8,-math.pi/2),('people_B',-.8,.6,-math.pi/2),('ebikes',1.2,.6,0)]:
        if selection:continue
        stamp=move('sq_mecanum_334',(x,y,.002),(0,0,yaw))
        save('robot_'+label+'_front','front',stamp)
        save('robot_'+label+'_wide','wide',stamp)
    with open('/home/terry/sq_ws/src/sq_community/config/props_observation_views_4p2.json') as f:
        observation_views=json.load(f)['views']
    for view in observation_views:
        if selection and 'scan_'+view['id'] not in selection:continue
        x,y,yaw=view['robot_pose_xy_yaw']
        stamp=move('sq_mecanum_334',(x,y,.002),(0,0,yaw))
        save('scan_'+view['id'],'front',stamp)
finally:
    state=ModelState();state.model_name='sq_mecanum_334';state.reference_frame='world';state.pose=copy.deepcopy(original)
    set_state(state);delete(name)
    with open(os.path.join(OUT,'capture_manifest.json'),'w') as f:json.dump(records,f,indent=2)
