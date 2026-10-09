#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧社区 · 相机视觉识别接入示例（把单文件 OpenCV 例程 ROS 化）
=================================================================
社区识别例程里的 6 个 *_cam.py 都是"打开本机摄像头 + cv2.imshow"的单文件脚本，
在 Gazebo 里没法直接用。本节点把它们接到仿真相机上：

相机话题（waffle 自带）:
  /camera/rgb/image_raw      RGB 图像  1920x1080
  /camera/depth/image_raw    深度图像
  /camera/depth/points       点云

用法:
  rosrun sq_community sq_vision_demo.py                       # 只抓拍存图
  rosrun sq_community sq_vision_demo.py _weights:=/path/xx.pt # 顺带跑 YOLO
  rosservice call /sq/vision/snapshot "{}"                    # 立刻抓一张

发布  /sq/vision/result    std_msgs/String   识别结果文本（可直接接播报）
参数  ~output_dir  抓拍目录，默认 ~/sq_frames
      ~rate        自动抓拍间隔(秒)，0 = 只在服务调用时抓，默认 0
      ~weights     YOLO 权重路径，留空则只抓图不推理
      ~conf        置信度阈值，默认 0.35
      ~classes     类别名，逗号分隔（用于把类别 id 映射成中文名）
=================================================================
"""
from __future__ import print_function

import os
import time
import rospy
from std_msgs.msg import String
from std_srvs.srv import Empty, EmptyResponse
from sensor_msgs.msg import Image

try:
    from cv_bridge import CvBridge
    import cv2
except ImportError as e:
    raise SystemExit("需要 cv_bridge 与 opencv: sudo apt install "
                     "ros-$ROS_DISTRO-cv-bridge python-opencv  (%s)" % e)


class VisionDemo(object):

    def __init__(self):
        rospy.init_node("sq_vision_demo", anonymous=False)
        self.out_dir = os.path.expanduser(rospy.get_param("~output_dir", "~/sq_frames"))
        self.rate = float(rospy.get_param("~rate", 0.0))
        self.weights = rospy.get_param("~weights", "")
        self.conf = float(rospy.get_param("~conf", 0.35))
        self.classes = [c for c in str(rospy.get_param("~classes", "")).split(",") if c]

        if not os.path.isdir(self.out_dir):
            os.makedirs(self.out_dir)

        self.bridge = CvBridge()
        self.latest = None
        self.n = 0

        # 可选：加载 YOLO 权重
        self.model = None
        if self.weights:
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.weights)
                rospy.loginfo("[视觉] 已加载 YOLO 权重 %s" % self.weights)
            except Exception as e:
                rospy.logwarn("[视觉] 加载 YOLO 失败(%s)，只做抓拍存图。"
                              "需要的话: pip install ultralytics" % e)

        self.pub = rospy.Publisher("/sq/vision/result", String, queue_size=10)
        rospy.Subscriber("/camera/rgb/image_raw", Image, self.on_image, queue_size=1)
        rospy.Service("/sq/vision/snapshot", Empty, self.on_snapshot)

        rospy.loginfo("[视觉] 抓拍目录: %s ; 自动抓拍间隔: %s s" % (self.out_dir, self.rate))
        if self.rate > 0:
            rospy.Timer(rospy.Duration(self.rate), self.timer_cb)

    # ---------------------------------------------------------------- 回调
    def on_image(self, msg):
        try:
            self.latest = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            rospy.logwarn_throttle(5.0, "[视觉] 图像转换失败: %s" % e)

    def timer_cb(self, _evt):
        self.snapshot()

    def on_snapshot(self, _req):
        self.snapshot()
        return EmptyResponse()

    # ---------------------------------------------------------------- 核心
    def snapshot(self):
        img = self.latest
        if img is None:
            rospy.logwarn_throttle(5.0, "[视觉] 还没收到 /camera/rgb/image_raw，"
                                        "确认用的是 waffle 且 Gazebo 已启动")
            return
        self.n += 1
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(self.out_dir, "sq_%s_%03d.jpg" % (stamp, self.n))
        cv2.imwrite(path, img)

        txt = "抓拍 %s" % os.path.basename(path)
        if self.model is not None:
            try:
                res = self.model.predict(img, conf=self.conf, verbose=False)
                hits = []
                for r in res:
                    for b in r.boxes:
                        cid = int(b.cls[0])
                        name = self.classes[cid] if cid < len(self.classes) else str(cid)
                        hits.append("%s(%.2f)" % (name, float(b.conf[0])))
                if hits:
                    txt = "识别到: " + ", ".join(hits)
                else:
                    txt = "未识别到目标"
            except Exception as e:
                txt = "推理失败: %s" % e
        rospy.loginfo("[视觉] %s" % txt)
        self.pub.publish(String(data=txt))


if __name__ == "__main__":
    try:
        VisionDemo()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
