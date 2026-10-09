import csv,json
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'src/sq_community'
m=json.loads((p/'docs/scene_manifest_4p2.json').read_text(encoding='utf-8'))
samples=[json.loads(s) for s in (root/'停止线核验.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
counts=Counter((line,s['light'],s['moving']) for s in samples for line in s['lines'])
bad=[s for s in samples if s['moving'] and s['light']!='green']
audit={'samples':len(samples),'moving_non_green_samples':len(bad),'counts':[{'line':k[0],'light':k[1],'moving':k[2],'samples':v} for k,v in counts.items()]}
(root/'停止线汇总.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
assert not bad,audit
summary=json.loads((root/'试跑汇总.json').read_text(encoding='utf-8'))
text='''# 决赛布局修改与预设点说明（2026-10-08）

10月8日完成布局修订，10月9日恢复仿真并完成取景修正。\n\n本次以用户提供的《第八届全球校园人工智能算法精英大赛算法应用赛道-智慧社区规则》第3页示意图为布局依据。图中没有逐个物料的精确坐标，因此坐标、观察点及示例任务状态是工程设定，不能代替现场标定或官方临场布置。

## 已修改内容

- 场地为4.2×4.2米，主要道路宽0.6米。路线依次沿顶边向西、左边向南、连接路向东、中央向南、底边向东、右边向北行驶。
- A、B人群区分别位于示意图对应的两个区域，立牌朝向与图中橙色箭头一致；示例为18个人物，并非规定数量。
- 楼宇A/B/C位于中间区域右侧，朝向分别为西/东/西；楼宇D朝西，站房朝南，保留窗格、火情示例、温度与仪表示例素材。
- 四类垃圾桶全部移到楼宇C下方，竖向排列并朝东。从北到南为有害、可回收、其他、厨余，不再占用原来B街附近位置。
- 右侧上部为电动车停放区，右侧下部自南向北为1/2/3号车位。保留停车区10辆与A区2辆示例电动车，以及倒伏、违停示例。这些数量和状态用于验证画面，不代表比赛固定答案。
- 标志牌放在B区西北侧，移除原先额外散布的标志牌。两组信号灯、斑马线与停止线保留；起终点使用地面分区。
- 按用户要求，地板上的8个方向箭头全部删除，行驶方向只保存在路线文件中。
- 预设31个任务/返回点，加10个必要转弯、清空停止线的过路点，共41个路线目标，中心线路程27.6米。检查点避开停止线，车身完全通过之后才转向。
- 广角相机前移并扩大到140°视场，上仰8°，电动车停车区改为低/中/高三个观察位，A区违停点改为斜视。人物顶部右侧观察点改为斜视，避开立牌背面遮挡。

## 使用方法

虚拟机工程：`/home/qyunt/sq_community_ws_20261008`。原工程包已备份至`acceptance/final_layout_20261008/source_before.tar.gz`。

桌面启动脚本继续使用。新终端依次执行：

```bash
cd ~/sq_community_ws_20261008
./start_scene.sh
```

场景已运行时不重复启动。另开终端启动巡检：

```bash
cd ~/sq_community_ws_20261008
./start_patrol.sh
```

停止巡检按Ctrl+C。地图/导航窗口中的旧SLAM地图不适用于新的物料位置，应重新建图。默认`sq_navigation_4p2.launch`使用本次重新生成的几何地图，不是SLAM成果。

## 验证范围与下一步

静态检查已通过：场景资源与连通性、41个目标的334×303毫米车身空间、路线方向、转向范围、停止线与人物/电动车的理论取景范围。

布局试跑版本完成40/40个目标、保存30张图像，采样43739次，越出道路0次。此后为完善取景增加中部电动车观察位、调整人物观察位及相机，并优化过路点，最终版为41目标；40目标的实跑结果不能冒充最终41目标的完整实跑验收。

最终观察点采用单独定位并抓图的方式检查画面，图像保存在`验收记录/final_layout_20261008/camera_qa`。31个预设点均已完成两路相机抓图，人物、垃圾桶、电动车等关键取景已人工复核，车体遮挡已消除。这种检查验证取景，不验证自主到点能力。

当前巡检主要使用里程计与激光安全检测。下一步应先跑最终41目标回归，再用新场地重新做SLAM/AMCL定位和move_base路线验收，最后接入人物、车牌、电动车、垃圾桶、火情、温度及仪表的真实识别与播报。当前素材显示、事件记录、拍照不等于已完成这些识别任务。若改用400×400毫米机器人，必须重新验证道路、转向和预设点。

## 最终预设点表

下表为Gazebo世界坐标（米），原点为场地中心；朝向角单位为度，0°朝东、90°朝北、180°朝西、−90°朝南。道路箭头不再绘制在地板上。

|序号|任务ID|X|Y|朝向|
|---:|---|---:|---:|---:|
'''
for i,t in enumerate(m['task_points'],1):
    import math
    x,y=t['world_xy_m'];text+='|%d|%s|%.2f|%.2f|%.1f°|\n'%(i,t['id'],x,y,math.degrees(t['yaw_rad']))
text+='\n停止线验收：%d条车身覆盖停止线的样本，运动且灯非绿的样本为%d。光源状态仅用于验收记录，巡检判断仍使用相机。\n'%(len(samples),len(bad))
if (root/'改动区段验收.json').exists():
    segment=json.loads((root/'改动区段验收.json').read_text(encoding='utf-8'))
    assert segment['success'] and segment['outside_samples']==0
    text+='\n10月9日最终改动区段实跑：前4个目标4/4到达，越出道路0次，人物和电动车均有实际到点照片；结束后机器人复位到起点。该记录是局部回归，不是最终41目标完整巡检记录。\n'
(root/'修改说明与预设点.md').write_text(text,encoding='utf-8')
(p/'SCENE_4P2_README.md').write_text(text,encoding='utf-8')
(root.parent/'项目总结/05_决赛布局修改与观察点.md').write_text(text,encoding='utf-8')
(p/'maps/README.md').write_text('''# 当前地图说明

`sq_community_4p2.pgm/.yaml`是2026-10-08决赛布局的几何先验地图，分辨率0.05米，92×92像素。由`tools/gen_map_4p2.py`生成，默认导航启动文件已指向它。

本目录其他旧SLAM地图、旧10×7.2米地图和旧导航验收记录仅用于历史参考。物料位置变更后必须重新建图与验收，不应沿用它们作为决赛布局地图。
''',encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False)); print('Written handover for',len(m['task_points']),'points')
