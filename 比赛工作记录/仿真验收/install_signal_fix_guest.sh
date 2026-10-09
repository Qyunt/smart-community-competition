#!/usr/bin/env bash
set -e
task_pkg="$HOME/sq_community_ws_20261008/src/sq_community"
task_backup="$HOME/sq_community_ws_20261008/acceptance/signal_fix_20261008_backup"
mkdir -p "$task_backup"
if [ ! -e "$task_backup/sq_signal_vision_4p2.py" ]; then
  cp -p "$task_pkg/scripts/sq_signal_vision_4p2.py" "$task_backup/"
fi
cp /tmp/sq_signal_vision_fixed.py "$task_pkg/scripts/sq_signal_vision_4p2.py"
chmod u+x "$task_pkg/scripts/sq_signal_vision_4p2.py"
python -m py_compile "$task_pkg/scripts/sq_signal_vision_4p2.py"
python3 - "$task_pkg" "$task_backup" <<'PY'
from pathlib import Path
import sys, shutil, xml.etree.ElementTree as ET
root=Path(sys.argv[1]);backup=Path(sys.argv[2])
for p in (root/'launch').glob('*.launch'):
    text=p.read_text()
    tree=ET.fromstring(text)
    if not any(n.get('type')=='sq_signal_vision_4p2.py' for n in tree.iter('node')):
        continue
    if 'min_brightness_upper' in text:
        continue
    if not (backup/p.name).exists(): shutil.copy2(str(p),str(backup/p.name))
    import re
    pattern=r'(<node\b[^>]*\btype="sq_signal_vision_4p2\.py"[^>]*?)/>'
    text,count=re.subn(pattern,r'\1>\n    <param name="min_brightness_upper" value="90"/>\n  </node>',text)
    if count!=1: raise ValueError('Unexpected signal node format: '+str(p))
    ET.fromstring(text)
    p.write_text(text)
    print('CALIBRATED_LAUNCH='+p.name)
PY
