"""Build the team's competition handoff without modifying source directories."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'github-share'
REPO = OUT / 'smart-community-competition'
ORIGINAL = Path('F:/codex/实践课小车/智慧社区项目')
SKIP = {'.git', '__pycache__', 'node_modules', 'github-share', '.pytest_cache'}

def copy_tree(source, target):
    for path in sorted(source.rglob('*')):
        rel = path.relative_to(source)
        if path.is_file() and not any(p in SKIP for p in rel.parts):
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dst)

REPO.mkdir(parents=True, exist_ok=True)
# Retain every competition workspace file, including historical archives/evidence.
copy_tree(ROOT, REPO / '比赛工作记录')
copy_tree(ORIGINAL, REPO / '资料归档' / '原始工程与部署')
# Present one complete development entry: original dependencies + latest package.
original_src = ORIGINAL / '原始工程' / 'src'
for child in original_src.iterdir():
    if child.is_dir() and child.name != 'sq_community':
        copy_tree(child, REPO / 'src' / child.name)
copy_tree(ROOT / '决赛布局修订工程' / 'src' / 'sq_community', REPO / 'src' / 'sq_community')
references = [
    '第八届全球校园人工智能算法精英大赛算法应用赛道-智慧社区规则.pdf',
    '智慧社区赛项.pdf', '2026智慧社区复赛技术报告模板.docx', 'ROS基础实验.docx',
]
for name in references:
    source = Path('F:/qq文件') / name
    if source.exists():
        target = REPO / '资料归档' / '比赛规则与模板' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

readme = '''# 智慧社区比赛 · 团队进度与工程

本仓库用于队员共享源码、进度、部署说明和验收材料。整理日期：2026-10-10；最近实际运行证据日期：2026-10-09。

## 目前做到哪里

| 内容 | 当前进度 | 证据入口 |
|---|---|---|
| 4.2×4.2 米决赛场景 | 布局、物料方向、地图和观察点已修订；地面方向箭头已删除 | [修改说明](比赛工作记录/决赛布局修订工程/修改说明与预设点.md) |
| 当前路线 | 31 个任务/返回点 + 10 个过路点，共 41 个目标 | [路线文件](src/sq_community/route/sq_route_patrol_4p2.csv) |
| 取景检查 | 31 个预设点均完成两路相机抓图，关键视角已人工复核 | [取景验收记录](比赛工作记录/决赛布局修订工程/验收记录/final_layout_20261008/camera_qa/) |
| 旧布局整圈试跑 | 40/40 目标到达，保存 30 张照片；不代表最终 41 目标版整圈通过 | [布局进度说明](比赛工作记录/项目总结/05_决赛布局修改与观察点.md) |
| 最终改动区段实跑 | 2026-10-09 前 4 个目标 4/4 到达，越出道路 0 次 | [局部回归记录](比赛工作记录/决赛布局修订工程/验收记录/patrol_20261009_final_segment/) |
| 停止线记录 | 已有修复及采样记录，运动且灯非绿的覆盖停止线样本为 0 | [停止线汇总](比赛工作记录/决赛布局修订工程/停止线汇总.json) |
| 识别与自主导航 | 已有接口及部分组件；各任务真实识别、最终路线完整回归、SLAM/AMCL/move_base 全程验收待完成 | [下一步建议](比赛工作记录/项目总结/02_下一步工作与建议分工.md) |

到点、拍照、素材显示和记录事件不等同于识别成功。当前机器人模型约 334×303 毫米；换成 400×400 毫米模型后需要重新验证道路、转弯和观察点。

## 文件怎么找

- `src/`：团队继续开发的统一入口。`sq_community` 使用本地最新决赛布局修订源码；TurtleBot3 依赖来自原始工程，保留原许可文件。
- `比赛工作记录/`：当前比赛目录的完整资料副本，包含决赛修订、仿真验收、截图、地图模型、巡检日志、脚本、历史压缩包和项目总结。
- `资料归档/原始工程与部署/`：之前保存的原始工程、部署工具、验收记录、总结及原始源码 ZIP。
- `资料归档/比赛规则与模板/`：本机已有比赛规则、赛项资料、报告模板及 ROS 实验参考文件。
- `FILE_MANIFEST.json`：全部交付文件的大小和 SHA-256 校验值，不含清单本身和 Git 元数据。

建议先读 [最新布局说明](比赛工作记录/项目总结/05_决赛布局修改与观察点.md)，再读 [部署与启动说明](比赛工作记录/项目总结/03_部署与启动说明.md) 和 [仿真验收总结](比赛工作记录/项目总结/04_仿真验收与检查点优化.md)。较早说明中的 33/40 点路线是历史状态，当前以 `src/` 的 41 目标路线和最新证据为准。

## 队员如何运行

已有验收环境：Ubuntu 18.04、ROS Melodic、Gazebo 9。本仓库是源码与证据交接，没有随包编译目录、识别模型权重或完整外部 OCR 服务环境；此次整理未重新运行虚拟机仿真。

在安装好 ROS 和工程依赖的 Ubuntu 中：

```bash
git clone https://github.com/Qyunt/smart-community-competition.git
cd smart-community-competition
source /opt/ros/melodic/setup.bash
catkin_make -j2 -l2
source devel/setup.bash
export TURTLEBOT3_MODEL=waffle
find src -type f \\( -name '*.py' -o -name '*.sh' \\) -exec chmod +x {} \\;

# 只看场景：
roslaunch sq_community sq_community_4p2.launch

# 或停止上面的场景，再启动里程计巡检：
roslaunch sq_community sq_autonomous_4p2.launch enable_ocr:=false enable_voice:=false
```

VMware 图形兼容性及软件渲染处理见部署说明。当前巡检使用里程计和激光安全检测；最终版完整回归仍需执行。OCR 要另行配置实际服务地址；随包默认地址是历史队员机器地址。

## 下一步协作

1. 先完成最终 41 目标完整路线回归，保留日志、照片和停止线样本。
2. 新布局重新建图，独立验证 AMCL 定位与 move_base 全路线。
3. 接入人群、车牌、电动车、垃圾桶、火情、温度及仪表真实识别和播报。
4. 每项工作使用单独分支和 Pull Request；交付时说明修改内容、验证结果和剩余问题。

仓库采用私有共享。队员需由仓库所有者添加协作者后才能访问。后续更新优先修改 `src/`，将新的证据按日期保存，更新本页进度表。归档中的旧源码和结果用于追溯。
'''
(REPO / 'README.md').write_text(readme, encoding='utf-8')
(REPO / '.gitignore').write_text('build/\ndevel/\ninstall/\n__pycache__/\n*.pyc\n.pytest_cache/\n.env\n.env.*\n!.env.example\n', encoding='utf-8')
(REPO / '.gitattributes').write_text('# Preserve archived source bytes and SHA-256 manifest values.\n* -text\n', encoding='utf-8')
files = []
for path in sorted(REPO.rglob('*')):
    if path.is_file() and '.git' not in path.parts and path.name != 'FILE_MANIFEST.json':
        data = path.read_bytes()
        files.append({'path': path.relative_to(REPO).as_posix(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
(REPO / 'FILE_MANIFEST.json').write_text(json.dumps({'date': '2026-10-10', 'file_count': len(files), 'total_bytes': sum(x['bytes'] for x in files), 'files': files}, ensure_ascii=False, indent=2), encoding='utf-8')
archive = OUT / '智慧社区_团队共享完整资料_20261010.zip'
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for path in sorted(REPO.rglob('*')):
        if path.is_file() and '.git' not in path.parts:
            z.write(path, 'smart-community-competition/' + path.relative_to(REPO).as_posix())
with zipfile.ZipFile(archive) as z:
    bad = z.testzip()
    assert bad is None, bad
print(json.dumps({'repo': str(REPO), 'archive': str(archive), 'file_count': len(files), 'total_bytes': sum(x['bytes'] for x in files), 'zip_bytes': archive.stat().st_size, 'zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))
