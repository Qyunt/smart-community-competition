# -*- coding: utf-8 -*-
"""
智慧社区 Gazebo 场地生成器

输入: 下面的 LAYOUT 布局常量 + models/sq_textures 里的贴图
输出:
    worlds/sq_community.world          场地主世界
    models/sq_traffic_light_{red,green,yellow}/{model.config,model.sdf}
    docs/sq_community_plan.svg         俯视平面图（给人看的）
    docs/元素-任务对照表.csv

坐标系: x 向东, y 向北, z 向上; 场地 x∈[-5,5], y∈[-3.6,3.6]

用法: python gen_scene.py --pkg <package_root>
"""
import os, argparse, csv, re

# ===================================================================== 布局常量
# 场地
AX, AY = 5.00, 3.60          # 场地半宽 / 半高
WALL_T, WALL_H = 0.06, 0.55  # 围墙厚 / 高

# 三条路（带状）
ROAD_A = (1.20, 2.40)        # A 街: y 区间
ROAD_B = (-2.40, -1.20)      # B 街: y 区间
ROAD_C = (-0.60, 0.60)       # 连接路: x 区间
CX_A, CX_B = 1.80, -1.80     # 两条街中心线

# 出发区 / 停止线
START_X = -4.20              # 出发横线
ROBOT_START = (-4.60, 1.80, 0.01, 0.0)
WAIT_A_X, WAIT_B_X = -0.75, 0.75   # 红绿灯等待线

# 楼宇（长 x 宽 y 高 z，正面朝街）
BLD = {
    "A": dict(c=(-3.20, 3.10), s=(1.60, 0.70, 0.85), face=-1, fire=(0, 3, 6)),   # 3 个火点
    "B": dict(c=(2.90, 3.10), s=(1.60, 0.70, 0.85), face=-1, fire=(1, 7, 9, 2, 5)),  # 5 个火点
    "C": dict(c=(-3.20, -3.10), s=(1.60, 0.70, 0.85), face=+1, fire=(4, 8)),    # 2 个火点
    "D": dict(c=(2.90, -3.10), s=(1.60, 0.70, 0.85), face=+1, fire=(), hot=7),  # 无火, 2楼高温
}
WIN_COLS, WIN_ROWS = 5, 2
WIN_W, WIN_H, WIN_T = 0.18, 0.16, 0.008
WIN_Z = [0.26, 0.52]         # 1楼 / 2楼

# 站房（含 2 个仪表）
STATION = dict(c=(-3.30, 0.55), s=(1.10, 0.50, 0.55))
GAUGE_X = [-3.62, -2.98]
GAUGE_Y = 0.815

# 垃圾桶（类型, x, 是否打开, 投放物: None/正确/错误）
BINS = [
    ("recycle", -2.30, False, None),
    ("hazard", -2.00, True, "correct"),
    ("kitchen", -1.70, True, "wrong"),
    ("other", -1.40, False, None),
]
BIN_Y = 0.85

# 指示牌（材质, x, y, yaw）
SIGNS = [
    ("sign_speed30", -4.30, 2.55, 3.14159),
    ("sign_no_straight", -1.00, 2.55, 3.14159),
    ("sign_turn_left", 2.60, 2.55, 3.14159),
    ("sign_crosswalk", -0.80, 0.90, 0.0),
    ("sign_no_entry", 0.80, -0.30, -1.5708),
    ("sign_turn_right", 3.60, -2.55, 0.0),
]

# 人偶立牌 (x, y, yaw, 是否外来人员)
PERSONS = (
    [(-3.90, 2.50, 3.14159, True), (-3.10, 2.50, 3.14159, False),
     (-2.30, 2.50, 3.14159, False), (-1.50, 2.50, 3.14159, False)] +
    [(-2.60, 1.10, 0.0, True), (-1.80, 1.10, 0.0, False),
     (1.40, 1.10, 0.0, False), (2.20, 1.10, 0.0, False)] +
    [(-3.90, -1.10, 0.0, False), (-2.90, -1.10, 0.0, False),
     (-1.90, -1.10, 0.0, False), (-0.90, -1.10, 0.0, False)] +
    [(-1.90, -2.50, 3.14159, False), (-0.90, -2.50, 3.14159, False),
     (1.90, -2.50, 3.14159, False), (2.90, -2.50, 3.14159, False)]
)

# 电动车 (x, y, yaw, 状态: upright/fallen, 区域)
EBIKES = (
    [(1.15, 0.55, 0.0, "upright"), (1.45, 0.55, 0.0, "upright"),
     (1.75, 0.55, 0.0, "upright"), (2.05, 0.55, 0.0, "upright"),
     (1.15, -0.55, 3.14159, "upright"), (1.45, -0.55, 3.14159, "upright"),
     (1.75, -0.55, 3.14159, "upright"), (2.05, -0.55, 3.14159, "upright"),
     (2.45, 0.55, 0.0, "fallen"), (2.45, -0.55, 0.0, "fallen")] +
    [(2.75, 1.35, 0.0, "upright"), (3.15, 1.35, 0.0, "upright")]   # A 街违停 2 辆
)

# 停车场 3 车位 + 3 辆车（车头朝 +y，即朝向 A 街）
PARK_C = (3.75, -0.35)
PARK_BAY_X = [3.25, 3.80, 4.35]
PARK_BAY_W, PARK_BAY_D = 0.50, 0.60
CARS = [("plate_A", 3.25, -0.35), ("plate_B", 3.80, -0.35), ("plate_C", 4.35, -0.35)]

# 泊车终点位（A 街北侧，车头朝街道 → 车头朝 -y）
PARK_SLOT = (4.45, 2.80, 0.55, 0.70)

# 红绿灯位姿
TL1 = (1.10, 2.62, 3.14159)      # 面向西（A 街东行车）
TL2 = (1.10, -2.62, 0.0)         # 面向东（B 街西行车）

TEX = "model://sq_textures/materials/scripts"
TEXD = "model://sq_textures/materials/textures"

# ===================================================================== SDF 助手
def fmt(v):
    return " ".join("%g" % x for x in v)


def P(x, y, z=0.0, r=0.0, p=0.0, yw=0.0):
    return fmt((x, y, z, r, p, yw))


def mat_tex(name):
    return ('<material><script><uri>%s</uri><uri>%s</uri><name>%s</name></script>'
            '<ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse>'
            '<specular>0.05 0.05 0.05 1</specular></material>' % (TEX, TEXD, name))


def mat_rgb(rgb, emissive=None, spec=0.1):
    r, g, b = rgb
    amb = (r * 0.55, g * 0.55, b * 0.55, 1.0)
    emi = tuple(emissive) + (1.0,) if emissive else (0.0, 0.0, 0.0, 1.0)
    return ('<material><script><uri>file://media/materials/scripts/gazebo.material</uri>'
            '<name>Gazebo/White</name></script>'
            '<ambient>%s</ambient><diffuse>%s</diffuse><specular>%s</specular>'
            '<emissive>%s</emissive></material>'
            % (fmt(amb), fmt((r, g, b, 1.0)), fmt((spec, spec, spec, 1.0)), fmt(emi)))


def geom_box(sx, sy, sz):
    return "<geometry><box><size>%s</size></box></geometry>" % fmt((sx, sy, sz))


def geom_cyl(r, l):
    return ("<geometry><cylinder><radius>%g</radius><length>%g</length></cylinder></geometry>"
            % (r, l))


def geom_sph(r):
    return "<geometry><sphere><radius>%g</radius></sphere></geometry>" % r


def link(name, pose, geom, material, coll=True, shadow=1, extra=""):
    # 厚度 < 5cm 的薄片一律只做视觉、不做碰撞：
    # 地面标线 / 路面 / 人行道 / 绿化带 / 车牌 / 屋面 之类不应变成障碍物，
    # 否则机器人会卡在 1~4cm 的"台阶"上动不了。
    if coll and "<box><size>" in geom:
        sz = geom.split("<box><size>")[1].split("</size>")[0].split()
        if len(sz) == 3 and float(sz[2]) < 0.05:
            coll = False
    c = ""
    if coll:
        c = ("<collision name='%s_c'><pose>%s</pose>%s</collision>"
             % (name, pose, geom))
    return ("<link name='%s'>%s"
            "<visual name='%s_v'><pose>%s</pose>%s%s"
            "<cast_shadows>%d</cast_shadows></visual>%s</link>"
            % (name, c, name, pose, geom, material, shadow, extra))


def model(name, links, static=True):
    body = ""
    for lk in links:
        body += "<link name='%s'>%s</link>" % (lk[0], lk[1]) if isinstance(lk, tuple) else lk
    return ("  <model name='%s'>\n    <static>%d</static>\n    <pose>0 0 0 0 0 0</pose>\n"
            "    %s\n  </model>\n" % (name, 1 if static else 0, body))


# 统一收集
MODELS = []
DOC = []          # (分类, 名称, 世界坐标说明, 对应赛项)
SVG = []          # svg 图元


def add_model(name, links):
    MODELS.append((name, links))


# ===================================================================== 地面 / 道路
def build_ground():
    L = []
    # 底盘
    L.append(("ground_base", link("ground_base", P(0, 0, -0.05),
                geom_box(2 * AX + 0.3, 2 * AY + 0.3, 0.10), mat_rgb((0.24, 0.25, 0.27)))))
    SVG.append(("rect", -AX, -AY, 2 * AX, 2 * AY, "#3a3d42", None))
    # 三条路面
    # 出发区地贴
    L.append(("start_decal", link("start_decal", P(START_X - 0.42, CX_A, 0.008),
                geom_box(0.62, 0.42, 0.012), mat_tex("SQ_start_plate"))))
    SVG.append(("rect", START_X - 0.73, CX_A - 0.21, 0.62, 0.42, "#3c9a52", "出发区"))
    # 路面
    L.append(("road_a", link("road_a", P(0, CX_A, 0.002),
                geom_box(2 * AX, ROAD_A[1] - ROAD_A[0], 0.006), mat_rgb((0.33, 0.34, 0.36)),)) )
    L.append(("road_b", link("road_b", P(0, CX_B, 0.002),
                geom_box(2 * AX, ROAD_B[1] - ROAD_B[0], 0.006), mat_rgb((0.33, 0.34, 0.36)))))
    L.append(("road_c", link("road_c", P(0, 0, 0.002),
                geom_box(ROAD_C[1] - ROAD_C[0], 2 * 2.40, 0.006), mat_rgb((0.33, 0.34, 0.36)))))
    for (y0, y1) in (ROAD_A, ROAD_B):
        SVG.append(("rect", -AX, y0, 2 * AX, y1 - y0, "#4a4d52", None))
    SVG.append(("rect", ROAD_C[0], -2.40, 1.20, 4.80, "#4a4d52", None))
    # 绿化带（中轴带两端）
    for cx, w, lab in [(-4.35, 0.90, "绿化带"), (4.75, 0.34, "")]:
        L.append(("grass_%.2f" % cx, link("grass_%.2f" % cx, P(cx, 0.0, 0.02),
                    geom_box(w, 2.00, 0.04), mat_tex("SQ_gnd_grass"))))
        SVG.append(("rect", cx - w / 2, -1.00, w, 2.00, "#568c46", lab))
    # 人行道（楼宇前）
    for y in (2.52, -2.52):
        L.append(("walk_%.1f" % y, link("walk_%.1f" % y, P(0, y, 0.015),
                    geom_box(2 * AX, 0.24, 0.03), mat_rgb((0.62, 0.61, 0.58)))))
    add_model("sq_ground", L)


def build_markings():
    L = []
    W_ = mat_rgb((0.95, 0.95, 0.95))
    Y_ = mat_rgb((0.92, 0.80, 0.15))
    # 车道中心虚线 (A街 y=1.8, B街 y=-1.8)，x 从 -4.8 到 4.8，避开路口
    for cy in (CX_A, CX_B):
        x = -4.80
        while x < 4.80:
            if not (-0.95 < x < 0.95):
                L.append(("dash_%.1f_%.2f" % (cy, x), link("dash_%.1f_%.2f" % (cy, x),
                            P(x, cy, 0.008), geom_box(0.35, 0.05, 0.012), Y_)))
            x += 0.80
    # 路缘实线
    for cy, off in ((CX_A, 0.58), (CX_B, -0.58)):
        L.append(("edge_%.1f" % cy, link("edge_%.1f" % cy, P(0, cy + off, 0.007),
                    geom_box(2 * AX, 0.04, 0.010), W_)))
    # 出发横线 / 两条红绿灯等待线
    L.append(("start_line", link("start_line", P(START_X, CX_A, 0.009),
                geom_box(0.08, 1.20, 0.014), W_)))
    L.append(("wait_a", link("wait_a", P(WAIT_A_X, CX_A, 0.009),
                geom_box(0.08, 1.20, 0.014), W_)))
    L.append(("wait_b", link("wait_b", P(WAIT_B_X, CX_B, 0.009),
                geom_box(0.08, 1.20, 0.014), W_)))
    SVG.append(("rect", START_X - 0.04, ROAD_A[0], 0.08, 1.20, "#f2f2f2", "出发横线"))
    SVG.append(("rect", WAIT_A_X - 0.04, ROAD_A[0], 0.08, 1.20, "#f2f2f2", "等待线"))
    SVG.append(("rect", WAIT_B_X - 0.04, ROAD_B[0], 0.08, 1.20, "#f2f2f2", "等待线"))
    # 斑马线
    L.append(("crosswalk", link("crosswalk", P(0.0, 0.90, 0.010),
                geom_box(1.20, 0.60, 0.016), mat_tex("SQ_gnd_crosswalk"))))
    SVG.append(("rect", -0.60, 0.60, 1.20, 0.60, "#dcdcdc", "斑马线"))
    # 停车场车位框（3 个）+ 车位地面
    for i, bx in enumerate(PARK_BAY_X):
        L.append(("bay_%d_g" % i, link("bay_%d_g" % i, P(bx, PARK_C[1], 0.005),
                    geom_box(PARK_BAY_W, PARK_BAY_D, 0.010), mat_tex("SQ_gnd_parking"))))
        L.append(("bay_%d_fl" % i, link("bay_%d_fl" % i,
                    P(bx - PARK_BAY_W / 2 + 0.02, PARK_C[1], 0.009),
                    geom_box(0.04, PARK_BAY_D, 0.014), W_)))
        L.append(("bay_%d_bk" % i, link("bay_%d_bk" % i, P(bx, PARK_C[1] - PARK_BAY_D / 2 + 0.02, 0.009),
                    geom_box(PARK_BAY_W, 0.04, 0.014), W_)))
        SVG.append(("rect", bx - PARK_BAY_W / 2, PARK_C[1] - PARK_BAY_D / 2,
                    PARK_BAY_W, PARK_BAY_D, "#5b5e63", "车位%d" % (i + 1)))
    # 泊车位（终点，A 街北侧）
    px, py, pw, pd = PARK_SLOT
    for dx, dy, sw, sd in [(-pw / 2, 0, 0.05, pd), (pw / 2, 0, 0.05, pd), (0, -pd / 2, pw, 0.05)]:
        L.append(("slot_%.2f_%.2f" % (dx, dy), link("slot_%.2f_%.2f" % (dx, dy),
                    P(px + dx, py + dy, 0.009), geom_box(sw, sd, 0.014), W_)))
    SVG.append(("rect", px - pw / 2, py - pd / 2, pw, pd, "#5b5e63", "泊车位(终点)"))
    add_model("sq_markings", L)
    DOC.append(("地面标线", "车道虚线/路缘实线/出发横线/等待线/斑马线/车位框",
                "A街B街中心虚线 y=±1.8; 出发横线 x=-4.20; 等待线 x=-0.75、+0.75", "场景搭建"))


# ===================================================================== 围墙
def build_walls():
    L = []
    c = mat_rgb((0.55, 0.55, 0.58))
    specs = [("n", P(0, AY, WALL_H / 2), geom_box(2 * AX + WALL_T, WALL_T, WALL_H)),
             ("s", P(0, -AY, WALL_H / 2), geom_box(2 * AX + WALL_T, WALL_T, WALL_H)),
             ("w", P(-AX, 0, WALL_H / 2), geom_box(WALL_T, 2 * AY + WALL_T, WALL_H)),
             ("e", P(AX, 0, WALL_H / 2), geom_box(WALL_T, 2 * AY + WALL_T, WALL_H))]
    for n, ps, g in specs:
        L.append(("wall_" + n, link("wall_" + n, ps, g, c)))
    add_model("sq_walls", L)
    DOC.append(("围界", "四周围墙 (0.06×0.55m)", "x=±5.00, y=±3.60", "场景搭建 / 建图边界"))


# ===================================================================== 楼宇
def build_buildings():
    L = []
    for key in ("A", "B", "C", "D"):
        d = BLD[key]
        cx, cy = d["c"]
        sx, sy, sz = d["s"]
        face = d["face"]                 # -1 -> 面向 -y(朝 A 街); +1 -> 面向 +y(朝 B 街)
        fy = cy + face * (sy / 2 + 0.004)
        L.append(("bld_%s_body" % key, link("bld_%s_body" % key, P(cx, cy, sz / 2),
                    geom_box(sx, sy, sz), mat_rgb((0.74, 0.72, 0.68)))))
        # 窗户
        fire = set(d.get("fire", ()))
        hot = d.get("hot", -1)
        for idx in range(WIN_COLS * WIN_ROWS):
            col, row = idx % WIN_COLS, idx // WIN_COLS
            wx = cx - sx / 2 + (sx / WIN_COLS) * (col + 0.5)
            wz = WIN_Z[row]
            if idx == hot:
                m = mat_tex("SQ_win_hot")
            elif idx in fire:
                m = mat_tex("SQ_win_fire")
            else:
                m = mat_tex("SQ_win_normal")
            L.append(("bld_%s_win%d" % (key, idx),
                      link("bld_%s_win%d" % (key, idx), P(wx, fy, wz),
                           geom_box(WIN_W, WIN_T, WIN_H), m)))
        # 楼层标（贴在正面左端）
        for row in range(WIN_ROWS):
            L.append(("bld_%s_fl%d" % (key, row),
                      link("bld_%s_fl%d" % (key, row),
                           P(cx - sx / 2 - 0.16, fy, WIN_Z[row]),
                           geom_box(0.13, WIN_T, 0.10), mat_tex("SQ_floor_%df" % (row + 1)))))
        # 楼号牌
        L.append(("bld_%s_plate" % key, link("bld_%s_plate" % key, P(cx, fy, 0.74),
                    geom_box(0.42, WIN_T, 0.17), mat_tex("SQ_bldg_%s" % key))))
        # 屋面檐口
        L.append(("bld_%s_roof" % key, link("bld_%s_roof" % key, P(cx, cy, sz + 0.02),
                    geom_box(sx + 0.08, sy + 0.08, 0.04), mat_rgb((0.45, 0.44, 0.46)))))
        # D 座异常温度牌
        if key == "D":
            L.append(("bld_D_temp", link("bld_D_temp", P(cx + 0.62, fy, 0.78),
                        geom_box(0.30, WIN_T, 0.14), mat_tex("SQ_panel_temp"))))
        SVG.append(("rect", cx - sx / 2, cy - sy / 2, sx, sy, "#b9b6ae",
                    "%s座(%d楼)" % (key, WIN_ROWS)))
    add_model("sq_buildings", L)
    DOC.append(("楼宇 A", "3 处火灾隐患窗 (1F/2F)", "中心(-3.20, 3.10), 正面朝 A 街", "楼宇火灾识别 4分"))
    DOC.append(("楼宇 B", "5 处火灾隐患窗", "中心(2.90, 3.10), 正面朝 A 街", "楼宇火灾识别 4分"))
    DOC.append(("楼宇 C", "2 处火灾隐患窗", "中心(-3.20,-3.10), 正面朝 B 街", "楼宇火灾识别 4分"))
    DOC.append(("楼宇 D", "2楼高温窗 + 异常温度牌 68℃", "中心(2.90,-3.10), 正面朝 B 街", "楼宇异常温度 10分"))


# ===================================================================== 站房 + 仪表
def build_station():
    L = []
    cx, cy = STATION["c"]
    sx, sy, sz = STATION["s"]
    L.append(("station_body", link("station_body", P(cx, cy, sz / 2),
                geom_box(sx, sy, sz), mat_rgb((0.80, 0.80, 0.78)))))
    L.append(("station_roof", link("station_roof", P(cx, cy, sz + 0.025),
                geom_box(sx + 0.10, sy + 0.10, 0.05), mat_rgb((0.35, 0.42, 0.60)))))
    L.append(("station_plate", link("station_plate", P(cx, cy + sy / 2 + 0.004, 0.42),
                geom_box(0.40, 0.008, 0.16), mat_tex("SQ_station_plate"))))
    for i, gx in enumerate(GAUGE_X):
        L.append(("gauge_%d" % (i + 1), link("gauge_%d" % (i + 1), P(gx, GAUGE_Y, 0.30),
                    geom_box(0.30, 0.010, 0.21), mat_tex("SQ_gauge_%d" % (i + 1)))))
    add_model("sq_station", L)
    SVG.append(("rect", cx - sx / 2, cy - sy / 2, sx, sy, "#c9c9c4", "站房(2仪表)"))
    DOC.append(("站房 + 仪表", "2 块仪表: 读数 01357 / 24680",
                "站房中心(-3.30,0.55), 仪表在其北面 y=0.815", "站房仪表读取 7分×2"))


# ===================================================================== 红绿灯（独立模型，可动态换灯）
TL_COLORS = {
    "red": ((0.85, 0.08, 0.08), (0.55, 0.06, 0.06), (0.55, 0.06, 0.06)),
    "yellow": ((0.95, 0.78, 0.05), (0.58, 0.10, 0.04), (0.06, 0.35, 0.10)),
    "green": ((0.10, 0.85, 0.20), (0.58, 0.10, 0.04), (0.06, 0.35, 0.10)),
}
TL_LAMP_Z = [0.775, 0.710, 0.645]      # 红 / 黄 / 绿


def traffic_light_sdf(active):
    """生成交通灯 model.sdf 文本；active ∈ red/yellow/green"""
    order = ["red", "yellow", "green"]
    on = TL_COLORS[active][0]
    off_r, off_g = TL_COLORS[active][1], TL_COLORS[active][2]
    links = []
    links.append(link("pole", P(0, 0, 0.30), geom_cyl(0.012, 0.60),
                      mat_rgb((0.38, 0.39, 0.42))))
    links.append(link("base", P(0, 0, 0.012), geom_cyl(0.055, 0.024),
                      mat_rgb((0.30, 0.31, 0.33))))
    links.append(link("housing", P(0, 0, 0.71), geom_box(0.055, 0.10, 0.20),
                      mat_rgb((0.13, 0.13, 0.15))))
    for i, col in enumerate(order):
        if col == active:
            rgb, emi = on, tuple(v * 0.85 for v in on)
        elif col == "red":
            rgb, emi = off_r, None
        elif col == "yellow":
            rgb, emi = off_g, None
        else:
            rgb, emi = off_g, None
        links.append(link("lamp_%s" % col, P(0.036, 0, TL_LAMP_Z[i], 0.0, 1.5708, 0.0),
                          geom_cyl(0.022, 0.014), mat_rgb(rgb, emissive=emi)))
    body = "".join(links)
    return ('<?xml version="1.0" ?>\n<sdf version="1.6">\n'
            '  <model name="sq_traffic_light_%s">\n'
            '    <pose>0 0 0 0 0 0</pose>\n'
            '    <static>1</static>\n    %s\n'
            '  </model>\n</sdf>\n' % (active, body))


TL_CFG = """<?xml version="1.0" ?>
<model>
    <name>sq_traffic_light_%(c)s</name>
    <version>1.0</version>
    <sdf version="1.6">model.sdf</sdf>
    <author><name>sq_community</name></author>
    <description>智慧社区红绿灯（%(cn)s）。配合 traffic_light_controller.py 动态切换。</description>
</model>
"""


# ===================================================================== 人偶立牌
def build_persons():
    L = []
    res_cols = [(0.20, 0.42, 0.78), (0.20, 0.65, 0.35), (0.55, 0.32, 0.72), (0.85, 0.55, 0.15)]
    n_res = n_out = 0
    for i, (x, y, yw, outside) in enumerate(PERSONS):
        if outside:
            body_c = (0.95, 0.45, 0.05)      # 外来人员：醒目橙色
            n_out += 1
        else:
            body_c = res_cols[i % len(res_cols)]
            n_res += 1
        pre = "person_%02d" % i
        L.append((pre + "_base", link(pre + "_base", P(x, y, 0.01),
                    geom_box(0.22, 0.08, 0.02), mat_rgb((0.35, 0.35, 0.36)))))
        L.append((pre + "_body", link(pre + "_body", P(x, y, 0.19),
                    geom_box(0.16, 0.05, 0.34), mat_rgb(body_c))))
        L.append((pre + "_head", link(pre + "_head", P(x, y, 0.415),
                    geom_sph(0.055), mat_rgb((0.90, 0.76, 0.62)))))
        tag = "外来" if outside else ""
        SVG.append(("circle", x, y, 0.09,
                    "#f28c28" if outside else "#4a86c8",
                    "%d%s" % (i + 1, tag)))
    add_model("sq_persons", L)
    DOC.append(("人偶立牌 (A街)", "8 人，其中 2 人为外来人员(橙色)",
                "A街北侧 y=2.50 四具; A街南侧 y=1.10 四具", "人群数量识别 6分/街区"))
    DOC.append(("人偶立牌 (B街)", "8 人，全部为社区人员",
                "B街北侧 y=-1.10 四具; B街南侧 y=-2.50 四具", "人群数量识别 6分/街区"))


# ===================================================================== 垃圾桶
def build_bins():
    L = []
    lid_c = (0.28, 0.29, 0.31)
    for i, (kind, x, opened, load) in enumerate(BINS):
        pre = "bin_%s" % kind
        L.append((pre + "_body", link(pre + "_body", P(x, BIN_Y, 0.15),
                    geom_box(0.17, 0.17, 0.30), mat_tex("SQ_bin_%s" % kind))))
        if opened:
            # 盖子向后掀起 60 度
            L.append((pre + "_lid", link(pre + "_lid", P(x, BIN_Y - 0.11, 0.325, -1.05, 0, 0),
                        geom_box(0.19, 0.19, 0.02), mat_rgb(lid_c))))
        else:
            L.append((pre + "_lid", link(pre + "_lid", P(x, BIN_Y, 0.305),
                        geom_box(0.19, 0.19, 0.02), mat_rgb(lid_c))))
        if load:
            col = (0.85, 0.75, 0.15) if load == "correct" else (0.30, 0.70, 0.85)
            L.append((pre + "_item", link(pre + "_item", P(x, BIN_Y, 0.345),
                        geom_box(0.07, 0.07, 0.08), mat_rgb(col))))
        SVG.append(("rect", x - 0.09, BIN_Y - 0.09, 0.18, 0.18, "#7c8188",
                    "%s%s" % (kind, "开" if opened else "关")))
    add_model("sq_bins", L)
    DOC.append(("垃圾桶 ×4", "可回收(关) / 有害(开·投放正确) / 厨余(开·投放错误) / 其他(关)",
                "中轴服务带 y=0.85, x=-2.30~-1.40, 贴纸朝 A 街", "垃圾桶状态识别 10分"))


# ===================================================================== 指示牌
def build_signs():
    L = []
    for i, (kind, x, y, yw) in enumerate(SIGNS):
        pre = "sign_%d_%s" % (i, kind)
        L.append((pre + "_pole", link(pre + "_pole", P(x, y, 0.22),
                    geom_cyl(0.012, 0.44), mat_rgb((0.42, 0.43, 0.45)))))
        L.append((pre + "_base", link(pre + "_base", P(x, y, 0.012),
                    geom_cyl(0.05, 0.024), mat_rgb((0.30, 0.31, 0.33)))))
        # 牌面绕 z 轴旋转 yw：薄板法线沿本地 ±y
        nx = x - 0.0
        L.append((pre + "_board", link(pre + "_board", P(x, y, 0.40, 0.0, 0.0, yw),
                    geom_box(0.22, 0.010, 0.22), mat_tex("SQ_%s" % kind))))
        SVG.append(("rect", x - 0.11, y - 0.11, 0.22, 0.22, "#f0e6c8",
                    kind.replace("sign_", "")))
    add_model("sq_signs", L)
    DOC.append(("指示牌 ×6", "限速30 / 禁止直行 / 左转 / 人行横道 / 禁止驶入 / 右转",
                "沿途分布在 A 街与 B 街路侧", "指示牌识别与响应 10分"))


# ===================================================================== 电动车
def build_ebikes():
    L = []
    for i, (x, y, yw, st) in enumerate(EBIKES):
        pre = "ebike_%02d" % i
        col = (0.85, 0.25, 0.20) if st == "upright" else (0.55, 0.20, 0.18)
        if st == "upright":
            L.append((pre + "_b", link(pre + "_b", P(x, y, 0.30, 0, 0, yw),
                        geom_box(0.46, 0.09, 0.10), mat_rgb(col))))
            L.append((pre + "_seat", link(pre + "_seat", P(x - 0.10, y, 0.38, 0, 0, yw),
                        geom_box(0.16, 0.11, 0.07), mat_rgb((0.18, 0.18, 0.20)))))
            for s, dy in (("l", -0.05), ("r", 0.05)):
                L.append((pre + "_w" + s, link(pre + "_w" + s, P(x + 0.16, y + dy, 0.11, 0, 1.5708, 0),
                            geom_cyl(0.10, 0.03), mat_rgb((0.10, 0.10, 0.11)))))
        else:
            # 倒伏：整体绕 x 轴转 90 度躺下
            L.append((pre + "_b", link(pre + "_b", P(x, y, 0.05, 1.5708, 0, yw),
                        geom_box(0.46, 0.09, 0.10), mat_rgb(col))))
            L.append((pre + "_seat", link(pre + "_seat", P(x - 0.10, y, 0.05, 1.5708, 0, yw),
                        geom_box(0.16, 0.11, 0.07), mat_rgb((0.18, 0.18, 0.20)))))
        SVG.append(("circle", x, y, 0.075, "#e0554a" if st == "upright" else "#8a3a34", ""))
    add_model("sq_ebikes", L)
    DOC.append(("电动车停车区", "8 辆正常 + 2 辆倒伏 (x 1.15~2.45, y=±0.55)",
                "中轴服务带东段", "电动车状态识别 6分"))
    DOC.append(("电动车违停", "A 街区 2 辆违停 (2.75,1.35)(3.15,1.35)；B 街区 0 辆",
                "停在 A 街车道上", "电动车状态识别 4分"))


# ===================================================================== 汽车 + 车牌
def build_cars():
    L = []
    for i, (plate, x, y) in enumerate(CARS):
        pre = "car_%d" % (i + 1)
        body_c = [(0.88, 0.88, 0.90), (0.20, 0.35, 0.70), (0.18, 0.18, 0.20)][i]
        L.append((pre + "_body", link(pre + "_body", P(x, y, 0.085),
                    geom_box(0.20, 0.42, 0.11), mat_rgb(body_c))))
        L.append((pre + "_cab", link(pre + "_cab", P(x, y - 0.02, 0.175),
                    geom_box(0.18, 0.22, 0.08), mat_rgb((0.45, 0.55, 0.62)))))
        for s, dx in (("l", -0.09), ("r", 0.09)):
            for f, dy in (("f", 0.14), ("b", -0.14)):
                L.append((pre + "_w%s%s" % (s, f), link(pre + "_w%s%s" % (s, f),
                            P(x + dx, y + dy, 0.045, 1.5708, 0, 0),
                            geom_cyl(0.045, 0.03), mat_rgb((0.09, 0.09, 0.10)))))
        # 前车牌（朝 +y，即朝 A 街）
        L.append((pre + "_plate", link(pre + "_plate", P(x, y + 0.213, 0.075),
                    geom_box(0.14, 0.006, 0.045), mat_tex("SQ_%s" % plate))))
        SVG.append(("rect", x - 0.10, y - 0.21, 0.20, 0.42, "#8a8f96", "车%d" % (i + 1)))
    add_model("sq_cars", L)
    DOC.append(("停车场 + 3 辆车", "车牌 苏E·12345 / 苏E·67890 / 苏E·A8888",
                "车位 x=3.25/3.80/4.35, y=-0.35, 车头朝 +y", "车辆车牌识别 4分×3"))


# ===================================================================== 世界装配
def build_world():
    head = """<?xml version="1.0" ?>
<sdf version="1.6">
  <world name="sq_community">
    <scene>
      <ambient>0.65 0.65 0.65 1</ambient>
      <background>0.72 0.78 0.85 1</background>
      <shadows>1</shadows>
      <grid>0</grid>
    </scene>
    <light name='sun' type='directional'>
      <cast_shadows>1</cast_shadows>
      <pose frame=''>0 0 12 0 -0 0</pose>
      <diffuse>0.95 0.95 0.92 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation><range>1000</range><constant>0.9</constant>
        <linear>0.01</linear><quadratic>0.001</quadratic></attenuation>
      <direction>-0.4 0.3 -1</direction>
    </light>
    <light name='fill_n' type='point'>
      <pose frame=''>-2.0 2.0 2.2 0 -0 0</pose>
      <diffuse>0.5 0.5 0.5 1</diffuse><specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>12</range><constant>0.6</constant>
        <linear>0.01</linear><quadratic>0.002</quadratic></attenuation>
      <cast_shadows>0</cast_shadows><direction>0 0 -1</direction>
    </light>
    <light name='fill_s' type='point'>
      <pose frame=''>2.5 -2.0 2.2 0 -0 0</pose>
      <diffuse>0.5 0.5 0.5 1</diffuse><specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>12</range><constant>0.6</constant>
        <linear>0.01</linear><quadratic>0.002</quadratic></attenuation>
      <cast_shadows>0</cast_shadows><direction>0 0 -1</direction>
    </light>
    <light name='fill_c' type='point'>
      <pose frame=''>0.6 0.0 2.4 0 -0 0</pose>
      <diffuse>0.45 0.45 0.45 1</diffuse><specular>0.1 0.1 0.1 1</specular>
      <attenuation><range>12</range><constant>0.6</constant>
        <linear>0.01</linear><quadratic>0.002</quadratic></attenuation>
      <cast_shadows>0</cast_shadows><direction>0 0 -1</direction>
    </light>
    <gravity>0 0 -9.8</gravity>
    <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
    <atmosphere type='adiabatic'/>
    <physics name='default_physics' default='0' type='ode'>
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1</real_time_factor>
      <real_time_update_rate>1000</real_time_update_rate>
    </physics>
    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <latitude_deg>0</latitude_deg><longitude_deg>0</longitude_deg>
      <elevation>0</elevation><heading_deg>0</heading_deg>
    </spherical_coordinates>

    <!-- 红绿灯：先摆一盏红灯，运行期由 traffic_light_controller.py 动态换灯 -->
    <include>
      <uri>model://sq_traffic_light_red</uri>
      <pose>%s</pose>
      <name>sq_tl_1</name>
    </include>
    <include>
      <uri>model://sq_traffic_light_red</uri>
      <pose>%s</pose>
      <name>sq_tl_2</name>
    </include>

""" % (P(TL1[0], TL1[1], 0, 0, 0, TL1[2]), P(TL2[0], TL2[1], 0, 0, 0, TL2[2]))

    body = ""
    for name, links in MODELS:
        body += "    <model name='%s'>\n      <static>1</static>\n      <pose>0 0 0 0 0 0</pose>\n" % name
        for lname, lx in links:
            body += "      " + lx + "\n"
        body += "    </model>\n"
    tail = """    <gui fullscreen='0'>
      <camera name='user_camera'>
        <pose frame=''>-6.5 -6.5 7.5 0 0.87 0.785</pose>
        <view_controller>orbit</view_controller>
        <projection_type>perspective</projection_type>
      </camera>
    </gui>
  </world>
</sdf>
"""
    return head + body + tail


# ===================================================================== 平面图 SVG
CAT = {
    "rect": None,
}


def build_svg():
    S = 96.0
    OX, OY = 560.0, 400.0

    def sx(x):
        return OX + x * S

    def sy(y):
        return OY - y * S

    W, H = 1120, 800
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="100%%" '
           'style="background:#fbfbfa;font-family:-apple-system,Segoe UI,Microsoft YaHei,sans-serif">'
           % (W, H)]
    out.append('<rect width="%d" height="%d" fill="#fbfbfa"/>' % (W, H))
    out.append('<text x="24" y="36" font-size="21" font-weight="700" fill="#1c1e22">'
               '智慧社区仿真场地平面图（俯视）</text>' % ())
    out.append('<text x="24" y="58" font-size="13" fill="#5a5f66">'
               'x 向东 / y 向北　场地 10.0m × 7.2m　waffle 出生点 (-4.60, 1.80) 朝向 +x</text>')

    # 网格
    for gx in range(-5, 6):
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e6e6e2" stroke-width="1"/>'
                   % (sx(gx), sy(-3.6), sx(gx), sy(3.6)))
    for gy in range(-3, 4):
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e6e6e2" stroke-width="1"/>'
                   % (sx(-5), sy(gy), sx(5), sy(gy)))

    for item in SVG:
        kind = item[0]
        if kind == "rect":
            _, x, y, w, h, fill, lab = item
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                       'stroke="#9a9a96" stroke-width="1.2" rx="1"/>'
                       % (sx(x), sy(y + h), w * S, h * S, fill))
            if lab:
                out.append('<text x="%.1f" y="%.1f" font-size="11" fill="#22252a" '
                           'text-anchor="middle" dominant-baseline="middle">%s</text>'
                           % (sx(x + w / 2), sy(y + h / 2), lab))
        elif kind == "circle":
            _, x, y, r, fill, lab = item
            out.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="#5c5c58" '
                       'stroke-width="1"/>' % (sx(x), sy(y), r * S, fill))
            if lab:
                out.append('<text x="%.1f" y="%.1f" font-size="9" fill="#fff" '
                           'text-anchor="middle" dominant-baseline="middle">%s</text>'
                           % (sx(x), sy(y), lab))

    # 红绿灯标记
    for (x, y, yw), nm in ((TL1, "红绿灯1"), (TL2, "红绿灯2")):
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#4d4f55" '
                   'stroke="#1c1e22" stroke-width="1.5"/>' % (sx(x) - 9, sy(y) - 16, 18, 32))
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#e02a2a"/>' % (sx(x), sy(y) - 8))
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#f2d02a"/>' % (sx(x), sy(y)))
        out.append('<circle cx="%.1f" cy="%.1f" r="5" fill="#22c43c"/>' % (sx(x), sy(y) + 8))
        out.append('<text x="%.1f" y="%.1f" font-size="11" fill="#1c1e22" text-anchor="middle">%s</text>'
                   % (sx(x), sy(y) + 30, nm))
    # 机器人出生点
    out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#1f7a3d" '
               'stroke="#0e3d1f" stroke-width="1"/>'
               % (sx(-4.60) + 12, sy(1.80), sx(-4.60) - 7, sy(1.80) - 8, sx(-4.60) - 7, sy(1.80) + 8))
    out.append('<text x="%.1f" y="%.1f" font-size="11" fill="#1f7a3d" font-weight="700">机器人出生</text>'
               % (sx(-4.60) - 22, sy(1.80) - 14))

    # 图例
    leg = [("#4a4d52", "车道"), ("#3a3d42", "地块"), ("#568c46", "绿化"),
           ("#b9b6ae", "楼宇"), ("#c9c9c4", "站房"), ("#f28c28", "外来人员"),
           ("#4a86c8", "社区人员"), ("#e0554a", "电动车正常"), ("#8a3a34", "电动车倒伏"),
           ("#7c8188", "垃圾桶"), ("#8a8f96", "汽车"), ("#f0e6c8", "指示牌")]
    bx, by = 700, 640
    out.append('<rect x="%d" y="%d" width="396" height="128" fill="#ffffff" stroke="#d8d8d4" rx="6"/>'
               % (bx - 12, by - 26))
    out.append('<text x="%d" y="%d" font-size="13" font-weight="700" fill="#1c1e22">图例</text>'
               % (bx, by - 8))
    for i, (c, t) in enumerate(leg):
        cx = bx + (i % 3) * 128
        cy = by + 12 + (i // 3) * 22
        out.append('<rect x="%d" y="%d" width="13" height="13" fill="%s" stroke="#8a8a86"/>'
                   % (cx, cy - 11, c))
        out.append('<text x="%d" y="%d" font-size="11.5" fill="#33363b">%s</text>' % (cx + 19, cy, t))
    out.append("</svg>")
    return "\n".join(out)


# ===================================================================== 场景清单 / 答案键
def road_of(y):
    return "A" if y > 0 else "B"


def build_manifest():
    """输出场地真值清单：既是感知算法的答案键，也可直接作为复赛文档的场地说明附录"""
    import collections
    m = collections.OrderedDict()
    m["meta"] = {
        "package": "sq_community",
        "world": "worlds/sq_community.world",
        "arena_m": [2 * AX, 2 * AY],
        "robot": {"model": "turtlebot3_waffle",
                  "start_xyz": list(ROBOT_START[:3]), "start_yaw": 0.0,
                  "sensors": {"laser": "scan (360°, 0.12~3.5m)",
                              "rgb": "camera/rgb/image_raw 1920x1080",
                              "depth": "camera/depth/image_raw"}},
        "a_axis": "x 向东, y 向北, z 向上; 单位 m",
        "usage": "本文件是场地真值(answer key)，可用于校验视觉识别结果，亦可作为复赛技术方案的场地说明附录。",
    }
    m["traffic_lights"] = {
        "count": 2,
        "cycle_s": {"red": 10, "green": 15, "yellow": 3},
        "models": ["sq_traffic_light_red", "sq_traffic_light_green", "sq_traffic_light_yellow"],
        "items": [
            {"id": "sq_tl_1", "xy": [TL1[0], TL1[1]], "face": "西(-x)", "serves": "A街东行"},
            {"id": "sq_tl_2", "xy": [TL2[0], TL2[1]], "face": "东(+x)", "serves": "B街西行"},
        ],
        "wait_lines": {"street_A_x": WAIT_A_X, "street_B_x": WAIT_B_X},
    }
    m["persons"] = {
        "total": len(PERSONS),
        "street_A": sum(1 for p in PERSONS if road_of(p[1]) == "A"),
        "street_B": sum(1 for p in PERSONS if road_of(p[1]) == "B"),
        "outsiders_total": sum(1 for p in PERSONS if p[3]),
        "outsiders_in_A": sum(1 for p in PERSONS if p[3] and road_of(p[1]) == "A"),
        "color_rule": "橙色 = 非社区人员(外来)；蓝/绿/紫/棕 = 社区人员",
        "items": [{"id": "person_%02d" % i, "xy": [p[0], p[1]], "is_outsider": p[3]}
                  for i, p in enumerate(PERSONS)],
    }
    m["bins"] = {"count": len(BINS), "items": [
        {"id": "bin_%s" % k, "type": k, "open": o, "load": ld, "xy": [x, BIN_Y]}
        for k, x, o, ld in BINS]}
    m["buildings"] = {
        "count": 4,
        "fire_windows": {k: len(BLD[k].get("fire", ())) for k in ("A", "B", "C")},
        "fire_window_rule": "窗户为 FIRE 贴图(橙红火焰)者 = 火灾隐患；蓝色普通窗 = 正常",
        "hot": {"building": "D", "window_index": BLD["D"]["hot"],
                "floor": BLD["D"]["hot"] // WIN_COLS + 1, "temp_c": 68,
                "xy": list(BLD["D"]["c"])},
        "items": [{"id": "bld_%s" % k, "xy": list(BLD[k]["c"]), "size": list(BLD[k]["s"])}
                  for k in ("A", "B", "C", "D")],
        "floors": WIN_ROWS,
    }
    m["station"] = {
        "xy": list(STATION["c"]),
        "gauges": [{"id": "gauge_%d" % (i + 1), "reading": r, "xy": [GAUGE_X[i], GAUGE_Y]}
                   for i, r in enumerate(["01357", "24680"])],
    }
    PLATES = {"plate_A": "苏E·12345", "plate_B": "苏E·67890", "plate_C": "苏E·A8888"}
    m["cars"] = {"count": len(CARS), "items": [
        {"id": "car_%d" % (i + 1), "plate": PLATES[pl], "xy": [x, y], "heading": "+y (朝A街)"}
        for i, (pl, x, y) in enumerate(CARS)]}
    m["ebikes"] = {
        "parking_area": {
            "upright": sum(1 for e in EBIKES[:10] if e[3] == "upright"),
            "fallen": sum(1 for e in EBIKES[:10] if e[3] == "fallen")},
        "illegal_parking": {
            "street_A": sum(1 for e in EBIKES[10:] if road_of(e[1]) == "A"),
            "street_B": sum(1 for e in EBIKES[10:] if road_of(e[1]) == "B")},
        "fallen_pose": "车体绕 x 轴转 90° 平躺于地面",
    }
    m["signs"] = {"count": len(SIGNS),
                  "items": [{"id": "sign_%s" % k, "xy": [x, y]} for k, x, y, _ in SIGNS]}
    m["parking"] = {
        "bays": [{"id": "bay_%d" % (i + 1), "xy": [x, PARK_C[1]]}
                 for i, x in enumerate(PARK_BAY_X)],
        "final_slot": {"xy": [PARK_SLOT[0], PARK_SLOT[1]],
                       "size": [PARK_SLOT[2], PARK_SLOT[3]],
                       "required_heading": "车头朝向街道(A街一侧)"},
    }
    m["answer_key"] = {
        "红绿灯": "红灯10s→绿灯15s→黄灯3s；共两处；红灯亮时车头不得越过等待线 x=-0.75(A街) / x=+0.75(B街)",
        "人群数量": "社区内共有16人，其中A街8人，B街8人，发现2名非社区人员在A街",
        "垃圾桶状态": "可回收垃圾桶关闭；有害垃圾桶打开、投放正确；厨余垃圾桶打开、投放错误；其他垃圾桶关闭",
        "楼宇火灾": "A座发现火灾隐患3个，B座5个，C座2个",
        "楼宇异常温度": "D座在2楼处发现高温，约68℃",
        "站房仪表": "1号表读数01357，2号表读数24680",
        "车辆车牌": "1号车位苏E·12345，2号车位苏E·67890，3号车位苏E·A8888",
        "电动车状态": "A街区有2辆电动车违停，B街区无违停；停车区内电动车正常8辆，倒伏2辆",
        "指示牌": "沿途6块：限速30 / 禁止直行 / 左转 / 人行横道 / 禁止驶入 / 右转",
        "停车": "需停入A街北侧泊车位(x=4.45, y=2.80)，车头朝向街道",
    }
    return m


# ===================================================================== 主流程
def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    a = ap.parse_args()
    pkg = a.pkg
    OUT = pkg

    build_ground()
    build_markings()
    build_walls()
    build_buildings()
    build_station()
    build_persons()
    build_bins()
    build_signs()
    build_ebikes()
    build_cars()

    os.makedirs(os.path.join(pkg, "worlds"), exist_ok=True)
    os.makedirs(os.path.join(pkg, "docs"), exist_ok=True)
    wpath = os.path.join(pkg, "worlds", "sq_community.world")
    with open(wpath, "w", encoding="utf-8") as f:
        f.write(build_world())

    for c, cn in (("red", "红灯"), ("green", "绿灯"), ("yellow", "黄灯")):
        d = os.path.join(pkg, "models", "sq_traffic_light_%s" % c)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "model.sdf"), "w", encoding="utf-8") as f:
            f.write(traffic_light_sdf(c))
        with open(os.path.join(d, "model.config"), "w", encoding="utf-8") as f:
            f.write(TL_CFG % {"c": c, "cn": cn})

    spath = os.path.join(pkg, "docs", "sq_community_plan.svg")
    with open(spath, "w", encoding="utf-8") as f:
        f.write(build_svg())

    cpath = os.path.join(pkg, "docs", "元素-任务对照表.csv")
    with open(cpath, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["分类", "场地元素", "位置/规格", "对应赛项"])
        for row in DOC:
            w.writerow(row)

    import json
    mpath = os.path.join(pkg, "docs", "scene_manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(build_manifest(), f, ensure_ascii=False, indent=2)

    print("world: %s (%.1f KB)" % (wpath, os.path.getsize(wpath) / 1024.0))
    print("svg  : %s" % spath)
    print("csv  : %s" % cpath)
    print("manifest: %s" % mpath)
    print("模型数: %d, link 数: %d, SVG 图元: %d"
          % (len(MODELS), sum(len(l) for _, l in MODELS), len(SVG)))


if __name__ == "__main__":
    main()
