# -*- coding: utf-8 -*-
"""
智慧社区仿真场地 - 贴图与材质生成器

用 PIL 生成带真实文字/数字的贴图（车牌、仪表读数、指示牌、火灾窗口、楼号…），
并统一放进一个模型目录 models/sq_textures/ 下，同时自动生成 Ogre 材质脚本，
这样 SDF 里只要写：

  <material>
    <script>
      <uri>model://sq_textures/materials/scripts</uri>
      <uri>model://sq_textures/materials/textures</uri>
      <name>SQ_plate_A</name>
    </script>
  </material>

用法: python gen_textures.py --out <package_root>/models
"""
import os, argparse, math
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]
_fc = {}
MATS = []          # [(material_name, png_filename)]
OUT = None         # <models>/sq_textures


def font(size):
    if size not in _fc:
        for p in FONT_CANDIDATES:
            if os.path.exists(p):
                try:
                    _fc[size] = ImageFont.truetype(p, size)
                    break
                except Exception:
                    pass
        else:
            _fc[size] = ImageFont.load_default()
    return _fc[size]


def canvas(w, h, bg):
    im = Image.new("RGB", (w, h), bg)
    return im, ImageDraw.Draw(im)


def save(im, name):
    """保存贴图并登记材质名"""
    tex = os.path.join(OUT, "materials", "textures")
    os.makedirs(tex, exist_ok=True)
    p = os.path.join(tex, "%s.png" % name)
    im.save(p)
    MATS.append(("SQ_%s" % name, "%s.png" % name))
    return p


# ================================================================ 车牌
def gen_plate(name, text):
    W, H = 440, 140
    im, d = canvas(W, H, (255, 255, 255))
    d.rounded_rectangle([4, 4, W - 4, H - 4], radius=14, fill=(0, 60, 170))
    d.rounded_rectangle([10, 10, W - 10, H - 10], radius=10, outline=(255, 255, 255), width=4)
    d.text((W // 2, H // 2 - 4), text, font=font(92), fill=(255, 255, 255), anchor="mm")
    return save(im, name)


# ================================================================ 仪表盘
def gen_gauge(name, reading, needle_deg):
    W, H = 420, 300
    im, d = canvas(W, H, (30, 32, 36))
    d.rectangle([0, 0, W - 1, H - 1], outline=(120, 124, 130), width=4)
    cx, cy, r = 105, 150, 86
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(238, 238, 232), outline=(60, 60, 60), width=4)
    for i in range(11):
        a = math.radians(210 - i * 24)
        d.line([cx + math.cos(a) * (r - 18), cy - math.sin(a) * (r - 18),
                cx + math.cos(a) * (r - 5), cy - math.sin(a) * (r - 5)], fill=(40, 40, 40), width=3)
    a = math.radians(needle_deg)
    d.line([cx, cy, cx + math.cos(a) * (r - 16), cy - math.sin(a) * (r - 16)],
           fill=(210, 30, 30), width=5)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(40, 40, 40))
    d.text((cx, cy + 42), "MPa", font=font(24), fill=(60, 60, 60), anchor="mm")
    d.rounded_rectangle([212, 96, 400, 204], radius=10, fill=(8, 20, 8), outline=(90, 90, 90), width=3)
    d.text((306, 150), reading, font=font(72), fill=(60, 255, 120), anchor="mm")
    d.text((306, 234), "SQ-METER", font=font(26), fill=(160, 165, 170), anchor="mm")
    return save(im, name)


# ================================================================ 窗户
def gen_window(name, kind):
    W, H = 160, 200
    if kind == "fire":
        im, d = canvas(W, H, (60, 20, 10))
        d.rectangle([0, 0, W - 1, H - 1], outline=(20, 20, 20), width=6)
        for cx, cy, rr, col in [(80, 155, 58, (255, 60, 0)), (58, 130, 42, (255, 140, 0)),
                                (104, 120, 38, (255, 180, 20)), (80, 96, 30, (255, 230, 90))]:
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
        d.text((80, 30), "FIRE", font=font(34), fill=(255, 245, 200), anchor="mm")
    elif kind == "hot":
        im, d = canvas(W, H, (80, 25, 25))
        d.rectangle([0, 0, W - 1, H - 1], outline=(20, 20, 20), width=6)
        d.line([80, 46, 80, 176], fill=(240, 240, 240), width=12)
        d.ellipse([60, 150, 100, 190], fill=(230, 40, 40))
        d.line([80, 170, 80, 66], fill=(230, 40, 40), width=12)
        d.text((80, 22), "HOT", font=font(28), fill=(255, 200, 120), anchor="mm")
    else:
        im, d = canvas(W, H, (150, 190, 220))
        d.rectangle([0, 0, W - 1, H - 1], outline=(230, 230, 230), width=8)
        d.line([80, 6, 80, H - 6], fill=(230, 230, 230), width=7)
        d.line([6, 100, W - 6, 100], fill=(230, 230, 230), width=7)
    return save(im, name)


# ================================================================ 指示牌
def gen_sign(name, kind):
    S = 320
    im, d = canvas(S, S, (235, 235, 235))
    d.rectangle([0, 0, S - 1, S - 1], fill=(235, 235, 235), outline=(90, 90, 90), width=8)
    if kind == "no_straight":
        d.ellipse([26, 26, S - 26, S - 26], fill=(255, 255, 255), outline=(210, 30, 30), width=26)
        d.line([160, 240, 160, 104], fill=(30, 30, 30), width=22)
        d.polygon([(160, 68), (128, 130), (192, 130)], fill=(30, 30, 30))
        d.line([72, 248, 248, 72], fill=(210, 30, 30), width=26)
    elif kind == "turn_left":
        d.ellipse([26, 26, S - 26, S - 26], fill=(20, 80, 190), outline=(255, 255, 255), width=12)
        d.line([196, 236, 196, 140, 122, 140], fill=(255, 255, 255), width=24)
        d.polygon([(96, 140), (152, 108), (152, 172)], fill=(255, 255, 255))
    elif kind == "turn_right":
        d.ellipse([26, 26, S - 26, S - 26], fill=(20, 80, 190), outline=(255, 255, 255), width=12)
        d.line([124, 236, 124, 140, 198, 140], fill=(255, 255, 255), width=24)
        d.polygon([(224, 140), (168, 108), (168, 172)], fill=(255, 255, 255))
    elif kind == "no_entry":
        d.ellipse([26, 26, S - 26, S - 26], fill=(210, 30, 30), outline=(255, 255, 255), width=12)
        d.rectangle([76, 142, 244, 178], fill=(255, 255, 255))
    elif kind == "crosswalk":
        d.rectangle([0, 0, S - 1, S - 1], fill=(20, 80, 190), outline=(255, 255, 255), width=10)
        d.polygon([(160, 56), (108, 118), (212, 118)], fill=(255, 255, 255))
        for i in range(5):
            d.rectangle([70 + i * 38, 168, 92 + i * 38, 252], fill=(255, 255, 255))
    elif kind == "speed30":
        d.ellipse([26, 26, S - 26, S - 26], fill=(255, 255, 255), outline=(210, 30, 30), width=26)
        d.text((160, 162), "30", font=font(150), fill=(20, 20, 20), anchor="mm")
    return save(im, name)


# ================================================================ 垃圾桶标贴
def gen_bin(name, kind):
    W, H = 240, 240
    bg, cn, en = {
        "recycle": ((20, 90, 200), "可回收物", "RECYCLE"),
        "hazard":  ((200, 30, 40), "有害垃圾", "HAZARD"),
        "kitchen": ((30, 150, 70), "厨余垃圾", "KITCHEN"),
        "other":   ((110, 115, 120), "其他垃圾", "OTHER"),
    }[kind]
    im, d = canvas(W, H, (245, 245, 245))
    d.rectangle([0, 0, W - 1, H - 1], fill=bg)
    d.rectangle([10, 10, W - 11, H - 11], outline=(255, 255, 255), width=5)
    d.text((120, 86), cn, font=font(50), fill=(255, 255, 255), anchor="mm")
    d.text((120, 154), en, font=font(30), fill=(255, 255, 255), anchor="mm")
    d.text((120, 202), "SQ-BIN", font=font(22), fill=(240, 240, 240), anchor="mm")
    return save(im, name)


# ================================================================ 牌匾/标牌
def gen_board(name, main, sub, bg=(255, 255, 255), fg=(25, 25, 25)):
    W, H = 420, 190
    im, d = canvas(W, H, bg)
    d.rectangle([0, 0, W - 1, H - 1], fill=bg, outline=(70, 70, 70), width=6)
    d.text((210, 76), main, font=font(76), fill=fg, anchor="mm")
    d.text((210, 146), sub, font=font(30), fill=fg, anchor="mm")
    return save(im, name)


# ================================================================ 地面
def gen_ground(name, kind):
    if kind == "asphalt":
        im, d = canvas(256, 256, (78, 80, 84))
        for i in range(0, 256, 8):
            d.line([0, i, 256, i], fill=(74, 76, 80), width=1)
    elif kind == "paving":
        im, d = canvas(256, 256, (176, 174, 168))
        for i in range(0, 260, 32):
            d.line([0, i, 256, i], fill=(158, 156, 150), width=2)
            d.line([i, 0, i, 256], fill=(158, 156, 150), width=2)
    elif kind == "parking":
        im, d = canvas(256, 256, (78, 80, 84))
        d.rectangle([6, 6, 249, 249], outline=(245, 245, 245), width=10)
        d.text((128, 128), "P", font=font(120), fill=(240, 240, 240), anchor="mm")
    elif kind == "crosswalk":
        im, d = canvas(256, 256, (78, 80, 84))
        for i in range(6):
            d.rectangle([10 + i * 42, 0, 34 + i * 42, 256], fill=(240, 240, 240))
    elif kind == "lane_dash":
        im, d = canvas(64, 256, (78, 80, 84))
        d.rectangle([24, 0, 40, 150], fill=(240, 240, 240))
    elif kind == "lane_solid":
        im, d = canvas(64, 256, (78, 80, 84))
        d.rectangle([24, 0, 40, 256], fill=(235, 235, 235))
    elif kind == "stopline":
        im, d = canvas(256, 64, (78, 80, 84))
        d.rectangle([0, 16, 256, 48], fill=(245, 245, 245))
    elif kind == "grass":
        im, d = canvas(256, 256, (86, 140, 70))
        for i in range(700):
            d.point(((i * 97) % 256, (i * 151) % 256), fill=(112, 168, 92))
    else:
        im, d = canvas(256, 256, (120, 120, 120))
    return save(im, name)


# ================================================================ 汇总清单
MATERIAL_INDEX = {
    "plate_A": "苏E·12345 车牌", "plate_B": "苏E·67890 车牌", "plate_C": "苏E·A8888 车牌",
    "gauge_1": "仪表读数 01357", "gauge_2": "仪表读数 24680",
    "win_normal": "普通窗", "win_fire": "火灾隐患窗", "win_hot": "高温窗",
    "sign_no_straight": "禁止直行牌", "sign_turn_left": "左转牌",
    "sign_turn_right": "右转牌", "sign_no_entry": "禁止驶入牌",
    "sign_crosswalk": "人行横道牌", "sign_speed30": "限速30牌",
    "bin_recycle": "可回收垃圾桶贴", "bin_hazard": "有害垃圾桶贴",
    "bin_kitchen": "厨余垃圾桶贴", "bin_other": "其他垃圾桶贴",
    "bldg_A": "A座楼牌", "bldg_B": "B座楼牌", "bldg_C": "C座楼牌", "bldg_D": "D座楼牌",
    "station_plate": "站房牌", "start_plate": "出发区牌",
    "floor_1f": "1楼楼层牌", "floor_2f": "2楼楼层牌", "panel_temp": "D座异常温度牌 68℃",
    "gnd_asphalt": "沥青路面", "gnd_paving": "人行道铺装", "gnd_parking": "停车位",
    "gnd_crosswalk": "斑马线", "gnd_lane_dash": "车道虚线",
    "gnd_lane_solid": "车道实线", "gnd_stopline": "停止线", "gnd_grass": "绿化带",
}

MAT_TPL = """// 智慧社区仿真场地 - 自动生成，请勿手改
material %(mat)s
{
  technique
  {
    pass
    {
      ambient 0.9 0.9 0.9 1
      diffuse 1.0 1.0 1.0 1
      specular 0.02 0.02 0.02 1
      texture_unit
      {
        texture %(png)s
      }
    }
  }
}
"""

CONFIG_TPL = """<?xml version="1.0" ?>
<model>
    <name>sq_textures</name>
    <version>1.0</version>
    <sdf version="1.6">model.sdf</sdf>
    <description>智慧社区场地的全部贴图材质（车牌/仪表/指示牌/窗户/地面）。仅提供材质，不实例化。</description>
</model>
"""

SDF_TPL = """<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="sq_textures">
    <static>1</static>
    <link name="link"/>
  </model>
</sdf>
"""


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="models 目录, e.g. .../src/sq_community/models")
    a = ap.parse_args()
    OUT = os.path.join(a.out, "sq_textures")
    os.makedirs(OUT, exist_ok=True)

    gen_plate("plate_A", "苏E·12345")
    gen_plate("plate_B", "苏E·67890")
    gen_plate("plate_C", "苏E·A8888")
    gen_gauge("gauge_1", "01357", 62)
    gen_gauge("gauge_2", "24680", 128)
    gen_window("win_normal", "normal")
    gen_window("win_fire", "fire")
    gen_window("win_hot", "hot")
    gen_sign("sign_no_straight", "no_straight")
    gen_sign("sign_turn_left", "turn_left")
    gen_sign("sign_turn_right", "turn_right")
    gen_sign("sign_no_entry", "no_entry")
    gen_sign("sign_crosswalk", "crosswalk")
    gen_sign("sign_speed30", "speed30")
    gen_bin("bin_recycle", "recycle")
    gen_bin("bin_hazard", "hazard")
    gen_bin("bin_kitchen", "kitchen")
    gen_bin("bin_other", "other")
    gen_board("bldg_A", "A 座", "ART BUILDING")
    gen_board("bldg_B", "B 座", "BUSINESS BUILDING")
    gen_board("bldg_C", "C 座", "CIVIC BUILDING")
    gen_board("bldg_D", "D 座", "DORM BUILDING")
    gen_board("station_plate", "站 房", "METER ROOM", bg=(20, 80, 190), fg=(255, 255, 255))
    gen_board("start_plate", "出 发 区", "START", bg=(30, 150, 70), fg=(255, 255, 255))
    gen_board("floor_1f", "1F", "FLOOR 1", bg=(30, 34, 40), fg=(255, 255, 255))
    gen_board("floor_2f", "2F", "FLOOR 2", bg=(30, 34, 40), fg=(255, 255, 255))
    gen_board("panel_temp", "68℃", "2F 异常温度", bg=(200, 40, 40), fg=(255, 255, 255))
    for g in ["asphalt", "paving", "parking", "crosswalk", "lane_dash",
              "lane_solid", "stopline", "grass"]:
        gen_ground("gnd_" + g, g)

    # 材质脚本
    sd = os.path.join(OUT, "materials", "scripts")
    os.makedirs(sd, exist_ok=True)
    with open(os.path.join(sd, "sq_textures.material"), "w", encoding="utf-8") as f:
        f.write("".join(MAT_TPL % {"mat": m, "png": p} for m, p in MATS))
    with open(os.path.join(OUT, "model.config"), "w", encoding="utf-8") as f:
        f.write(CONFIG_TPL)
    with open(os.path.join(OUT, "model.sdf"), "w", encoding="utf-8") as f:
        f.write(SDF_TPL)

    print("贴图 %d 张, 材质 %d 条 -> %s" % (len(MATS), len(MATS), OUT))
    missing = [m for m in MATERIAL_INDEX if m not in dict(MATS).keys() and
               ("SQ_" + m) not in [x[0] for x in MATS]]
    print("清单未覆盖: %s" % (missing if missing else "无"))


if __name__ == "__main__":
    main()
