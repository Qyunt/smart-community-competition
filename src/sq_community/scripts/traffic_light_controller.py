#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧社区 · 红绿灯控制器
=================================================================
灯时序严格按赛题规则：  红灯 10s  ->  绿灯 15s  ->  黄灯 3s
两处红绿灯（A街东行 / B街西行）同步切换。

实现方式：调用 Gazebo 的 /gazebo/delete_model 删除当前灯，
          再 /gazebo/spawn_sdf_model 在相同位姿生成新颜色的灯。
          （红/黄/绿 三套模型已随包提供，纯基本几何，无外部依赖）

订阅  /sq/traffic_light/enable   std_msgs/Bool   默认 true；置 false 暂停循环并保持当前灯色
发布  /sq/traffic_light/state    std_msgs/String latched: "red" / "green" / "yellow"
      /sq/traffic_light/time_left std_msgs/Float32 当前相位剩余秒数
参数  ~cycle_red / ~cycle_green / ~cycle_yellow  相位时长（秒）
      ~start_phase  启动时的首个相位，默认 red
      ~sync         两灯是否同步，默认 true
=================================================================
"""
from __future__ import print_function

import os
import sys
import rospy
import rospkg
from std_msgs.msg import String, Bool, Float32
from geometry_msgs.msg import Pose
from gazebo_msgs.srv import SpawnModel, DeleteModel
from tf.transformations import quaternion_from_euler

# 两处红绿灯： (模型名, x, y, yaw)  —— yaw=pi 面向西, yaw=0 面向东
LIGHTS = [
    ("sq_tl_1", 1.10, 2.62, 3.14159),   # A 街东行车看得见
    ("sq_tl_2", 1.10, -2.62, 0.0),      # B 街西行车看得见
]
DEFAULT_CYCLE = [("red", 10.0), ("green", 15.0), ("yellow", 3.0)]


def load_sdf(pkg_models, color):
    """读取 sq_traffic_light_<color>/model.sdf 并去掉 XML 声明，服务端更好解析"""
    p = os.path.join(pkg_models, "sq_traffic_light_%s" % color, "model.sdf")
    with open(p, "r") as f:
        txt = f.read()
    txt = txt.replace('<?xml version="1.0" ?>', "").replace("<?xml version='1.0'?>", "")
    return txt.strip()


class TrafficLightController(object):

    def __init__(self):
        rospy.init_node("sq_traffic_light", anonymous=False)

        rospack = rospkg.RosPack()
        pkg_path = rospack.get_path("sq_community")
        self.models_dir = os.path.join(pkg_path, "models")

        # 相位时长
        self.cycle = [
            ("red",    rospy.get_param("~cycle_red", 10.0)),
            ("green",  rospy.get_param("~cycle_green", 15.0)),
            ("yellow", rospy.get_param("~cycle_yellow", 3.0)),
        ]
        self.sync = rospy.get_param("~sync", True)
        start_phase = rospy.get_param("~start_phase", "red")

        # 预读三套模型
        self.sdf = {}
        for c, _ in DEFAULT_CYCLE:
            try:
                self.sdf[c] = load_sdf(self.models_dir, c)
            except Exception as e:
                rospy.logerr("[红绿灯] 读取 %s 模型失败: %s" % (c, e))
                self.sdf[c] = None

        # 服务
        rospy.loginfo("[红绿灯] 等待 Gazebo 服务 …")
        rospy.wait_for_service("/gazebo/delete_model")
        rospy.wait_for_service("/gazebo/spawn_sdf_model")
        self.del_srv = rospy.ServiceProxy("/gazebo/delete_model", DeleteModel)
        self.spawn_srv = rospy.ServiceProxy("/gazebo/spawn_sdf_model", SpawnModel)

        self.enabled = True
        self.state = start_phase
        self.pub_state = rospy.Publisher("/sq/traffic_light/state", String,
                                         queue_size=10, latch=True)
        self.pub_left = rospy.Publisher("/sq/traffic_light/time_left", Float32, queue_size=10)
        rospy.Subscriber("/sq/traffic_light/enable", Bool, self.on_enable)
        # 供其它节点（如视觉识别）读取的真值
        rospy.set_param("/sq/traffic_light/cycle_s",
                        {"red": self.cycle[0][1], "green": self.cycle[1][1],
                         "yellow": self.cycle[2][1]})

    def on_enable(self, msg):
        self.enabled = bool(msg.data)
        rospy.loginfo("[红绿灯] 循环%s" % ("恢复" if self.enabled else "暂停"))

    # ---------------------------------------------------------------- 换灯
    def set_color(self, color):
        if color not in self.sdf or self.sdf[color] is None:
            return
        q = quaternion_from_euler(0.0, 0.0, 0.0)
        for name, x, y, yaw in LIGHTS:
            qy = quaternion_from_euler(0.0, 0.0, yaw)
            pose = Pose()
            pose.position.x = x
            pose.position.y = y
            pose.position.z = 0.0
            pose.orientation.x = qy[0]
            pose.orientation.y = qy[1]
            pose.orientation.z = qy[2]
            pose.orientation.w = qy[3]
            try:
                self.del_srv(name)
            except Exception:
                pass          # 首次可能是世界自带的灯，删不掉也无妨
            try:
                self.spawn_srv(name, self.sdf[color], "", pose, "world")
            except Exception as e:
                rospy.logwarn("[红绿灯] %s -> %s 失败: %s" % (name, color, e))
            if not self.sync:
                # 不同步时另一盏灯用互补相位，这里简单留出接口
                pass
        self.state = color
        self.pub_state.publish(String(data=color))
        cn = {"red": "红灯", "green": "绿灯", "yellow": "黄灯"}[color]
        rospy.loginfo("[红绿灯] 切换为 %s（%s）" % (cn, color))

    # ---------------------------------------------------------------- 主循环
    def run(self):
        if self.sdf["red"] is None:
            rospy.logerr("[红绿灯] 红灯模型缺失，退出")
            return
        rospy.loginfo("[红绿灯] 时序 红%.0fs -> 绿%.0fs -> 黄%.0fs，共 %d 处"
                      % (self.cycle[0][1], self.cycle[1][1], self.cycle[2][1], len(LIGHTS)))
        self.pub_state.publish(String(data=self.state))
        idx = [i for i, (c, _) in enumerate(self.cycle) if c == self.state]
        idx = idx[0] if idx else 0

        while not rospy.is_shutdown():
            color, dur = self.cycle[idx]
            if self.state != color:
                self.set_color(color)
            # 按 0.1s 切片等待，保证 enable=false 能立即暂停
            t0 = rospy.get_time()
            while not rospy.is_shutdown():
                if not self.enabled:
                    self.pub_left.publish(Float32(data=0.0))
                    rospy.sleep(0.1 if not rospy.is_shutdown() else 0)
                    continue
                left = dur - (rospy.get_time() - t0)
                self.pub_left.publish(Float32(data=max(0.0, left)))
                if left <= 0.0:
                    break
                rospy.sleep(min(0.1, left))
            idx = (idx + 1) % len(self.cycle)


if __name__ == "__main__":
    try:
        TrafficLightController().run()
    except rospy.ROSInterruptException:
        pass
