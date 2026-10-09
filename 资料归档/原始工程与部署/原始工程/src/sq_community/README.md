# sq_community —— 智慧社区 Gazebo 仿真场地

> **4.2 m 比赛修订版入口：**请先读 [SCENE_4P2_README.md](SCENE_4P2_README.md)，
> 使用 `roslaunch sq_community sq_autonomous_4p2.launch` 启动新的麦轮车、双信号灯、
> 相机判灯及 33 点巡检。本页下方描述的是早期 10.0 m × 7.2 m 场景，坐标和模型
> 不适用于 4.2 m 比赛修订版。

> 全球校园人工智能算法精英大赛 · 算法应用赛（赛马制）· **智慧社区**
> 面向复赛「任务一：巡检场景设计与演示（50 分）」的仿真工程。

场地尺寸 **10.0 m × 7.2 m**，覆盖总决赛全部 10 类识别任务所需的物料模型，
所有识别目标都带**真实可读的文字/数字/颜色**（车牌号、仪表读数、禁行标志、火灾窗口、
楼号、投放正确的垃圾等），不是空壳几何体。

---

## 1. 依赖与编译

```bash
# 依赖（Melodic/Noetic 通用）
sudo apt install ros-$ROS_DISTRO-gmapping ros-$ROS_DISTRO-navigation \
     ros-$ROS_DISTRO-map-server ros-$ROS_DISTRO-amcl ros-$ROS_DISTRO-move-base \
     ros-$ROS_DISTRO-dwa-local-planner ros-$ROS_DISTRO-teleop-twist-keyboard \
     ros-$ROS_DISTRO-robot-state-publisher ros-$ROS_DISTRO-cv-bridge

# 机器人必须选 waffle（只有它带深度相机，视觉识别要用）
export TURTLEBOT3_MODEL=waffle
echo 'export TURTLEBOT3_MODEL=waffle' >> ~/.bashrc

cd ~/sq_ws && catkin_make && source devel/setup.bash

# 从 Windows 拷过来的脚本没有执行位，必须补上
chmod +x src/sq_community/scripts/*.py
```

## 2. 三步跑起来

```bash
# ① 起场地 + 机器人（出生在出发区 -4.60, 1.80，车头朝 A 街东向）
roslaunch sq_community sq_community.launch

# ② 建图（另开终端）
roslaunch sq_community sq_gmapping.launch
rosrun teleop_twist_keyboard teleop_twist_keyboard.py     # 键盘遥控跑遍全场
rosrun map_server map_saver -f $(find sq_community)/maps/sq_community

# ③ 导航 + 多点巡检（另开终端）
roslaunch sq_community sq_navigation.launch
rosrun sq_community sq_patrol.py
```

辅助：

```bash
rosrun sq_community traffic_light_controller.py     # 已含在 ① 里，可单独跑
rosrun sq_community sq_vision_demo.py _weights:=/path/xx.pt   # 相机抓拍/识别
rosservice call /sq/vision/snapshot "{}"            # 立刻抓一张存到 ~/sq_frames
```

## 3. 场地布局（坐标系：x 向东，y 向北，原点在场地中心）

| 区域 | 位置 | 内容 |
|---|---|---|
| 出发区 | x=-4.20 横线，机器人 x=-4.60, y=1.80 | 出发地贴 + 白色出发横线 |
| A 街（主干道） | y ∈ [1.20, 2.40]，中心线 y=1.80 | 黄色中心虚线、路缘实线 |
| B 街 | y ∈ [-2.40, -1.20]，中心线 y=-1.80 | 同上 |
| 连接路 | x ∈ [-0.60, 0.60] | 连通 A、B 两街；南端有斑马线 |
| 楼宇 A | 中心 (-3.20, 3.10)，正面朝 A 街 | 2 层 10 窗，**3 个火点** |
| 楼宇 B | 中心 (2.90, 3.10)，正面朝 A 街 | **5 个火点** |
| 楼宇 C | 中心 (-3.20, -3.10)，正面朝 B 街 | **2 个火点** |
| 楼宇 D | 中心 (2.90, -3.10)，正面朝 B 街 | **2 楼高温窗 + 68℃ 温度牌** |
| 站房 | 中心 (-3.30, 0.55)，仪表在北面 y=0.815 | **2 块表：01357 / 24680** |
| 垃圾桶 ×4 | y=0.85，x=-2.30 / -2.00 / -1.70 / -1.40 | 可回收(关)、有害(开·正确)、厨余(开·错误)、其他(关) |
| 人偶立牌 ×16 | A 街 8（y=2.50 与 y=1.10）、B 街 8（y=-1.10 与 y=-2.50） | **A 街 2 人穿橙色 = 外来人员** |
| 红绿灯 ×2 | (1.10, 2.62) 朝西、(1.10, -2.62) 朝东 | 红 10s → 绿 15s → 黄 3s |
| 等待线 | A 街 x=-0.75、B 街 x=+0.75 | 红灯时车头不得越过 |
| 停车场 | 车位 x=3.25 / 3.80 / 4.35，y=-0.35 | **3 辆车，车牌 苏E·12345 / 67890 / A8888** |
| 电动车停车区 | x ∈ [1.15, 2.45]，y=±0.55 | **8 辆正常 + 2 辆倒伏** |
| 电动车违停 | (2.75, 1.35)、(3.15, 1.35) | **A 街区 2 辆违停，B 街区 0 辆** |
| 指示牌 ×6 | 沿途路侧 | 限速30 / 禁止直行 / 左转 / 人行横道 / 禁止驶入 / 右转 |
| 泊车位（终点） | 中心 (4.45, 2.80)，尺寸 0.55×0.70 | A 街北侧，**车头朝街道** |

> 完整机器可读真值见 **`docs/scene_manifest.json`**，其中 `answer_key` 字段直接给出每一项
> 任务的播报答案，可用于校验你的识别结果，也可直接摘进复赛技术方案文档。
> 场地俯视图见 **`docs/sq_community_plan.svg`**（用浏览器打开）。

## 4. 元素 → 赛项对照

| 总决赛任务 | 分值 | 场地对应 |
|---|---|---|
| 红绿灯识别 | 10（2×5） | `sq_traffic_light_{red,green,yellow}` + 控制器 |
| 人群数量识别 | 12（2×6） | `sq_persons`：A 街 8 / B 街 8，外来 2（橙色） |
| 垃圾桶状态识别 | 10 | `sq_bins`：4 类，含开/闭与投放正确性 |
| 楼宇火灾识别 | 12（3×4） | 楼宇 A/B/C 的 `SQ_win_fire` 窗户 |
| 车辆车牌识别 | 12（3×4） | 停车场 3 辆车 + 3 张车牌贴图 |
| 楼宇异常温度 | 10 | 楼宇 D 的 `SQ_win_hot` + `SQ_panel_temp` |
| 站房仪表读取 | 14（2×7） | 站房 2 块 `SQ_gauge_{1,2}` |
| 电动车状态识别 | 10 | 停车区正常 8 / 倒伏 2，A 街违停 2 |
| 停车 | 10 | 终点泊车位 (4.45, 2.80)，朝向要求 |
| 指示牌识别 | — | 6 块 `SQ_sign_*` |

## 5. 话题（waffle 模型自带）

| 话题 | 类型 | 说明 |
|---|---|---|
| `/scan` | sensor_msgs/LaserScan | 360°，量程 0.12 ~ **3.5 m** |
| `/camera/rgb/image_raw` | sensor_msgs/Image | 1920×1080，**视觉识别用这个** |
| `/camera/depth/image_raw` | sensor_msgs/Image | 深度图 |
| `/camera/depth/points` | sensor_msgs/PointCloud2 | 点云 |
| `/odom`、`/imu` | — | 里程计 / IMU |
| `/cmd_vel` | geometry_msgs/Twist | 速度指令 |
| `/sq/traffic_light/state` | std_msgs/String | 灯色真值（latched） |
| `/sq/patrol/current`、`/sq/patrol/result` | std_msgs/String | 巡检进度 |
| `/sq/vision/result` | std_msgs/String | 视觉识别结果 |

## 6. 目录结构

```
sq_community/
├── worlds/sq_community.world     场地主世界（10 个模型组 / 256 个 link）
├── models/
│   ├── sq_textures/              35 张贴图与 Ogre 材质脚本
│   ├── sq_traffic_light_red/     红/黄/绿三套可切换红绿灯
│   ├── sq_traffic_light_green/
│   └── sq_traffic_light_yellow/
├── launch/                       sq_community / sq_gmapping / sq_navigation
├── scripts/                      traffic_light_controller / sq_patrol / sq_vision_demo
├── maps/                         建图输出（提交时务必带上）
├── docs/                         平面图 SVG、对照表 CSV、真值 JSON、自检报告
└── tools/                        场地生成器与静态自检器（可重新生成/校验）
```

## 7. 修改与重建场地

场地不是手写死的，由 `tools/gen_scene.py` 里的 `LAYOUT` 常量表生成：

```bash
python tools/gen_textures.py --out models      # 重新生成 35 张贴图与材质
python tools/gen_scene.py    --pkg .           # 重建 world / 红绿灯 / 平面图 / 真值
python tools/verify_pkg.py   --pkg .           # 静态自检（不需要 ROS 也能跑）
```

改坐标、改火点数量、加楼宇… 都只改 `gen_scene.py` 顶部的常量，然后重跑即可。

## 8. 常见问题

**Q: `spawn_model` 报 robot_description 为空**
A: 确认 `TURTLEBOT3_MODEL=waffle` 已 export，且已 `source devel/setup.bash`。

**Q: RViz 里没有激光/黑屏**
A: 检查 Fixed Frame 设为 `map`（建图时）或 `odom`；确认 Gazebo 已完全加载场地。

**Q: 模型全是灰色、没有贴图**
A: `sq_textures` 没被找到。确认 `package.xml` 里的
`<gazebo_ros gazebo_model_path="${prefix}/models"/>` 存在，且 `echo $GAZEBO_MODEL_PATH`
能看到 `.../sq_community/models`。

**Q: 机器人卡在标线上动不了**
A: 已处理——厚度 <5 cm 的薄片（标线/路面/绿化带）全部只做视觉不做碰撞。
若你新加了物件，注意别把碰撞体做得太薄。

**Q: 激光只有 3.5 m，能建完整张图吗**
A: 能，但需要开得慢一点、贴墙走。`sq_gmapping.launch` 已把地图范围放宽到 ±6.0 × ±4.5 m。
