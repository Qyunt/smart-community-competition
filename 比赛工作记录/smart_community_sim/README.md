# 智慧社区 SLAM 练习场景（ROS Melodic）

这是根据复赛规则的**布局示意图**制作的简化 Gazebo Classic 场景，供团队先跑通机器人、激光雷达、Gmapping 和地图保存。场景约 7.1 m × 5.7 m；楼栋、行人、汽车、交通灯和道路标线的位置、尺寸均为练习用估计值。它**不是**组委会提供的正式赛场模型，也不是复赛的最终高保真作品。红绿灯目前是静态彩色模型，车牌是空白占位板，行人是简单几何体；视觉识别和自主导航还需继续开发。

## 第一步：把工程放进虚拟机

将整个 `smart_community_sim` 文件夹复制到 Ubuntu 的 `~/catkin_ws/src/`，然后在 Ubuntu 终端执行：

```bash
source /opt/ros/melodic/setup.bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
rospack find smart_community_sim
```

最后一条应显示 `~/catkin_ws/src/smart_community_sim` 的实际路径。若是压缩包，可先把 `smart_community_sim.zip` 放到 Ubuntu 的 `~/Downloads/`，再执行：

```bash
mkdir -p ~/catkin_ws/src
unzip ~/Downloads/smart_community_sim.zip -d ~/catkin_ws/src
```

## 第二步：打开仿真（终端 1）

关闭先前练习用的 Gazebo 和 SLAM 窗口，在新终端执行：

```bash
source ~/catkin_ws/devel/setup.bash
export TURTLEBOT3_MODEL=burger
SVGA_VGPU10=0 LIBGL_ALWAYS_SOFTWARE=1 roslaunch smart_community_sim community_world.launch
```

Gazebo 应出现社区几何场景和一台 TurtleBot3 Burger。启动过程中的 Gazebo Fuel 网络证书错误通常与联网模型列表有关；本场景只使用本地基本几何体。判断是否能继续，应看 Gazebo 是否显示场景，以及 ROS 话题是否实际发布。

另开终端检查：

```bash
source ~/catkin_ws/devel/setup.bash
timeout 5s rostopic echo -n 1 /scan/header
timeout 5s rostopic echo -n 1 /odom/child_frame_id
```

预期分别看到 `frame_id: "base_scan"` 和 `"base_footprint"`。若 `/scan` 有消息而 `/odom` 没有，先确认 Gazebo 左下角处于播放状态，再在**另一终端**执行以下恢复操作，不要关闭终端 1：

```bash
rosservice call /gazebo/delete_model "model_name: 'turtlebot3_burger'"
rosrun gazebo_ros spawn_model -urdf -model turtlebot3_burger -param robot_description -x 2.65 -y 2.05 -z 0.0 -Y 3.14159
timeout 5s rostopic echo -n 1 /odom/child_frame_id
```

这是针对之前在当前虚拟机上出现过的“模型已生成但差速驱动插件没有发布里程计”的恢复办法。

## 第三步：建图（终端 2）

```bash
source ~/catkin_ws/devel/setup.bash
export TURTLEBOT3_MODEL=burger
SVGA_VGPU10=0 LIBGL_ALWAYS_SOFTWARE=1 roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping
```

RViz 的 Map 应从 `Status: Warn` 变成 `Status: Ok`，并逐渐出现道路、楼栋和边界。若 RViz 黑屏或崩溃，保留上面的软件渲染环境变量再启动。

## 第四步：先手动探索，再保存地图（终端 3 / 4）

终端 3：

```bash
source ~/catkin_ws/devel/setup.bash
export TURTLEBOT3_MODEL=burger
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch
```

保持这个终端在前台，用屏幕显示的按键缓慢行驶，避免撞墙。这个步骤是**人工验证 SLAM**，还不算复赛要求的自主建图。RViz 地图覆盖了目标区域后，在终端 4 保存：

```bash
mkdir -p ~/slam_maps
rosrun map_server map_saver -f ~/slam_maps/community_practice
ls -lh ~/slam_maps/community_practice.*
```

应得到 `community_practice.pgm` 和 `community_practice.yaml`。建议同时截取 Gazebo 场景、RViz 地图、保存成功的终端输出，作为阶段性记录。

## 后续要替换和完成的内容

1. 用组委会正式尺寸、布局和资源替换所有估计位置和占位模型。
2. 增加可控制的红绿灯、真实人形模型、可辨识车牌与建筑/道路标志，并验证相机画面。
3. 增加自主探索和导航避障节点；不能将键盘遥控录像当作自主运行。
4. 把最终地图、源代码、启动文件、说明文档和演示视频按规则整理交付。

场景由 `scripts/generate_world.py` 生成。如果团队修改了物体位置或尺寸，在 Ubuntu 中运行 `python3 scripts/generate_world.py`，重新生成 `worlds/smart_community.world` 后再启动仿真。
