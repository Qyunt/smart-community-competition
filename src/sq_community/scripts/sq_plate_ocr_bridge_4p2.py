#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Send captured car frames to a persistent Python 3 OCR worker.

ROS Melodic on the Ubuntu 18.04 VM is Python 2; the supplied EasyOCR runtime is
Python 3 on the host. This node carries only JPEG bytes and JSON across that
boundary. The worker URL is a ROS parameter and can later point to a Python 3
environment on the robot itself.
"""
from __future__ import print_function

import json
import os
import threading

import rospy
from std_msgs.msg import String

try:
    from Queue import Queue
    from urllib2 import Request, urlopen
except ImportError:
    from queue import Queue
    from urllib.request import Request, urlopen


CAR_NAMES = {'CAR_1': u'一号', 'CAR_2': u'二号', 'CAR_3': u'三号'}


class PlateBridge(object):
    def __init__(self):
        rospy.init_node('sq_plate_ocr_bridge_4p2')
        self.url = rospy.get_param('~url', 'http://192.168.232.1:8765/ocr')
        self.result_file = rospy.get_param('~result_file', '/tmp/sq4_plate_results.jsonl')
        self.queue = Queue()
        self.pub = rospy.Publisher('/sq/vision/plate', String, queue_size=10)
        self.pub_voice = rospy.Publisher('/sq/voice/say', String, queue_size=10)
        rospy.Subscriber('/sq/patrol/observation', String, self.on_observation,
                         queue_size=10)
        worker = threading.Thread(target=self.work)
        worker.daemon = True
        worker.start()

    def on_observation(self, message):
        try:
            event = json.loads(message.data)
            if event.get('task_id') in CAR_NAMES and event.get('image'):
                self.queue.put(event)
        except (ValueError, TypeError) as exc:
            rospy.logwarn('[plate OCR] invalid observation: %s' % exc)

    def work(self):
        while not rospy.is_shutdown():
            try:
                event = self.queue.get(timeout=0.5)
            except Exception:
                continue
            task_id = event['task_id']
            try:
                with open(event['image'], 'rb') as stream:
                    jpeg = stream.read()
                request = Request(self.url, data=jpeg, headers={
                    'Content-Type': 'image/jpeg', 'X-Task-Id': task_id})
                reply = urlopen(request, timeout=90)
                result = json.loads(reply.read().decode('utf8'))
                result['task_id'] = task_id
                result['image'] = event['image']
            except Exception as exc:
                result = {'task_id': task_id, 'image': event['image'],
                          'plate': None, 'reason': str(exc)}
            payload = json.dumps(result, ensure_ascii=False).encode('utf8')
            self.pub.publish(String(data=payload))
            with open(self.result_file, 'ab') as stream:
                stream.write(payload + b'\n')
            if result.get('plate'):
                spoken = CAR_NAMES[task_id] + u'车位车牌号为' + result['plate']
            else:
                spoken = CAR_NAMES[task_id] + u'车位车牌未识别，请复核照片'
            self.pub_voice.publish(String(data=spoken.encode('utf8')))
            rospy.loginfo('[plate OCR] %s' % payload)
            self.queue.task_done()


if __name__ == '__main__':
    PlateBridge()
    rospy.spin()
