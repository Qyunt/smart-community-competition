#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Speak short Chinese patrol results and keep the last sentence on a ROS topic.

Speech Dispatcher is part of the tested Ubuntu 18.04 VM. The text topic and
ROS log remain available when that VM has no audible output device.
"""
from __future__ import print_function

import subprocess
import threading

import rospy
from std_msgs.msg import String

try:
    from Queue import Queue
except ImportError:
    from queue import Queue


class Voice(object):
    def __init__(self):
        rospy.init_node('sq_voice_4p2')
        self.queue = Queue()
        self.last = rospy.Publisher('/sq/voice/last', String, queue_size=10, latch=True)
        rospy.Subscriber('/sq/voice/say', String, self.on_text, queue_size=10)
        thread = threading.Thread(target=self.speak_loop)
        thread.daemon = True
        thread.start()

    def on_text(self, message):
        if message.data:
            self.queue.put(message.data)

    def speak_loop(self):
        while not rospy.is_shutdown():
            try:
                sentence = self.queue.get(timeout=0.5)
            except Exception:
                continue
            self.last.publish(String(data=sentence))
            rospy.loginfo('[voice] %s' % sentence)
            try:
                subprocess.check_call(['timeout', '25', 'spd-say', '-l', 'cmn',
                                       '-w', sentence])
            except (OSError, subprocess.CalledProcessError) as exc:
                rospy.logwarn('[voice] speech unavailable: %s' % exc)
            finally:
                self.queue.task_done()


if __name__ == '__main__':
    Voice()
    rospy.spin()
