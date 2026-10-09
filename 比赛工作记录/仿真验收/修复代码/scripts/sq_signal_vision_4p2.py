#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Classify the two 4.2 m arena signals from fresh robot camera frames.

The fixed ROIs are calibrated for the two surveyed wait poses in this
package.  This node never reads the simulator's traffic-light state topic.
"""
from __future__ import print_function

import json
import time

import cv2
import numpy as np
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import String


BOXES = {
    'TL_UP_WAIT': ((448, 570, 151, 239), (575, 704, 151, 239),
                   (707, 833, 151, 239)),
    'TL_LOW_WAIT': ((352, 540, 47, 181), (548, 735, 47, 181),
                    (740, 925, 47, 181)),
}
COLORS = ('red', 'yellow', 'green')


def activation(hsv, index):
    hue, sat, value = cv2.split(hsv)
    if index == 0:
        mask = ((hue < 12) | (hue > 170)) & (sat > 70)
    elif index == 1:
        mask = (hue > 12) & (hue < 42) & (sat > 70)
    else:
        mask = (hue > 42) & (hue < 100) & (sat > 70)
    selected = value[mask]
    if selected.size < 100:
        return 0.0
    return float(np.percentile(selected, 90))


def classify(image, site, min_brightness=None, min_score_margin=25):
    if image.shape[:2] != (720, 1280):
        return 'unknown', [0, 0, 0]
    scores = []
    for index, (x0, x1, y0, y1) in enumerate(BOXES[site]):
        hsv = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
        scores.append(round(activation(hsv, index), 1))
    order = sorted(range(3), key=lambda i: scores[i], reverse=True)
    first, second = scores[order[0]], scores[order[1]]
    if min_brightness is None:
        min_brightness = 145 if site == 'TL_UP_WAIT' else 85
    if first < min_brightness or first - second < min_score_margin:
        return 'unknown', scores
    return COLORS[order[0]], scores


class SignalVision(object):
    def __init__(self):
        rospy.init_node('sq_signal_vision_4p2')
        self.site = rospy.get_param('~site', '')
        self.min_brightness = {
            'TL_UP_WAIT': float(rospy.get_param('~min_brightness_upper', 145)),
            'TL_LOW_WAIT': float(rospy.get_param('~min_brightness_lower', 85)),
        }
        self.min_score_margin = float(rospy.get_param('~min_score_margin', 25))
        self.bridge = CvBridge()
        self.latest = None
        self.frame_stamp = rospy.Time(0)
        self.state_pub = rospy.Publisher('/sq/vision/traffic_light', String,
                                         queue_size=10)
        self.debug_pub = rospy.Publisher('/sq/vision/traffic_light_debug', String,
                                         queue_size=10)
        rospy.Subscriber('/sq/patrol/current', String, self.on_site, queue_size=1)
        rospy.Subscriber('/camera/rgb/image_raw', Image, self.on_image, queue_size=1)
        self.timer = rospy.Timer(rospy.Duration(0.2), self.tick)

    def on_site(self, message):
        self.site = message.data if message.data in BOXES else ''

    def on_image(self, message):
        # A new subscriber can receive a cached frame from before the camera
        # started rendering.  Keep its stamp so tick() rejects that frame.
        self.latest = message
        self.frame_stamp = message.header.stamp

    def tick(self, _event):
        site = self.site
        message = self.latest
        now = rospy.Time.now()
        age = (now - self.frame_stamp).to_sec() if message is not None else 999
        state, scores = 'unknown', [0, 0, 0]
        if site in BOXES and 0 <= age <= 0.6:
            try:
                image = self.bridge.imgmsg_to_cv2(message, 'bgr8')
                state, scores = classify(image, site, self.min_brightness[site],
                                         self.min_score_margin)
            except Exception as exc:
                rospy.logwarn_throttle(5.0, '[signal vision] %s' % exc)
        self.state_pub.publish(String(data=state))
        self.debug_pub.publish(String(data=json.dumps({
            'site': site, 'state': state, 'scores': scores,
            'frame_age_s': round(age, 3), 'stamp': self.frame_stamp.to_sec(),
        })))


if __name__ == '__main__':
    try:
        SignalVision()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
