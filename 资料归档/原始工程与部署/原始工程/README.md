# 智慧社区复赛工程代码

这是可继续开发的 ROS 工作空间源码包。包内 `src/` 包含 `sq_community` 场景工程，以及随包提供的 `turtlebot3*` catkin 源码依赖。它不是已编译的二进制包；目标环境需自行安装并编译。

详细交接顺序、当前进度、已知问题和排查方式见同级 `成果交接文档.md`。

## 当前工程入口与注意事项

- 当前正式场景入口为 `src/sq_community/SCENE_4P2_README.md`，场地为 4.2 m × 4.2 m。对应 world、launch、地图、路线和结构化场景信息均以文件名带 `4p2` 的版本为准。
- 包内旧 `sq_community.world`、旧地图/路线和根目录历史材料仍保留，供参考，不要把旧 10.0 m × 7.2 m 场景当作当前正式场地。
- `docs/scene_manifest_4p2.json` 标记为按示意图工程化布置；其中锚点/任务点不是规则图给出的精确尺寸。正式比赛结构与尺度应继续以规则图和队内确认参数核对。
- 机器人模型外廓在当前说明中记为 334 × 303 mm，与比赛机器人 400 × 400 mm 的确认参数不同；需要在后续工程验收中处理，不能视为一致。
- 本包未附 `build/`、`devel/`、`install/`、`.git` 或 Python 字节码缓存。VM 当前状态、最新编译结果及 Gazebo 现场验收未在本包生成时复核，因此不宣称“解压即运行”或编译通过。

## 建议开发环境

现有工程按 ROS 1 Melodic、Ubuntu 18.04、Gazebo 9 编写。其他系统/ROS 版本的兼容性未核实。开发前先阅读 `src/sq_community/SCENE_4P2_README.md` 和包内各 catkin 包的 `package.xml`，安装依赖后在工作空间根目录构建：

```bash
cd <解压目录>
catkin_make
source devel/setup.bash
```

若要启动当前 4.2 m Gazebo 场地，可从工作空间根目录运行：

```bash
roslaunch sq_community sq_community_4p2.launch
```

若无图形界面，可按场景说明使用 `gui:=false`。导航、SLAM、视觉/OCR 等组件的参数和启动方式请以 `SCENE_4P2_README.md` 及对应 launch 文件为准；其中部分视觉能力依赖工作空间外的服务/模型，不能仅凭本 ZIP 推定已配置。

## 目录说明

```text
src/
├── sq_community/             # 场景、模型、launch、脚本、地图、路线和文档
├── turtlebot3/               # 随包的第三方 catkin 源码
├── turtlebot3_msgs/          # 随包的第三方消息源码
└── turtlebot3_simulations/   # 随包的第三方仿真源码
```

随包第三方源码保留各自原有许可/版权文件。继续分发或修改前请阅读相关许可证。

## 本次打包范围

本 ZIP 从现有 Windows 工作空间的 `sq_ws/src` 复制源码和运行资产；排除了构建目录、Git 元数据、Python 缓存及临时/编译文件。桌面原工程未被修改。此包是源码开发起点，不含本机盘点清单，也不替代赛题要求的方案 PDF、答辩 PDF 或展示视频。
