> 已被人物立牌纠正版本取代。本目录保留历史截图，不代表当前正式场景。

# 实际 Gazebo 截图

共 29 张；原始图像未加工。

- `01`–`09`：临时检查摄像头拍摄的模型俯视、近照和全场。
- `robot_*`：原单点取景的前置/广角摄像头对照，部分存在裁切或车体遮挡。
- `scan_A_1`–`scan_A_4`、`scan_B_1`–`scan_B_3`：多角度人群取景；A_4 为绕开立柱遮挡的侧移位置。
- `scan_A_violations_*`：A 街区两辆违规停放道具。
- `scan_parking_*`：沿停车区分四个位置取景，末端包含两辆倒伏车。

位置定义见 `../../config/props_observation_views_4p2.json`。图像时间戳见 `capture_manifest.json`。
脚本 `../../tools/capture_props3d_review.py` 供 ROS Melodic Python 2 环境使用，输出目录在脚本顶部。它临时设置机器人位置，最后恢复；不是导航运行。
