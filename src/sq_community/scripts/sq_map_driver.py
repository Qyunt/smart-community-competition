#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧社区 · 建图航点驱动器（sq_map_driver）
=================================================================
为什么需要它：
  gmapping 建图阶段**还没有地图**，用不了 move_base。所以这个节点用
  「里程计闭环 + 激光前向急停」直接开 /cmd_vel，沿 route/sq_route_map.csv
  的航点把场地跑一遍，让 gmapping 把整张地图建全（含一个闭环回路，
  有利于回环检测）。

控制逻辑（每个航点一个状态机，逐点推进）：
  1) 先原地转到朝向该航点的方向（角度误差 < 0.15 rad 才算转好）
  2) 再向前开，速度随剩余距离线性收尾
  3) 距目标 < 0.12 m → 停车，切下一个航点
  4) 前向 ±25° 扇区最近距离 < 0.30 m → 停车等待；连续 5 s 仍被挡则
     判定该航点不可达，记 warn 并跳过（**绝不倒车乱撞**）
  单点超时（默认 60 s）同样跳过。航点名前缀 "过路" 表示纯过路点，
  不打印"到达"播报（避免视频里噪音）。

用法（虚拟机内）:
  roslaunch sq_community sq_community.launch gui:=false     # 起场地
  roslaunch sq_community sq_gmapping.launch                 # 起建图
  rosrun   sq_community sq_map_driver.py                    # 跑这一轮

发布:
  /sq/map/status   std_msgs/String   "RUN <i>/<n> <name>" / "DONE ok=<k> fail=<f>"
  /cmd_vel         geometry_msgs/Twist

参数:
  ~route_file  航点表，默认 $(find sq_community)/route/sq_route_map.csv
  ~v_max       直线速度上限 (m/s)，默认 0.20
  ~w_max       角速度上限 (rad/s)，默认 0.90
  ~reach_tol   到点容差 (m)，默认 0.12
  ~wp_timeout  单点超时 (s)，默认 60
  ~odom_csv    里程计落盘路径，默认 /tmp/sq_map_odom.csv
=================================================================
"""
from __future__ import print_function

import io
import math
import os
import sys
import time

import rospy
import tf.transformations as tft
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String


def wrap(a):
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def load_route(path):
    """读 名称,x,y,yaw[,播报] 表；兼容 # 注释与首行表头。

    ★ Python 2 坑（踩过）：用 io.open(encoding="utf-8") 读出来是 **unicode**，
      而下面的 loginfo 格式串是 utf-8 的 **byte str**，`"%s" % unicode` 会让
      Python 2 去按 ascii 解码那个 byte str → 
          UnicodeDecodeError: 'ascii' codec can't decode byte 0xe5 ...
      节点在第一个航点就崩（表现为"1 秒退出、地图是空的"）。
      所以这里统一 `.encode("utf-8")` 回 byte str，全程只用 byte str。
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


class MapDriver(object):

    def __init__(self):
        rospy.init_node("sq_map_driver", anonymous=False)

        default_route = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "route", "sq_route_map.csv")
        self.route_path = rospy.get_param("~route_file", default_route)
        self.v_max = float(rospy.get_param("~v_max", 0.20))
        self.w_max = float(rospy.get_param("~w_max", 0.90))
        self.tol = float(rospy.get_param("~reach_tol", 0.12))
        self.wp_timeout = float(rospy.get_param("~wp_timeout", 60.0))
        self.odom_csv = rospy.get_param("~odom_csv", "/tmp/sq_map_odom.csv")

        self.stop_dist = 0.30              # 前向安全距离
        self.half_sector = math.radians(25.0)

        self.pub_cmd = rospy.Publisher("/cmd_vel", Twist, queue_size=1)
        self.pub_st = rospy.Publisher("/sq/map/status", String, queue_size=10, latch=True)

        self.x = self.y = self.yaw = None
        self.odom_t = None
        self.front_min = 9.9
        self._csv = None
        self._csv_n = 0

        rospy.Subscriber("/odom", Odometry, self.on_odom, queue_size=20)
        rospy.Subscriber("/scan", LaserScan, self.on_scan, queue_size=5)

        if self.odom_csv:
            try:
                self._csv = io.open(self.odom_csv, "w", encoding="utf-8")
                self._csv.write(u"t,x,y,yaw,vx,wz\n")
            except Exception as e:
                rospy.logwarn("[建图] 里程计 CSV 打不开: %s" % e)
                self._csv = None

    # ---------------- 回调 ----------------
    def on_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.x, self.y = p.x, p.y
        self.yaw = tft.euler_from_quaternion([q.x, q.y, q.z, q.w])[2]
        self.odom_t = msg.header.stamp.to_sec()
        if self._csv is not None and self._csv_n % 5 == 0:
            v = msg.twist.twist
            self._csv.write(u"%.3f,%.4f,%.4f,%.4f,%.4f,%.4f\n"
                            % (self.odom_t, self.x, self.y, self.yaw,
                               v.linear.x, v.angular.z))
        self._csv_n += 1

    def on_scan(self, msg):
        n = len(msg.ranges)
        if n == 0:
            return
        # 只取机器人正前方 ±25° 扇区（scan 角度 0 = 车头）
        a0 = msg.angle_min
        da = msg.angle_increment
        best = 9.9
        for i in range(n):
            ang = wrap(a0 + da * i)
            if abs(ang) > self.half_sector:
                continue
            r = msg.ranges[i]
            if r is None or r != r:        # nan
                continue
            if r < msg.range_min or r > msg.range_max:
                continue
            if r < best:
                best = r
        self.front_min = best

    # ---------------- 控制 ----------------
    def stop(self):
        self.pub_cmd.publish(Twist())

    def spin_to(self, target_yaw, budget):
        """原地转到目标朝向；返回 True=到位。"""
        t0 = time.time()
        r = rospy.Rate(20)
        while not rospy.is_shutdown():
            err = wrap(target_yaw - self.yaw)
            if abs(err) < 0.15:
                self.stop()
                return True
            if time.time() - t0 > budget:
                self.stop()
                return False
            tw = Twist()
            tw.angular.z = clamp(1.6 * err, -self.w_max, self.w_max)
            self.pub_cmd.publish(tw)
            r.sleep()
        return False

    def drive_to(self, tx, ty, budget):
        """朝 (tx,ty) 开过去；返回 (ok, min_clearance_seen)。"""
        t0 = time.time()
        r = rospy.Rate(20)
        blocked_since = None
        worst = 9.9
        while not rospy.is_shutdown():
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist < self.tol:
                self.stop()
                return True, worst
            if time.time() - t0 > budget:
                self.stop()
                return False, worst

            head = math.atan2(dy, dx)
            err = wrap(head - self.yaw)
            tw = Twist()
            tw.angular.z = clamp(1.6 * err, -self.w_max, self.w_max)

            if self.front_min < self.stop_dist:
                tw.linear.x = 0.0
                if blocked_since is None:
                    blocked_since = time.time()
                    rospy.logwarn_throttle(2.0, "[建图] 前方 %.2f m 有障碍，停车等待"
                                           % self.front_min)
                elif time.time() - blocked_since > 5.0:
                    rospy.logwarn("[建图] 连续被挡 5 s，放弃该航点")
                    self.stop()
                    return False, worst
            else:
                blocked_since = None
                # 角度误差大时先转不走，避免画弧
                if abs(err) > 0.45:
                    tw.linear.x = 0.0
                else:
                    tw.linear.x = self.v_max * clamp(dist / 0.5, 0.35, 1.0)
            if self.front_min < worst:
                worst = self.front_min
            self.pub_cmd.publish(tw)
            r.sleep()
        return False, worst

    # ---------------- 主流程 ----------------
    def run(self):
        route = load_route(self.route_path)
        if not route:
            rospy.logerr("[建图] 航点表为空或不存在: %s" % self.route_path)
            return 1
        rospy.loginfo("[建图] 载入 %d 个航点: %s" % (len(route), self.route_path))

        # 等里程计
        t0 = time.time()
        while self.x is None and not rospy.is_shutdown():
            if time.time() - t0 > 30:
                rospy.logerr("[建图] 30 s 没收到 /odom，先起 gazebo")
                return 2
            rospy.sleep(0.2)
        rospy.loginfo("[建图] 起点 (%.2f, %.2f, %.3f rad)" % (self.x, self.y, self.yaw))

        ok = fail = 0
        t_start = rospy.Time.now().to_sec()
        for i, (name, x, y, yaw, say) in enumerate(route, 1):
            if rospy.is_shutdown():
                break
            transit = name.startswith("过路")
            self.pub_st.publish(String(data="RUN %d/%d %s" % (i, len(route), name)))
            rospy.loginfo("[建图] >>> %d/%d %s (%.2f, %.2f)"
                          % (i, len(route), name, x, y))

            head = yaw if abs(yaw) > 1e-6 else None
            if head is None:
                head = math.atan2(y - self.y, x - self.x)
            self.spin_to(head, 12.0)

            t_wp = rospy.Time.now().to_sec()
            budget = min(self.wp_timeout,
                         max(12.0, 6.0 * math.hypot(x - self.x, y - self.y) / self.v_max))
            good, clr = self.drive_to(x, y, budget)
            dt = rospy.Time.now().to_sec() - t_wp
            if good:
                ok += 1
                rospy.loginfo("[建图]     到达 %s  用时 %.1f s" % (name, dt))
                if say and not transit:
                    rospy.loginfo("[建图]     %s" % say)
            else:
                fail += 1
                d = math.hypot(x - self.x, y - self.y)
                rospy.logwarn("[建图]     未到 %s  残差 %.2f m  用时 %.1f s（跳过）"
                              % (name, d, dt))
            rospy.sleep(0.3)

        self.stop()
        total = rospy.Time.now().to_sec() - t_start
        msg = "DONE ok=%d fail=%d total=%.1fs" % (ok, fail, total)
        rospy.loginfo("[建图] " + msg)
        self.pub_st.publish(String(data=msg))
        if self._csv is not None:
            try:
                self._csv.flush()
                self._csv.close()
            except Exception:
                pass
            rospy.loginfo("[建图] 里程计已落盘 -> %s" % self.odom_csv)
        return 0


if __name__ == "__main__":
    try:
        sys.exit(MapDriver().run())
    except rospy.ROSInterruptException:
        pass
