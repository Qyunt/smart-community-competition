#!/usr/bin/env python3
"""Generate deterministic competition plates with category-correct serial formats.

The physical standee remains the 95 x 30 mm size set by the training PDF.
Artwork is for a miniature recognition target, not a registrable real plate.
"""

import argparse
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


PKG = Path(__file__).resolve().parents[1]
TEXTURES = PKG / "models/sq_competition_assets/materials/textures"
PLATES = (
    ("blue", "苏A·31682", "ordinary_small_passenger"),
    ("yellow", "苏A·57246", "large_passenger_vehicle"),
    ("green", "苏A·D68125", "small_pure_electric"),
    ("white", "苏A·7624警", "police_vehicle_optional"),
)
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
)


def font_path():
    for path in FONT_CANDIDATES:
        if path.exists():
            return str(path)
    raise RuntimeError("A Chinese TrueType/OpenType font is required")


def validate(kind, number):
    if kind in ("blue", "yellow"):
        return re.fullmatch(r"苏A·[0-9]{5}", number) is not None
    if kind == "green":
        return re.fullmatch(r"苏A·D[0-9]{5}", number) is not None
    return re.fullmatch(r"苏A·[0-9]{4}警", number) is not None


def palette(kind, size):
    w, h = size
    if kind == "blue":
        return Image.new("RGB", size, (9, 50, 141)), (248, 248, 246), (246, 246, 244)
    if kind == "yellow":
        return Image.new("RGB", size, (250, 199, 33)), (15, 19, 20), (15, 19, 20)
    if kind == "white":
        return Image.new("RGB", size, (245, 245, 242)), (15, 19, 20), (15, 19, 20)
    im = Image.new("RGB", size)
    pixels = im.load()
    for y in range(h):
        t = y / float(h - 1)
        color = (int(241 - 112 * t), int(252 - 35 * t), int(241 - 103 * t))
        for x in range(w):
            pixels[x, y] = color
    return im, (15, 34, 26), (5, 112, 67)


def fitted_font(draw, value, path, max_width, initial=205):
    for size in range(initial, 98, -2):
        font = ImageFont.truetype(path, size)
        box = draw.textbbox((0, 0), value, font=font)
        if box[2] - box[0] <= max_width:
            return font
    raise RuntimeError("plate text does not fit")


def draw_plate(kind, number, path):
    assert validate(kind, number), (kind, number)
    im, ink, border = palette(kind, (960, 300))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((10, 10, 949, 289), radius=16, outline=border, width=10)
    draw.rounded_rectangle((25, 25, 934, 274), radius=7, outline=border, width=2)
    if kind == "green":
        # Simplified small-new-energy circular E/plug mark.
        draw.ellipse((40, 105, 120, 185), outline=(6, 111, 67), width=11)
        draw.line((64, 119, 64, 171), fill=(6, 111, 67), width=7)
        for y in (120, 145, 170):
            draw.line((64, y, 92 if y != 145 else 84, y), fill=(6, 111, 67), width=7)
        left, width = 130, 785
    elif kind == "white":
        left, width = 40, 710
    else:
        left, width = 50, 850
    main = number[:-1] if kind == "white" else number
    face = fitted_font(draw, main, font_path(), width)
    box = draw.textbbox((0, 0), main, font=face)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    draw.text((left + (width - text_width) / 2, (300 - text_height) / 2 - box[1]),
              main, font=face, fill=ink)
    if kind == "white":
        police = ImageFont.truetype(font_path(), 160)
        box = draw.textbbox((0, 0), "警", font=police)
        draw.text((770, (300 - (box[3] - box[1])) / 2 - box[1]),
                  "警", font=police, fill=(189, 28, 39))
    if kind == "blue":
        for x in (220, 680):
            for y in (29, 271):
                draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(243, 243, 243))
    im.save(path)
    return im


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path)
    args = parser.parse_args()
    images = []
    metadata = []
    for kind, number, vehicle in PLATES:
        images.append(draw_plate(kind, number, TEXTURES / ("plate_" + kind + ".png")))
        metadata.append({"kind": kind, "number": number,
                         "texture": "plate_" + kind + ".png", "vehicle_category": vehicle})
    manifest_path = PKG / "models/sq_competition_assets/asset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["plates"] = metadata
    manifest["plate_semantics"] = {
        "blue": "ordinary small passenger vehicle; five-digit serial",
        "yellow": "large passenger vehicle; five-digit serial",
        "green": "small pure-electric vehicle; D followed by five digits",
        "white": "police vehicle; four digits and final red police ideograph; optional asset",
    }
    manifest["large_vehicle_source"] = "AI-generated transparent large-passenger rear with blank plate mount"
    manifest["materials"]["car_rear_large_cutout"] = "SQ4_CarRearLarge"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    material_path = PKG / "models/sq_competition_assets/materials/scripts/sq_competition_assets.material"
    material_source = material_path.read_text(encoding="utf-8")
    if "material SQ4_CarRearLarge" not in material_source:
        material_source += ("\nmaterial SQ4_CarRearLarge\n{\n technique\n {\n  pass\n  {\n"
                            "   lighting off\n   scene_blend alpha_blend\n   depth_write off\n"
                            "   texture_unit\n   {\n    texture car_rear_large_cutout.png\n   }\n"
                            "  }\n }\n}\n")
        material_path.write_text(material_source, encoding="utf-8")
    if args.preview:
        sheet = Image.new("RGB", (2040, 780), (236, 241, 245))
        for index, im in enumerate(images):
            x = 25 + (index % 2) * 1020
            y = 15 + (index // 2) * 390
            sheet.paste(im, (x, y + 55))
            draw = ImageDraw.Draw(sheet)
            label = ("蓝牌", "黄牌", "绿牌", "白牌")[index]
            draw.text((x, y), label + "  " + metadata[index]["number"],
                      font=ImageFont.truetype(font_path(), 35), fill=(27, 40, 55))
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(args.preview)
    print("generated", ", ".join(m["number"] for m in metadata))


if __name__ == "__main__":
    main()
