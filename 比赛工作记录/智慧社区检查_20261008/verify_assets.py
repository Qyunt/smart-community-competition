import hashlib
import json
from pathlib import Path
from PIL import Image

out = Path(__file__).resolve().parent
pkg = Path(r'F:\codex\实践课小车\智慧社区项目\原始工程\src\sq_community')
diffs = []
checked = 0
prefix = '/home/qyunt/sq_community_ws_20261008/src/sq_community/'
for row in (out/'原始记录/source_hashes.txt').read_text(encoding='utf-8').splitlines():
    sha, name = row.split('  ', 1)
    path = pkg/name.removeprefix(prefix)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        diffs.append(name)
    checked += 1

maps = pkg/'maps'
evidence = json.loads((maps/'sq_slam_4p2_evidence.json').read_text())
nav_evidence = json.loads((maps/'sq_slam_road_nav_4p2_evidence.json').read_text())
raw = maps/'sq_slam_4p2_raw.pgm'
crop = maps/'sq_slam_4p2.pgm'
nav = maps/'sq_slam_road_nav_4p2.pgm'
image = Image.open(raw).crop(evidence['crop_box_pixels'])
pixels = Image.open(crop).tobytes()
checks = {
    'raw_sha256_matches_record': hashlib.sha256(raw.read_bytes()).hexdigest() == evidence['raw_sha256'],
    'crop_sha256_matches_record': hashlib.sha256(crop.read_bytes()).hexdigest() == evidence['crop_sha256'],
    'crop_pixels_match_raw_crop': image.tobytes() == pixels,
    'derived_map_sha256_matches_record': hashlib.sha256(nav.read_bytes()).hexdigest() == nav_evidence['derived_sha256'],
    'nav_source_sha256_matches_crop': hashlib.sha256(crop.read_bytes()).hexdigest() == nav_evidence['source_sha256'],
}
result = {'vm_source_files_compared': checked, 'vm_vs_source_differences': diffs,
          'map_evidence_checks': checks, 'crop_unknown_pixels': pixels.count(205),
          'crop_total_pixels': len(pixels)}
(out/'源码与地图证据核验.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
