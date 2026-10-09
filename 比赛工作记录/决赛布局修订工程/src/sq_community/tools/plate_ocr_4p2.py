#!/usr/bin/env python3
"""Camera-only OCR for the three surveyed car viewpoints (optional Python 3 tool).

Usage: python3 tools/plate_ocr_4p2.py 25_CAR_1.jpg 27_CAR_2.jpg 28_CAR_3.jpg
Requires opencv-python and easyocr with Chinese and English model weights.
It reads image pixels only; it never consults the scene manifest or answer key.
The center ROI is calibrated for 1280x720 frames from the planned car goals.
"""
import argparse
import json
import re
from pathlib import Path

import cv2
import easyocr
import numpy as np


def read_frame(path):
    data = np.fromfile(path, dtype=np.uint8)
    frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if frame is None or frame.shape[:2] != (720, 1280):
        raise ValueError('expected 1280x720 camera image: ' + path)
    return frame


def box_in_frame(box, scale=3, offset=(500, 350)):
    x = [float(point[0]) for point in box]
    y = [float(point[1]) for point in box]
    return (int(offset[0] + min(x)/scale), int(offset[1] + min(y)/scale),
            int(offset[0] + max(x)/scale), int(offset[1] + max(y)/scale))


def classify_plate_color(frame, bounds):
    x0, y0, x1, y1 = bounds
    patch = frame[max(0,y0-7):min(720,y1+7), max(0,x0-7):min(1280,x1+7)]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    ranges = {
        'blue': ((90, 40, 30), (135, 255, 255)),
        'yellow': ((15, 40, 30), (40, 255, 255)),
        'green': ((35, 25, 30), (85, 255, 255)),
    }
    counts = {name: int(cv2.countNonZero(cv2.inRange(hsv, low, high)))
              for name, (low, high) in ranges.items()}
    style = max(counts, key=counts.get)
    return style, counts


def read_green_first_letter(reader, frame, suffix_box, raw_suffix):
    x0, y0, x1, y1 = suffix_box
    char_width = float(x1-x0)/len(raw_suffix)
    crop = frame[max(0,y0-15):min(720,y1+15),
                 max(0,int(x0-9)):min(1280,int(x0+1.8*char_width))]
    crop = cv2.resize(crop, None, fx=8, fy=8,
                      interpolation=cv2.INTER_CUBIC)
    readings = reader.readtext(crop, detail=1, allowlist='DF')
    choices = [(text, float(confidence)) for _, text, confidence in readings
               if text in ('D', 'F')]
    return max(choices, key=lambda pair: pair[1]) if choices else ('', 0.0)


def recognize(reader, path):
    frame = read_frame(path)
    region = frame[350:550,500:790]
    enlarged = cv2.resize(region, None, fx=3, fy=3,
                          interpolation=cv2.INTER_CUBIC)
    found = reader.readtext(enlarged, detail=1, paragraph=False)
    pieces = sorted(((box_in_frame(box), text.replace(' ', '').upper(),
                      float(confidence)) for box, text, confidence in found),
                    key=lambda item: item[0][0])
    province = next(((box, text, confidence) for box, text, confidence in pieces
                     if re.match(r'^[\u4e00-\u9fff][A-Z]$', text)), None)
    suffix = next(((box, text, confidence) for box, text, confidence in pieces
                   if re.match(r'^[A-Z0-9]{5,6}$', text)), None)
    if province is None or suffix is None:
        return {'image':path, 'plate':None, 'reason':'prefix or serial not read',
                'raw_tokens':[text for _,text,_ in pieces]}
    plate_bounds = (min(province[0][0],suffix[0][0]),
                    min(province[0][1],suffix[0][1]),
                    max(province[0][2],suffix[0][2]),
                    max(province[0][3],suffix[0][3]))
    style, color_counts = classify_plate_color(frame, plate_bounds)
    serial = suffix[1]
    correction = None
    if style == 'green' and len(serial) == 6 and serial[0] not in 'DF':
        letter, confidence = read_green_first_letter(reader, frame, suffix[0], serial)
        if confidence >= .8:
            serial = letter + serial[1:]
            correction = {'first_character':letter, 'confidence':round(confidence,3)}
    valid = len(serial) == (6 if style == 'green' else 5)
    if style == 'green':
        valid = valid and serial[0] in 'DF'
    plate = province[1] + '\u00b7' + serial if valid else None
    return {'image':path, 'plate':plate, 'style':style,
            'raw_tokens':[text for _,text,_ in pieces],
            'confidence':round(min(province[2],suffix[2]),3),
            'color_counts':color_counts, 'syntax_correction':correction}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('images', nargs='+')
    parser.add_argument('--output', help='optional UTF-8 JSON report path')
    args = parser.parse_args()
    reader = easyocr.Reader(['ch_sim','en'], gpu=False, verbose=False)
    result = [recognize(reader, path) for path in args.images]
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False,
                                              indent=2), encoding='utf8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
