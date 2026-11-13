#!/usr/bin/env python3
"""Add the fonts a plan needs. Usage: fonts.py <plan.json> <fontsource_dir> <public_dir>

<fontsource_dir> holds the unpacked npm packages of scripts/crime/get_fonts.sh (Japanese: noto-sans-jp; German:
anton and source-sans-3). Only the unicode-range chunks that contain characters of this video are copied to
<public_dir>/crime/fonts/ and listed in plan["fonts"] (CrimeV registers them with FontFace).
"""
import json, os, re, shutil, sys

plan_path, src, pub = sys.argv[1], sys.argv[2], sys.argv[3]
plan = json.load(open(plan_path, encoding='utf-8'))
FAMILIES = {'ja': [('Noto Sans JP', 'noto-sans-jp')], 'de': [('Anton', 'anton'), ('Source Sans 3', 'source-sans-3')]}[plan.get('lang', 'ja')]
text = json.dumps(plan, ensure_ascii=False)
chars = set(text) | set(text.upper()) | set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÄÖÜäöüß—–„“‚‘«».,:;!?()/・「」（）、。 　')
os.makedirs(f'{pub}/crime/fonts', exist_ok=True); out = []
for fam, pkg in FAMILIES:
    base = os.path.join(src, pkg)
    for blk in re.findall(r'@font-face\s*{(.*?)}', open(f'{base}/index.css').read(), re.S):
        f = re.search(r"url\(\./files/([^)]+\.woff2)\)", blk).group(1)
        ur = re.search(r'unicode-range:\s*([^;]+);', blk).group(1).strip()
        rs = []
        for part in ur.split(','):
            part = part.strip().replace('U+', '')
            a, b = part.split('-') if '-' in part else (part, part); rs.append((int(a, 16), int(b, 16)))
        if any(any(a <= ord(c) <= b for a, b in rs) for c in chars):
            shutil.copy(f'{base}/files/{f}', f'{pub}/crime/fonts/{f}'); out.append({'family': fam, 'file': f'crime/fonts/{f}', 'range': ur})
plan['fonts'] = out
json.dump(plan, open(plan_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'font chunks')
