#!/usr/bin/env python
from __future__ import print_function
import json,os,time,sys
import rospy
from std_msgs.msg import String

root=os.path.expanduser('~/sq_community_ws_20261008/acceptance/'+(sys.argv[1] if len(sys.argv)>1 else 'patrol_20261008_01'))
rospy.init_node('sq_patrol_evidence_recorder',anonymous=True)
stream=open(os.path.join(root,'events.jsonl'),'ab',0)
def on_message(topic,message):
    payload=message.data
    try:
        payload=json.loads(payload)
    except ValueError:
        payload=payload.decode('utf8') if isinstance(payload,str) else payload
    if topic.endswith('_debug') and payload.get('site') not in ('TL_UP_WAIT','TL_LOW_WAIT'):
        return
    row={'topic':topic,'wall_time':time.time(),'sim_time':rospy.Time.now().to_sec(),'payload':payload}
    stream.write(json.dumps(row,ensure_ascii=False).encode('utf8')+b'\n')
topics=['/sq/patrol/current','/sq/patrol/observation','/sq/voice/say','/sq/vision/traffic_light_debug']
subs=[rospy.Subscriber(t,String,lambda m,t=t:on_message(t,m),queue_size=20) for t in topics]
deadline=time.time()+1800
while not rospy.is_shutdown() and time.time()<deadline:
    if os.path.isfile(os.path.join(root,'status.txt')) and 'FINISHED' in open(os.path.join(root,'status.txt')).read():
        break
    time.sleep(.5)
stream.close()
