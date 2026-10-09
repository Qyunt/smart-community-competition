#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Switch the face material inside each of two fixed traffic-light models."""
from __future__ import print_function

import math
import rospy
from gazebo_msgs.msg import LinkState
from gazebo_msgs.srv import SetLinkState
from std_msgs.msg import Bool, Float32, String
from tf.transformations import quaternion_from_euler


LIGHTS = (
    ("sq4_tl_upper", -.6, 1.8, 0.0),
    ("sq4_tl_lower", 0.0, -1.2, math.pi / 2),
)
STATES = ("red", "green", "yellow")


class Controller(object):
    def __init__(self):
        rospy.init_node("sq_traffic_light_4p2")
        self.cycle = (
            ("red", float(rospy.get_param("~cycle_red", 10.0))),
            ("green", float(rospy.get_param("~cycle_green", 15.0))),
            ("yellow", float(rospy.get_param("~cycle_yellow", 3.0))),
        )
        self.enabled = True
        rospy.Subscriber("/sq/traffic_light/enable", Bool, self.on_enable)
        self.state_pub = rospy.Publisher("/sq/traffic_light/state", String, queue_size=10, latch=True)
        self.left_pub = rospy.Publisher("/sq/traffic_light/time_left", Float32, queue_size=10)
        rospy.set_param("/sq/traffic_light/cycle_s", dict(self.cycle))
        rospy.wait_for_service("/gazebo/set_link_state")
        self.set_link = rospy.ServiceProxy("/gazebo/set_link_state", SetLinkState)

    def on_enable(self, msg):
        self.enabled = bool(msg.data)

    def move_panel(self, name, x, y, yaw, visible):
        # A hidden panel is recessed into the opaque 5 cm-deep housing.
        # Moving links leaves exactly two light models on the map.
        local_x = 0.0 if visible else -0.05
        state = LinkState()
        state.link_name = name
        state.reference_frame = "world"
        state.pose.position.x = x + local_x * math.cos(yaw)
        state.pose.position.y = y + local_x * math.sin(yaw)
        state.pose.position.z = 0.0
        q = quaternion_from_euler(0, 0, yaw)
        state.pose.orientation.x = q[0]
        state.pose.orientation.y = q[1]
        state.pose.orientation.z = q[2]
        state.pose.orientation.w = q[3]
        response = self.set_link(state)
        if not response.success:
            raise RuntimeError("cannot position %s: %s" % (name, response.status_message))

    def set_color(self, color):
        for base, x, y, yaw in LIGHTS:
            for state in STATES:
                if state != color:
                    self.move_panel(base + "::front_" + state, x, y, yaw, False)
            self.move_panel(base + "::front_" + color, x, y, yaw, True)
        self.state_pub.publish(String(data=color))
        rospy.loginfo("[sq4 lights] state=%s" % color)

    def run(self):
        rate = rospy.Rate(10)
        idx = 0
        self.set_color(self.cycle[idx][0])
        phase_start = rospy.get_time()
        while not rospy.is_shutdown():
            if not self.enabled:
                self.left_pub.publish(Float32(data=0.0))
                rate.sleep()
                phase_start += .1
                continue
            color, duration = self.cycle[idx]
            left = duration - (rospy.get_time() - phase_start)
            if left <= 0:
                idx = (idx + 1) % len(self.cycle)
                self.set_color(self.cycle[idx][0])
                phase_start = rospy.get_time()
                left = self.cycle[idx][1]
            self.left_pub.publish(Float32(data=max(0.0, left)))
            rate.sleep()


if __name__ == "__main__":
    try:
        Controller().run()
    except rospy.ROSInterruptException:
        pass
