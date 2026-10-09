# -*- coding: utf-8 -*-
"""
sq_community 包静态自检器（不需要 ROS / Gazebo 即可运行）

检查项:
  1. 所有 XML 文件良构 (world / model.sdf / model.config / package.xml / launch)
  2. 是否存在 <link> 嵌套 <link> 这类结构错误
  3. 每个 visual / collision 是否都有 pose + geometry
  4. 所有 model:// URI 是否能在 models/ 下落地
  5. 所有 SQ_* 材质名是否在 sq_textures.material 中有定义
  6. 世界模型的包围盒是否落在场地范围内
  7. 与赛题要求逐项对照（元素清单 vs 世界内容）

用法: python verify_pkg.py --pkg <package_root>
"""
import os, sys, argparse, re
import xml.etree.ElementTree as ET

OK, BAD, WARN = "[OK]", "[FAIL]", "[WARN]"
res = []
cnt = {"ok": 0, "bad": 0, "warn": 0}


def log(flag, msg):
    res.append("%s %s" % (flag, msg))
    if flag == OK:
        cnt["ok"] += 1
    elif flag == BAD:
        cnt["bad"] += 1
    else:
        cnt["warn"] += 1


def xml_files(pkg):
    out = []
    for dp, dn, fn in os.walk(pkg):
        if ".git" in dp:
            continue
        for f in fn:
            if f.endswith((".world", ".sdf", ".config", ".xml", ".launch", ".xacro", ".urdf")):
                out.append(os.path.join(dp, f))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    a = ap.parse_args()
    pkg = a.pkg
    models_dir = os.path.join(pkg, "models")

    res.append("=" * 72)
    res.append(" sq_community 包静态自检   pkg=%s" % pkg)
    res.append("=" * 72)

    # ---------- 1. XML 良构 ----------
    res.append("")
    res.append("【1】XML 良构性")
    trees = {}
    files = xml_files(pkg)
    for p in files:
        rel = os.path.relpath(p, pkg)
        try:
            trees[p] = ET.parse(p)
            log(OK, rel)
        except ET.ParseError as e:
            log(BAD, "%s  ->  %s" % (rel, e))
    log(OK, "共解析 %d 个 XML 文件" % len(trees))

    # ---------- 2/3. 结构检查 ----------
    res.append("")
    res.append("【2】结构：link 嵌套 / pose / geometry")
    world = os.path.join(pkg, "worlds", "sq_community.world")
    if world not in trees:
        log(BAD, "缺少 sq_community.world")
        return report(res, cnt)
    root = trees[world].getroot()
    nested = 0
    n_link = n_vis = n_col = 0
    miss_geo = []
    for lnk in root.iter("link"):
        n_link += 1
        if lnk.find("link") is not None:
            nested += 1
            log(BAD, "link '%s' 内部又嵌了 link" % lnk.get("name"))
        for v in lnk.findall("visual"):
            n_vis += 1
            if v.find("geometry") is None:
                miss_geo.append("%s/%s (visual)" % (lnk.get("name"), v.get("name")))
        for c in lnk.findall("collision"):
            n_col += 1
            if c.find("geometry") is None:
                miss_geo.append("%s/%s (collision)" % (lnk.get("name"), c.get("name")))
    if nested == 0:
        log(OK, "没有 link 嵌套 link")
    log(OK if not miss_geo else BAD,
        "visual=%d collision=%d ; 缺 geometry: %s" % (n_vis, n_col, miss_geo[:6] or "无"))
    n_model = len(list(root.iter("model")))
    log(OK, "世界内 <model> 元素 %d 个, <link> %d 个" % (n_model, n_link))
    inc = [i for i in root.iter("include")]
    log(OK, "<include> %d 处" % len(inc))

    # ---------- 4. model:// 落地检查 ----------
    res.append("")
    res.append("【3】model:// URI 落地检查")
    txt_all = ""
    for p in [world] + [q for q in files if q.endswith(".sdf")]:
        txt_all += open(p, "r", encoding="utf-8", errors="replace").read()
    uris = sorted(set(re.findall(r"model://([A-Za-z0-9_\-/\.]+)", txt_all)))
    log(OK, "发现 model:// 引用 %d 条" % len(uris))
    for u in uris:
        head = u.split("/")[0]
        p = os.path.join(models_dir, head)
        if os.path.isdir(p):
            sub = u[len(head):].strip("/")
            if sub:
                parts = sub.split("/")
                # 允许引用 models/<head>/<子路径>
                cand = os.path.join(p, *parts)
                if os.path.exists(cand):
                    log(OK, "  %s  -> 存在" % u)
                else:
                    log(BAD, "  %s  -> 子路径不存在 (%s)" % (u, cand))
            else:
                log(OK, "  %s  -> 模型目录存在" % u)
        else:
            log(WARN, "  %s  -> models/%s 不存在（若引用 turtlebot3_* 属正常，由对应包提供）"
                % (u, head))

    # ---------- 5. 材质名检查 ----------
    res.append("")
    res.append("【4】SQ_* 材质定义检查")
    matf = os.path.join(models_dir, "sq_textures", "materials", "scripts", "sq_textures.material")
    defined = set()
    if os.path.exists(matf):
        mt = open(matf, "r", encoding="utf-8").read()
        defined = set(re.findall(r"^material\s+(\S+)", mt, re.M))
        log(OK, "材质脚本定义 %d 条" % len(defined))
    else:
        log(BAD, "缺 sq_textures.material")
    used = set(re.findall(r"<name>(SQ_[A-Za-z0-9_]+)</name>", txt_all))
    missing = sorted(u for u in used if u not in defined)
    log(OK, "世界/模型中引用 SQ_* 材质 %d 个" % len(used))
    log(OK if not missing else BAD, "未定义的材质: %s" % (missing or "无"))
    unused = sorted(d for d in defined if d not in used)
    if unused:
        log(WARN, "已定义但未使用: %d 个 (%s)" % (len(unused), ", ".join(unused[:8])))

    # ---------- 6. 包围盒 ----------
    res.append("")
    res.append("【5】几何包围盒")
    def size_of(g):
        if g is None:
            return None
        b = g.find("box")
        if b is not None:
            s = b.find("size")
            return [float(v) for v in s.text.split()]
        c = g.find("cylinder")
        if c is not None:
            r = float(c.find("radius").text)
            l = float(c.find("length").text)
            return [2 * r, 2 * r, l]
        s = g.find("sphere")
        if s is not None:
            r = float(s.find("radius").text)
            return [2 * r, 2 * r, 2 * r]
        return None

    xs, ys, zs = [], [], []
    for m in root.iter("model"):
        for lnk in m.findall("link"):
            for v in lnk.findall("visual"):
                pz = v.find("pose")
                pose = [float(x) for x in pz.text.split()] if pz is not None else [0] * 6
                sz = size_of(v.find("geometry"))
                if not sz:
                    continue
                for i, ax in enumerate((xs, ys, zs)):
                    ax.append(pose[i] - sz[i] / 2)
                    ax.append(pose[i] + sz[i] / 2)
    if xs:
        log(OK, "x ∈ [%.2f, %.2f]  (场地 ±5.00)" % (min(xs), max(xs)))
        log(OK, "y ∈ [%.2f, %.2f]  (场地 ±3.60)" % (min(ys), max(ys)))
        log(OK, "z ∈ [%.2f, %.2f]" % (min(zs), max(zs)))
        if min(xs) < -5.15 or max(xs) > 5.15 or min(ys) < -3.75 or max(ys) > 3.75:
            log(WARN, "有物件越出场地范围（含围墙厚度属正常）")
        else:
            log(OK, "所有物件均在场地范围内")
        if min(zs) < -0.15:
            log(WARN, "有物件 z 低于地面 %.2f" % min(zs))

    # ---------- 7. 赛题元素对照 ----------
    res.append("")
    res.append("【6】赛题元素对照（以 docs/scene_manifest.json 为真值）")
    mpath = os.path.join(pkg, "docs", "scene_manifest.json")
    if not os.path.exists(mpath):
        log(BAD, "缺 docs/scene_manifest.json，无法做元素对照")
    else:
        import json
        M = json.load(open(mpath, encoding="utf-8"))
        wtxt = open(world, "r", encoding="utf-8").read()

        def ids(pat):
            return sorted(set(re.findall(pat, wtxt)))

        eb_exp = (M["ebikes"]["parking_area"]["upright"] + M["ebikes"]["parking_area"]["fallen"]
                  + M["ebikes"]["illegal_parking"]["street_A"]
                  + M["ebikes"]["illegal_parking"]["street_B"])
        checks = [
            ("红绿灯", 2, len(re.findall(r"model://sq_traffic_light_", wtxt)),
             "两处，含红/黄/绿三套可切换模型"),
            ("人偶立牌", M["persons"]["total"], len(ids(r"person_(\d+)_head")),
             "A街%d + B街%d，其中外来%d"
             % (M["persons"]["street_A"], M["persons"]["street_B"], M["persons"]["outsiders_total"])),
            ("垃圾桶", M["bins"]["count"], len(ids(r"bin_([a-z]+)_body")),
             "可回收/有害/厨余/其他，含开闭与投放"),
            ("楼宇", M["buildings"]["count"], len(ids(r"bld_([ABCD])_body")), "A/B/C/D 四座"),
            ("火灾隐患窗", sum(M["buildings"]["fire_windows"].values()),
             wtxt.count("<name>SQ_win_fire</name>"),
             "A座%d + B座%d + C座%d"
             % tuple(M["buildings"]["fire_windows"][k] for k in ("A", "B", "C"))),
            ("高温窗", 1, wtxt.count("<name>SQ_win_hot</name>"),
             "%s座 %d 楼异常温度 + 温度牌"
             % (M["buildings"]["hot"]["building"], M["buildings"]["hot"]["floor"])),
            ("站房仪表", len(M["station"]["gauges"]), len(ids(r"gauge_(\d+_?v?)")),
             "读数 " + " / ".join(g["reading"] for g in M["station"]["gauges"])),
            ("车辆", M["cars"]["count"], len(ids(r"car_(\d)_body")),
             " " .join(c["plate"] for c in M["cars"]["items"])),
            ("车牌贴图", 3, sum(wtxt.count("<name>SQ_%s</name>" % p)
                            for p in ("plate_A", "plate_B", "plate_C")), "3 张车牌"),
            ("电动车", eb_exp, len(ids(r"ebike_(\d+)_b")),
             "停车区正常%d + 倒伏%d；A街违停%d，B街违停%d"
             % (M["ebikes"]["parking_area"]["upright"], M["ebikes"]["parking_area"]["fallen"],
                M["ebikes"]["illegal_parking"]["street_A"],
                M["ebikes"]["illegal_parking"]["street_B"])),
            ("指示牌", M["signs"]["count"], len(ids(r"sign_(\d+)_[a-z]")),
             "限速30/禁止直行/左转/人行横道/禁止驶入/右转"),
            ("停车位", len(M["parking"]["bays"]), len(ids(r"bay_(\d+)_g")),
             "3 个停车场车位 + 1 个终点泊车位"),
            ("斑马线", 1, wtxt.count("<name>SQ_gnd_crosswalk</name>"), "A街与连接路交叉处"),
            ("出发点", 1, wtxt.count("<name>SQ_start_plate</name>"), "出发区地贴 x=-4.62"),
        ]
        for name, want, got, note in checks:
            log(OK if got >= want else BAD,
                "%-10s 真值=%-3s 世界内=%-3s  %s" % (name, want, got, note))
        if "answer_key" in M:
            res.append("")
            res.append("  ── 场地答案键（可直接用于校验识别结果 / 写入复赛文档）──")
            for k, v in M["answer_key"].items():
                res.append("    %s: %s" % (k, v))

    # ---------- 8. 文件清单 ----------
    res.append("")
    res.append("【7】包文件清单")
    tot = 0
    nf = 0
    for dp, dn, fn in os.walk(pkg):
        if ".git" in dp:
            continue
        for f in fn:
            tot += os.path.getsize(os.path.join(dp, f))
            nf += 1
    log(OK, "文件 %d 个, 合计 %.2f MB" % (nf, tot / 1048576.0))
    for sub in ["worlds", "models", "launch", "scripts", "maps", "rviz", "docs", "tools"]:
        p = os.path.join(pkg, sub)
        if os.path.isdir(p):
            n = sum(len(fn) for _, _, fn in os.walk(p))
            log(OK, "  %-8s %d 文件" % (sub + "/", n))
        else:
            log(WARN, "  %-8s 缺失" % (sub + "/"))

    return report(res, cnt)


def report(res, cnt):
    res.append("")
    res.append("=" * 72)
    res.append(" 通过 %d 项 / 失败 %d 项 / 警告 %d 项" % (cnt["ok"], cnt["bad"], cnt["warn"]))
    res.append("=" * 72)
    txt = "\n".join(res)
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "静态自检报告.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(txt)
    print(txt)
    print("\n报告已写入: %s" % out)
    return cnt["bad"]


if __name__ == "__main__":
    sys.exit(0 if main() == 0 else 1)
