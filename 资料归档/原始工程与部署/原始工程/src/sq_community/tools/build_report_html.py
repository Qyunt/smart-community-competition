# -*- coding: utf-8 -*-
"""
从已生成的产物拼出交付说明 HTML（单文件、内嵌平面图 SVG）：
  - docs/sq_community_plan.svg      内嵌为场地平面图
  - docs/scene_manifest.json        生成元素对照表与答案键
  - docs/静态自检报告.txt           生成校验结论
用法: python build_report_html.py --pkg <sq_community> --out <html 路径>
"""
from __future__ import print_function
import os
import json
import argparse

TASK_ROW = [
    ("红绿灯状态识别", "10 分（2 处 ×5）", "场地内 2 处红绿灯，红 10s→绿 15s→黄 3s，红灯时不得越过等待线"),
    ("人群数量识别", "12 分（2 街区 ×6）", "人偶立牌 16 具：A 街 8、B 街 8；其中 2 具橙色 = 非社区人员"),
    ("垃圾桶状态识别", "10 分", "4 个桶含开/闭与投放正确性；厨余桶内为投放错误样本"),
    ("楼宇火灾识别", "12 分（3 栋 ×4）", "楼宇 A/B/C 正面窗户中有橙红火焰贴图者即为火点"),
    ("车辆车牌识别", "12 分（3 辆 ×4）", "停车场 3 辆车，车牌贴图为可读文本"),
    ("楼宇异常温度识别", "10 分", "楼宇 D 第 2 层有高温窗，并挂 68℃ 温度牌"),
    ("站房仪表读取", "14 分（2 块 ×7）", "站房北面 2 块仪表，数码读数可 OCR"),
    ("电动车状态识别", "10 分", "停车区 8 正立 + 2 倒伏；A 街 2 辆违停，B 街 0 辆"),
    ("停车", "10 分", "A 街北侧泊车位 (4.45, 2.80)，要求车头朝向街道"),
    ("指示牌识别", "—", "沿途 6 块：限速30 / 禁止直行 / 左转 / 人行横道 / 禁止驶入 / 右转"),
]

VERIFY_ROW = [
    ("工程编译", "catkin_make 100% 通过（依赖 13 个 ros-melodic 包全部已装）"),
    ("roslaunch 解析", "通过，6 个节点全部识别（曾有一个重复 arg 的致命错，已修）"),
    ("Gazebo 世界加载", "11 组 sq_* 场地模型 + turtlebot3_waffle 全部加载成功"),
    ("机器人出生点", "/odom 实测 (-4.5999, 1.8000, -0.0010)，与设计值 (-4.60, 1.80) 一致"),
    ("激光雷达", "/scan 稳定 5.0 Hz 出数（waffle 的 LDS，量程 3.5 m）"),
    ("深度相机", "/camera/rgb/image_raw 1920×1080 rgb8 正常出图，/camera/depth/points 可用"),
    ("红绿灯控制器", "绿→黄→红→绿 循环正常，两盏灯 sq_tl_1 / sq_tl_2 同步生成"),
    ("场地可读性", "相机实拍中可辨认 FIRE 火焰窗、站房仪表读数 24680、可回收物桶、人偶立牌、车道线、远处红灯"),
    ("注意", "深度相机需要渲染引擎 = 必须带 GUI 运行；纯 gzserver 无头模式下相机建不出来（激光雷达不受影响）"),
]

NEXT_STEPS = [
    ("把视觉识别接到仿真相机上", "run", "scripts/sq_vision_demo.py 已给出接入骨架（订阅 /camera/rgb/image_raw + cv_bridge）。社区识别例程里 6 个 *_cam.py 是「打开本机摄像头」的单文件脚本，需要把 cv2.VideoCapture 换成图像回调；7 个 .pt 权重可以直接喂给 ultralytics。"),
    ("跑一次完整建图并存图", "run", "roslaunch sq_community sq_gmapping.launch，遥控跑遍 A 街 → 连接路 → B 街，再 map_saver 存到 maps/。提交的工程代码 zip 里必须有地图文件。"),
    ("标定导航参数", "tune", "waffle 在 1.2m 宽的街道里，costmap 的 inflation_radius 要调小，否则窄道会被判成不可通行。"),
    ("录像与讲解", "task2", "复赛视频上半段要求同屏展示 Gazebo + RViz，并在末尾讲建图/导航/识别的核心代码；下半段全队出镜答辩。"),
    ("技术方案文档 / PPT", "task2", "任务二 50 分：赛题分析 15 + 工程落地 15 + 文档质量 5 + 表达 10 + 排版 5。docs/scene_manifest.json 可直接作为场地说明附录。"),
]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def table(headers, rows, cls=""):
    h = "".join("<th>%s</th>" % esc(x) for x in headers)
    b = ""
    for r in rows:
        b += "<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>"
    return '<table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (cls, h, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pkg = a.pkg

    svg = ""
    sp = os.path.join(pkg, "docs", "sq_community_plan.svg")
    if os.path.exists(sp):
        svg = open(sp, "r", encoding="utf-8").read()
        # 去掉固定宽高，交给 CSS 自适应
        svg = svg.replace('width="100%"', 'class="plan"')

    M = json.load(open(os.path.join(pkg, "docs", "scene_manifest.json"), encoding="utf-8"))

    rep = ""
    rp = os.path.join(pkg, "docs", "静态自检报告.txt")
    if os.path.exists(rp):
        rep = open(rp, "r", encoding="utf-8").read()
    pass_line = ""
    fails = "?"
    for line in rep.splitlines():
        if "通过" in line and "项" in line:
            pass_line = line.strip()
    import re as _re
    m = _re.search(r"失败\s*(\d+)", pass_line)
    if m:
        fails = m.group(1)
    m2 = _re.search(r"通过\s*(\d+)", pass_line)
    n_ok = m2.group(1) if m2 else "?"

    # 元素明细表
    el_rows = []
    el_rows.append(["人偶立牌", "%d 具" % M["persons"]["total"],
                    "A 街 %d 人 / B 街 %d 人，橙色 %d 人（外来）"
                    % (M["persons"]["street_A"], M["persons"]["street_B"],
                       M["persons"]["outsiders_total"])])
    for b in M["bins"]:
        pass
    el_rows.append(["垃圾桶", "%d 个" % M["bins"]["count"],
                    " / ".join("%s(%s%s)" % (i["type"], "开" if i["open"] else "关",
                                             "·有垃圾" if i["load"] else "")
                               for i in M["bins"]["items"])])
    el_rows.append(["楼宇", "4 座",
                    "A/B/C 火点 %d/%d/%d；D 座 %d 楼高温 %.0f℃"
                    % (M["buildings"]["fire_windows"]["A"], M["buildings"]["fire_windows"]["B"],
                       M["buildings"]["fire_windows"]["C"],
                       M["buildings"]["hot"]["floor"], M["buildings"]["hot"]["temp_c"])])
    el_rows.append(["站房仪表", "2 块",
                    "读数 " + " / ".join(g["reading"] for g in M["station"]["gauges"])])
    el_rows.append(["汽车 + 车牌", "3 辆",
                    " / ".join("%s→%s" % (c["id"], c["plate"]) for c in M["cars"]["items"])])
    el_rows.append(["电动车", "12 辆",
                    "停车区 正常 %d / 倒伏 %d；违停 A 街 %d、B 街 %d"
                    % (M["ebikes"]["parking_area"]["upright"], M["ebikes"]["parking_area"]["fallen"],
                       M["ebikes"]["illegal_parking"]["street_A"],
                       M["ebikes"]["illegal_parking"]["street_B"])])
    el_rows.append(["指示牌", "6 块", "限速30 / 禁止直行 / 左转 / 人行横道 / 禁止驶入 / 右转"])
    el_rows.append(["红绿灯", "2 处",
                    "tl_1 (%.2f, %.2f) 朝西；tl_2 (%.2f, %.2f) 朝东"
                    % (M["traffic_lights"]["items"][0]["xy"][0], M["traffic_lights"]["items"][0]["xy"][1],
                       M["traffic_lights"]["items"][1]["xy"][0], M["traffic_lights"]["items"][1]["xy"][1])])
    el_rows.append(["泊车位", "1 个",
                    "(%.2f, %.2f) 尺寸 %.2f×%.2f，%s"
                    % (M["parking"]["final_slot"]["xy"][0], M["parking"]["final_slot"]["xy"][1],
                       M["parking"]["final_slot"]["size"][0], M["parking"]["final_slot"]["size"][1],
                       M["parking"]["final_slot"]["required_heading"])])

    ans_rows = [[k, esc(v)] for k, v in M["answer_key"].items()]
    verify_rows = [[a, esc(b)] for a, b in VERIFY_ROW]
    task_rows = [[n, s, d] for n, s, d in TASK_ROW]
    step_rows = [[n, "<span class='tag %s'>%s</span>" % (k, {"run": "现在就能跑",
                                                             "tune": "需要调参",
                                                             "task2": "任务二"}[k]), esc(d)]
                 for n, k, d in NEXT_STEPS]

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>智慧社区 · 建模与仿真空间（已建好）</title>
<style>
:root{
  --bg:#f7f7f5; --card:#ffffff; --line:#e3e3df; --ink:#1c1e22; --sub:#5c6167;
  --ok:#1f7a3d; --okbg:#eaf6ee; --warn:#a8620a; --warnbg:#fdf3e3; --run:#1b5fa8; --runbg:#eaf2fb;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height:1.72;font-size:15px}
.wrap{max-width:1120px;margin:0 auto;padding:34px 24px 80px}
h1{font-size:29px;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--sub);font-size:14px;margin-bottom:26px}
h2{font-size:20px;margin:38px 0 12px;padding-bottom:7px;border-bottom:2px solid var(--line)}
h3{font-size:16px;margin:22px 0 8px;color:#2a2d32}
.card{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:18px 20px;margin:14px 0}
.stats{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0 6px}
.stat{flex:1 1 150px;background:var(--card);border:1px solid var(--line);border-radius:11px;padding:14px 16px}
.stat .n{font-size:25px;font-weight:700;letter-spacing:-.02em}
.stat .l{font-size:12.5px;color:var(--sub);margin-top:2px}
.stat.good .n{color:var(--ok)}
table{width:100%%;border-collapse:collapse;margin:10px 0 4px;font-size:14px;background:var(--card)}
th,td{border:1px solid var(--line);padding:9px 11px;text-align:left;vertical-align:top}
th{background:#f1f1ee;font-weight:600;font-size:13.5px;white-space:nowrap}
tbody tr:nth-child(even){background:#fbfbfa}
code{background:#f1f1ee;border:1px solid var(--line);border-radius:5px;padding:1.5px 6px;
  font-size:13px;font-family:ui-monospace,Consolas,"Courier New",monospace}
pre{background:#1e2126;color:#e8e8e6;border-radius:10px;padding:15px 17px;overflow-x:auto;
  font-size:13px;line-height:1.65;font-family:ui-monospace,Consolas,"Courier New",monospace}
pre .c{color:#8f9aa6}
pre .k{color:#8fd08f}
.tag{display:inline-block;font-size:12px;padding:2px 9px;border-radius:20px;white-space:nowrap}
.tag.run{background:var(--runbg);color:var(--run)}
.tag.tune{background:var(--warnbg);color:var(--warn)}
.tag.task2{background:#f0ecfa;color:#5a3fa8}
.ok{background:var(--okbg);border-color:#bfe0c9}
.plan{width:100%%;height:auto;display:block;border-radius:10px}
.figcap{font-size:13px;color:var(--sub);margin-top:8px}
ul{margin:8px 0 0 20px;padding:0}
li{margin:5px 0}
.note{font-size:13.5px;color:var(--sub)}
strong{font-weight:600}
.kv{display:grid;grid-template-columns:118px 1fr;gap:6px 14px;font-size:14px}
.kv b{color:var(--sub);font-weight:500}
@media print{
  body{background:#fff;font-size:12px}
  .wrap{max-width:none;padding:0}
  h2{page-break-after:avoid}
  table,pre,.card{page-break-inside:avoid}
  pre{background:#f4f4f2;color:#1c1e22;border:1px solid #ddd}
  pre .c{color:#777}
  pre .k{color:#1f7a3d}
}
</style>
</head>
<body>
<div class="wrap">

<h1>智慧社区 · 建模与仿真空间</h1>
<div class="sub">
  全球校园人工智能算法精英大赛 · 算法应用赛（赛马制）· 智慧社区 &nbsp;|&nbsp;
  复赛任务一「巡检场景设计与演示」&nbsp;|&nbsp; 工程：<code>sq_ws/src/sq_community</code>
</div>

<div class="stats">
  <div class="stat good"><div class="n">%(n_ok)s</div><div class="l">静态自检通过项</div></div>
  <div class="stat good"><div class="n">%(fails)s</div><div class="l">失败项</div></div>
  <div class="stat"><div class="n">10 × 7.2<span style="font-size:15px"> m</span></div><div class="l">场地尺寸</div></div>
  <div class="stat"><div class="n">256</div><div class="l">世界内 link 数</div></div>
  <div class="stat"><div class="n">35</div><div class="l">带文字/数字的贴图</div></div>
  <div class="stat"><div class="n">30<span style="font-size:15px"> MB</span></div><div class="l">工作空间大小（限 150MB）</div></div>
</div>

<h2>1. 这次交付了什么</h2>
<div class="card">
<p>一套<strong>可直接编译运行的 ROS1 仿真工程</strong>，不是空壳场景：场地里每一个识别目标都带真实可读的文字或颜色特征，
视觉算法有东西可认；同时给出机器可读的<strong>场地真值</strong>可以拿来对答案。</p>
<div class="kv">
  <b>世界文件</b><span><code>worlds/sq_community.world</code>（10 个模型组、256 个 link、185 个碰撞体）</span>
  <b>红绿灯</b><span>红/黄/绿三套模型 + <code>traffic_light_controller.py</code>，严格按规则 10s / 15s / 3s 循环</span>
  <b>贴图素材</b><span>35 张：车牌、仪表读数、6 种指示牌、火灾窗口、楼号、垃圾分类贴、斑马线、停车位…</span>
  <b>导航脚本</b><span>建图 / 导航 / 多点巡检 / 相机视觉接入骨架</span>
  <b>场地真值</b><span><code>docs/scene_manifest.json</code>：坐标 + 出现次数 + 每项任务的播报答案</span>
  <b>生成器</b><span><code>tools/</code> 三个脚本，坐标和物件数量都是常量表，改完重跑即可重建</span>
</div>
</div>

<h2>2. 场地平面图</h2>
<div class="card">
%(svg)s
<div class="figcap">俯视图，单位米。x 向东、y 向北，原点在场地中心。
机器人出生在出发区 (−4.60, 1.80)，车头朝 +x 沿 A 街向东。
绿色三角为出生点，深色圆点为立牌/垃圾桶/电动车/指示牌位置。</div>
</div>

<h2>3. 场地元素清单</h2>
%(el_table)s

<h2>4. 元素 → 赛项对照</h2>
%(task_table)s

<h2>5. 场地答案键（真值）</h2>
<div class="card ok">
<p class="note">这一段是<strong>场地里实际摆放的正确结果</strong>。你的识别程序跑完后可以直接拿它对答案；
写复赛技术方案时也可以作为「仿真场景说明」附录直接引用。</p>
%(ans_table)s
</div>

<h2>6. 怎么把工程放进虚拟机</h2>
<div class="card">
<p>已经打好包并在宿主机上起好了 HTTP 服务：<code>_share/sq_ws_transfer.tar.gz</code>（8.07 MB，383 个文件；解包后 30.1 MB）。
虚拟机是 <strong>Ubuntu 18.04.6 LTS（ROS Melodic）</strong>，走 VMware NAT，宿主机地址 <code>192.168.232.1</code>。</p>

<h3>虚拟机里执行这三步</h3>
<pre><span class="c"># ① 拉取并解包</span>
mkdir -p ~/dl &amp;&amp; cd ~/dl
wget -O sq_ws_transfer.tar.gz http://192.168.232.1:8000/sq_ws_transfer.tar.gz
tar -xzf sq_ws_transfer.tar.gz -C ~

<span class="c"># ② 一键安装（装依赖 + 补执行位 + catkin_make + 写 .bashrc）</span>
cd ~/sq_ws
bash src/sq_community/install_to_ws.sh

<span class="c"># ③ 生效并启动</span>
source ~/.bashrc
roslaunch sq_community sq_community.launch</pre>

<p class="note"><strong>务必带 <code>-O</code></strong>：wget 遇到同名文件会存成 <code>.1</code>，
而 <code>tar -xzf</code> 仍解压旧的那份，白跑一遍。加上 <code>-O</code> 就是直接覆盖。</p>

<p class="note">如果 wget 连不上：先在虚拟机里 <code>ip addr show</code> 确认拿到 <code>192.168.232.x</code>；
仍不行就 <code>sudo ufw disable</code> 关掉虚拟机防火墙再试。
宿主机上如果服务被关掉了，重新执行 <code>python sq_ws\\serve_to_vm.py</code> 即可。</p>
</div>

<h2>6.5 虚拟机实机验收（已跑通）</h2>
<div class="card ok">
<p>工程已经真正在 <strong>Ubuntu 18.04.6 + ROS Melodic</strong> 虚拟机里编译并运行过一轮，
不是只有静态检查。结论如下（同一轮里顺手修掉了一个会直接起不来的致命错——launch 文件里
<code>traffic_light</code> 这个 arg 被重复声明，roslaunch 会拒绝解析整个文件）。</p>
%(verify_table)s
<p class="note" style="margin-top:12px">验收截图放在工作区 <code>仿真验收截图\\</code> 目录：
<code>相机实拍.jpg</code>（机器人深度相机的真实出图）、<code>Gazebo与RViz截图.png</code>。</p>
</div>

<h3>Gazebo 窗口没出现就补一条命令</h3>
<div class="card">
<p><code>gzclient</code>（Gazebo 的窗口程序）<strong>一旦连不上 <code>gzserver</code> 就会立刻以退出码 255 静默退出</strong>。
场地有 256 个物体，<code>gzserver</code> 要几十秒才加载完，而 <code>roslaunch</code> 会把两者同时拉起来，
窗口程序常常抢跑、连不上、然后自己退掉 —— 表现就是 <strong>Gazebo 窗口时有时无</strong>。
服务端和世界都还在，补开窗口即可：</p>
<pre><span class="c"># 做法一（推荐）：先起服务端，等场地加载完再单独开窗口</span>
roslaunch sq_community sq_community.launch gui:=false
<span class="c"># 等 40~60 秒，另开一个终端：</span>
gzclient

<span class="c"># 做法二：正常起，窗口没出来就补一条</span>
roslaunch sq_community sq_community.launch
gzclient</pre>
<p class="note">另有一条无害报错：<code>REST.cc Error in REST request ... api.ignitionfuel.org</code>
—— Gazebo 尝试访问在线模型库失败（虚拟机网络所致）。本工程不用任何在线模型，忽略即可。</p>
</div>

<h2>7. 跑起来的三步</h2>
<pre><span class="c"># ① 场地 + 机器人（含红绿灯控制器、RViz）</span>
roslaunch sq_community sq_community.launch

<span class="c"># ② 建图：另开终端，键盘遥控跑遍全场，然后存图</span>
roslaunch sq_community sq_gmapping.launch
rosrun teleop_twist_keyboard teleop_twist_keyboard.py
rosrun map_server map_saver -f $(find sq_community)/maps/sq_community

<span class="c"># ③ 导航 + 多点巡检：再开一个终端</span>
roslaunch sq_community sq_navigation.launch
rosrun sq_community sq_patrol.py</pre>

<div class="card">
<p><strong>要录像的话</strong>，第 ① 步之后画面上应该有 Gazebo 的社区沙盘和 RViz；
第 ② 步的 <code>map_saver</code> 之前记得让机器人把 A 街、连接路、B 街都走一遍——
复赛视频要求「同屏展示 Gazebo 视角与 RViz 界面」，录屏时把两个窗口并排放好。</p>
</div>

<h2>8. 还没做 / 接下来要做</h2>
%(step_table)s

<h2>9. 复赛提交四件套对照</h2>
<table>
<thead><tr><th>提交物</th><th>命名规范</th><th>当前状态</th></tr></thead>
<tbody>
<tr><td>技术方案文档（.pdf）</td><td><code>【队名】-智慧社区复赛技术方案.pdf</code></td>
    <td>未写。可用第 3/4/5 节内容做「仿真场景」一章</td></tr>
<tr><td>工程源代码（.zip ≤150MB）</td><td><code>【队名】-智慧社区复赛工程代码.zip</code></td>
    <td><strong>基本就绪</strong>：打包 <code>sq_ws/src</code> 即可（30 MB）。注意补上 <code>maps/</code> 里的地图，并确认根目录有 README.md</td></tr>
<tr><td>答辩幻灯片（.pdf）</td><td><code>【队名】-智慧社区复赛答辩展示.pdf</code></td>
    <td>未做</td></tr>
<tr><td>综合展示视频（.mp4 ≤300MB）</td><td><code>【队名】-智慧社区复赛综合展示视频.mp4</code></td>
    <td>未录。要求 8–12 分钟，上半段实操+代码讲解，下半段全队出镜答辩</td></tr>
</tbody>
</table>

<h2>10. 静态自检报告全文</h2>
<pre>%(report)s</pre>

<p class="note" style="margin-top:34px">
  本页由 <code>tools/build_report_html.py</code> 从工程实际产物自动生成 ——
  平面图来自 <code>docs/sq_community_plan.svg</code>，数据来自 <code>docs/scene_manifest.json</code>，
  校验结论来自 <code>docs/静态自检报告.txt</code>。改动场地后重跑生成器与自检，
  再执行一次本页的生成脚本即可同步。
</p>

</div>
</body>
</html>
""" % {
        "n_ok": n_ok, "fails": fails, "svg": svg,
        "el_table": table(["场地元素", "数量", "细节"], el_rows),
        "task_table": table(["总决赛任务", "分值", "场地对应"], task_rows),
        "ans_table": table(["任务", "场地内的正确答案"], ans_rows),
        "step_table": table(["待办", "类型", "说明"], step_rows),
        "verify_table": table(["验收项", "实测结果"], verify_rows),
        "report": esc(rep),
    }

    out = a.out
    d = os.path.dirname(out)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    open(out, "w", encoding="utf-8").write(html)
    print("HTML: %s  (%.1f KB)" % (out, os.path.getsize(out) / 1024.0))
    print("自检通过 %s 项 / 失败 %s 项" % (n_ok, fails))


if __name__ == "__main__":
    main()
