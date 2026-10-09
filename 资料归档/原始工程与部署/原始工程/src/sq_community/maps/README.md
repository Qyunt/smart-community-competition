# maps —— 建好的地图放这里

本目录初始为空，跑完建图后由 `map_saver` 写入。

```bash
# 1) 起仿真 + 机器人
roslaunch sq_community sq_community.launch

# 2) 另开终端：建图
roslaunch sq_community sq_gmapping.launch

# 3) 再开终端：键盘遥控跑遍全场（A街 → 连接路 → B街 → 回出发区）
rosrun teleop_twist_keyboard teleop_twist_keyboard.py

# 4) 存图（会生成 sq_community.pgm 与 sq_community.yaml 到本目录）
rosrun map_server map_saver -f $(find sq_community)/maps/sq_community
```

存好后 `sq_navigation.launch` 的默认 `map_file` 就指向 `maps/sq_community.yaml`：

```bash
roslaunch sq_community sq_navigation.launch
```

> 复赛提交要求工程代码 zip 里包含地图文件，所以地图务必存在本目录并一起打包。
