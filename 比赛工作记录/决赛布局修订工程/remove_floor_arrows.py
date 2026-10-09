#!/usr/bin/env python
from __future__ import print_function
import rospy,json,os
from gazebo_msgs.srv import DeleteModel
rospy.init_node('sq_remove_floor_arrows',anonymous=True)
rospy.wait_for_service('/gazebo/delete_model',timeout=10)
remove=rospy.ServiceProxy('/gazebo/delete_model',DeleteModel)
result=[]
for i in range(8):
    name='sq4_direction_%02d'%i;r=remove(name)
    result.append({'model':name,'removed':r.success,'message':r.status_message})
json.dump(result,open(os.path.expanduser('~/sq_community_ws_20261008/acceptance/final_layout_20261008/remove_arrows.json'),'w'),indent=2)
print(json.dumps(result,indent=2))