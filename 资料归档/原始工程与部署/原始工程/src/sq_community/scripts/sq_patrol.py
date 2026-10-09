#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧社区 · 多点自主巡检节点（sq_patrol）
=================================================================
用 move_base 的 action 接口依次导航到若干巡检点（对应场地里的各个任务点），
每到一个点就发布一次播报，便于录制复赛视频时讲解。

★ 航点表来自 route/sq_route_patrol.csv（**单一真源**），该表已用
  tools/check_sq_venue.py 做过纸上验收：25 个航点全部可达、逐段最小净空
  0.280 m（最窄在"车牌"点，避让 A 街违停电动车）。
  表里名字以「过路」开头的点只导航、不播报（纯路径点，避免视频噪音）。

★ 每个观测点都带 yaw，指向该任务元素真正的观察面（口径来自
  docs/元素-任务对照表.csv）：
    站房仪表 / 垃圾桶 / 楼宇 A·B 火点 → 在 A 街，朝 +y 看楼或朝 -y 看服务带
    楼宇 C·D 火点 / 温度面板          → 在 B 街，朝 -y
    车牌                              → 车头朝 +y，必须自 A 街俯视（朝 -y）

用法:
  roslaunch sq_community sq_navigation.launch map_file:=...   # 先起导航
  rosrun  sq_community sq_patrol.py                           # 再跑巡检
  rosrun  sq_community sq_patrol.py _loop:=true               # 循环跑

发布:
  /sq/patrol/current   std_msgs/String  当前目标点名
  /sq/patrol/result    std_msgs/String  到达某个点时的播报文本

参数:
  ~route_file     航点表，默认 $(find sq_community)/route/sq_route_patrol.csv
  ~loop           是否循环，默认 false
  ~timeout        单点超时(秒)，默认 90
  ~goal_tolerance 到达容差(米)，默认 0.18
=================================================================
"""
from __future__ import print_function

import io
import logging
import math
import os
import sys
import time

import actionlib
import rospy
from std_msgs.msg import String
from geometry_msgs.msg import Quaternion
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler

TRANSIT_PREFIX = "过路"        # ★ byte str，别加 u 前缀（见 load_route 注释）


def wait_action_server(client, timeout_s):
    """等 action server 上线 —— ★★ 必须用**墙钟**计时，绝不能用 wait_for_server(Duration)。

    踩过的坑（"一次成功一次失败"的抽风故障，最费时间的那种）：
      原来写的是
          if not client.wait_for_server(rospy.Duration(60.0)): 报错退出
      在 /use_sim_time = true 下会**假超时**：
        · Python 版 actionlib 里是 `timeout_time = rospy.get_rostime() + timeout`，
          用的是 **ROS 时间**；
        · 节点刚起来的那一瞬间 /clock 还没到，rospy.get_rostime() == 0，
          于是 timeout_time = 0 + 60 = 60（ROS 时间）；
        · 紧接着 /clock 一到，仿真时间已经是 **60.8 s**（gzserver 早就起了），
          60.8 > 60 —— 截止线在建立的那一刻就已经是过去时，
          wait_for_server 立刻返回 False，**哪怕 move_base 明明活着**。
      日志上的铁证是 `[墙钟, ROS时间]` 从 `..., 0.000000` 直接跳到 `..., 60.806000`：
          [INFO] [1790217861.607460, 0.000000]: [巡检] 等待 move_base ...
          [ERROR][1790217861.628552, 60.806000]: [巡检] move_base 没起来
      —— 间隔只有 20 ms，而"等 60 秒"根本没发生。
      它真正的本质是：**在跟首条 /move_base/status 赛跑，而超时窗口被压成了 0**。
      因为窗口极小，所以它看起来是随机抽风：同一份代码上一遍好、这一遍就崩。

    正确做法：外层用 time.time()（墙钟，不受 /clock 影响）记账，
    内层每次只等 1 s；一旦 ROS 时间稳定下来，内层就会正常等满 1 s 并连上。
    """
    t0 = time.time()
    while not rospy.is_shutdown():
        if client.wait_for_server(rospy.Duration(1.0)):
            return True
        if time.time() - t0 > timeout_s:
            return False
        time.sleep(0.2)          # ★ 墙钟 sleep；别用 rospy.sleep（它走 ROS 时间）
    return False


def flush_logs():
    """把 stdout 和所有 logging handler 立刻刷出去。

    ★ 踩过的坑：rospy 的 loginfo 在**输出重定向到文件**时是块缓冲的
      （Python 2 默认 4 KB），跑的时候 `tail patrol.log` 永远是空的，
      只能等进程退出才一次性刷出来 —— 录视频/盯进度时非常难受。
      试过 `export PYTHONUNBUFFERED=1`：**不生效**，因为 rospy 自己握着
      stdout / StreamHandler 的引用，解释器级别的 -u 管不到它。
      所以只能在这里手动 flush（stdout 和 handler 两边都刷，稳妥）。
    """
    try:
        sys.stdout.flush()
    except Exception:
        pass
    loggers = [logging.getLogger()]
    try:
        loggers += [logging.getLogger(n) for n in list(logging.Logger.manager.loggerDict)]
    except Exception:
        pass
    for lg in loggers:
        for h in list(getattr(lg, "handlers", []) or []):
            try:
                h.flush()
            except Exception:
                pass


def say_info(msg):
    # ⚠ 这三个包装函数体里必须调 **rospy.loginfo**，不能调 say_info 自己！
    #   踩过：用 replace_all 把 `rospy.loginfo(` 全替换成 `say_info(` 时，
    #   把函数体里那一行也换了 → 自己调自己 → 无限递归 → 节点 1 秒就崩
    #   （RecursionError 的 traceback 长到把 patrol.log 刷成几 MB）。
    rospy.loginfo(msg)
    flush_logs()


def say_warn(msg):
    rospy.logwarn(msg)
    flush_logs()


def say_err(msg):
    rospy.logerr(msg)
    flush_logs()


def load_route(path):
    """读 名称,x,y,yaw,播报 表；兼容 # 注释行与首行表头。

    ★ Python 2 坑：io.open(encoding="utf-8") 读出来是 unicode，与 utf-8 的
      byte str 格式串做 `%` 会触发 ascii 解码 → UnicodeDecodeError。
      统一 .encode("utf-8") 回 byte str。
    """
    out = []
    if not os.path.isfile(path):
        return out
    for ln in io.open(path, encoding="utf-8"):
        ln = ln.strip().encode("utf-8")
        if not ln or ln.startswith("#"):
            continue
        parts = [t.strip() for t in ln.split(",")]
        if len(parts) < 3:
            continue
        try:
            x, y = float(parts[1]), float(parts[2])
        except ValueError:
            continue                       # 表头
        yaw = float(parts[3]) if len(parts) > 3 and parts[3] else 0.0
        say = parts[4] if len(parts) > 4 else ""
        out.append((parts[0], x, y, yaw, say))
    return out


class Patrol(object):

    def __init__(self):
        rospy.init_node("sq_patrol", anonymous=False)
        self.loop = rospy.get_param("~loop", False)
        self.timeout = float(rospy.get_param("~timeout", 90.0))
        self.tol = float(rospy.get_param("~goal_tolerance", 0.18))

        default_route = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "route", "sq_route_patrol.csv")
        self.route_path = rospy.get_param("~route_file", default_route)
        self.route = load_route(self.route_path)
        if not self.route:
            say_err("[巡检] 航点表为空或不存在: %s" % self.route_path)
            rospy.signal_shutdown("no route")
            return
        say_info("[巡检] 载入 %d 个航点: %s" % (len(self.route), self.route_path))
        n_stop = sum(1 for w in self.route if not w[0].startswith(TRANSIT_PREFIX))
        say_info("[巡检] 其中观测点 %d 个，过路点 %d 个"
                      % (n_stop, len(self.route) - n_stop))

        self.pub_cur = rospy.Publisher("/sq/patrol/current", String,
                                       queue_size=10, latch=True)
        self.pub_res = rospy.Publisher("/sq/patrol/result", String, queue_size=10)

        self.client = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        say_info("[巡检] 等待 move_base ...")
        # ★ 用墙钟计时等待，别用 wait_for_server(rospy.Duration(60))（会假超时，见函数注释）
        if not wait_action_server(self.client, 90.0):
            say_err("[巡检] move_base 没起来（已等 90 s），"
                    "先 roslaunch sq_community sq_navigation.launch")
            rospy.signal_shutdown("no move_base")
            return
        say_info("[巡检] move_base 已连接")

    def make_goal(self, x, y, yaw):
        g = MoveBaseGoal()
        g.target_pose.header.frame_id = "map"
        g.target_pose.header.stamp = rospy.Time.now()
        g.target_pose.pose.position.x = x
        g.target_pose.pose.position.y = y
        g.target_pose.pose.position.z = 0.0
        q = quaternion_from_euler(0.0, 0.0, yaw)
        g.target_pose.pose.orientation = Quaternion(*q)
        return g

    def go(self, wp):
        name, x, y, yaw, say = wp
        transit = name.startswith(TRANSIT_PREFIX)
        if not transit:
            say_info("[巡检] >>> 前往 %s (%.2f, %.2f, yaw=%.2f)" % (name, x, y, yaw))
            self.pub_cur.publish(String(data=name))
        else:
            say_info("[巡检] 过路 %s (%.2f, %.2f)" % (name, x, y))
        self.client.send_goal(self.make_goal(x, y, yaw))
        ok = self.client.wait_for_result(rospy.Duration(self.timeout))
        if not ok:
            self.client.cancel_goal()
            say_warn("[巡检] %s 超时" % name)
            return False
        st = self.client.get_state()
        if st == actionlib.GoalStatus.SUCCEEDED:
            say_info("[巡检] 到达 %s %s" % (name, ("—— " + say) if say else ""))
            if say and not transit:
                self.pub_res.publish(String(data="%s: %s" % (name, say)))
            return True
        say_warn("[巡检] %s 失败 (state=%d)" % (name, st))
        return False

    def run(self):
        while not rospy.is_shutdown():
            ok_n = 0
            for wp in self.route:
                if rospy.is_shutdown():
                    return
                if self.go(wp):
                    ok_n += 1
                rospy.sleep(0.3)
            say_info("[巡检] 一轮结束，成功 %d/%d 个点" % (ok_n, len(self.route)))
            if not self.loop or rospy.is_shutdown():
                break
        say_info("[巡检] 结束")


if __name__ == "__main__":
    try:
        p = Patrol()
        if not rospy.is_shutdown():
            p.run()
    except rospy.ROSInterruptException:
        pass
