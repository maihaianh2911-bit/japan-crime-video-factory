#!/usr/bin/env python3
"""Preview every scene before rendering, rendered by Remotion exactly as the video (same plan, same code): for each
scene the frame at its end (everything laid down) and, for a scene over 7 s, one in the middle, with the time and the
subtitle. Catches wrong pictures, cut subjects, items off the desk or over each other, a tag hiding a face, before a
20-minute render.

Usage: preview.py <crime/N dir with script.json + picks.json> <renders crime/N dir with voice/ and img/> <out.jpg>
Needs node_modules (npm ci) and the fonts (scripts/crime/get_fonts.sh "$FONTSOURCE"; default /tmp/fontsource).
Also writes <out>.plan.json (times of every scene, item and subtitle) next to the sheet."""
import json, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))

job, rend, out = sys.argv[1:4]
tmp = tempfile.mkdtemp(prefix='crime-preview-')
pub = os.path.join(tmp, 'public'); base = os.path.join(pub, 'crime', 'P')
os.makedirs(base); shutil.copytree(os.path.join(rend, 'voice'), os.path.join(base, 'voice'))
imgsrc = os.path.join(tmp, 'img'); shutil.copytree(os.path.join(rend, 'img'), imgsrc)
if os.path.isdir(os.path.join(job, 'own')): shutil.copytree(os.path.join(job, 'own'), os.path.join(imgsrc, 'own'), dirs_exist_ok=True)
def run(*a):
    if subprocess.run([sys.executable, *a], stdout=subprocess.DEVNULL).returncode: sys.exit(1)   # the step printed why
run(os.path.join(HERE, 'prep.py'), os.path.join(job, 'picks.json'), imgsrc, os.path.join(base, 'img'))
run(os.path.join(HERE, 'build.py'), job, pub, 'P', imgsrc, os.path.join(tmp, 'out'))
plan_p = os.path.join(tmp, 'out', 'plan.json')
run(os.path.join(HERE, 'fonts.py'), plan_p, os.environ.get('FONTSOURCE', '/tmp/fontsource'), pub)
plan = json.load(open(plan_p, encoding='utf-8'))

shots = []
for sc in plan['scenes']:
    ts = [sc['e'] - 0.15]
    if sc['e'] - sc['s'] > 7: ts.insert(0, (sc['s'] + sc['e']) / 2)
    shots += [(sc['scene'], round(t, 2)) for t in ts]
subprocess.run(['node', os.path.join(HERE, 'stills.mjs'), plan_p, pub, os.path.join(tmp, 'f'), *[f'{t:.2f}' for _, t in shots]],
               check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
TW, TH = 270, 480
tiles = []
for n, t in shots:
    f = Image.open(os.path.join(tmp, f'f_{t:.2f}.jpg')).convert('RGB').resize((TW, TH), Image.LANCZOS)
    tile = Image.new('RGB', (TW, TH + 24), (10, 10, 12)); tile.paste(f, (0, 24))
    ImageDraw.Draw(tile).text((4, 6), f"#{n}  {t:.1f}s", fill=(255, 210, 90))
    tiles.append(tile)
cols = 6; rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * (TW + 8), rows * (TH + 32)), (0, 0, 0))
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * (TW + 8), (i // cols) * (TH + 32)))
sheet.save(out, quality=85)
json.dump({'duration': plan['duration'],
           'scenes': [{'scene': sc['scene'], 's': sc['s'], 'e': sc['e'],
                       'items': [[i['k'], i['s'], i.get('text') or i.get('title') or i.get('num') or os.path.basename(i.get('src', ''))] for i in sc['items']]}
                      for sc in plan['scenes']],
           'subs': [[c['s'], c['text']] for c in plan['subs']]},
          open(out + '.plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(out, len(tiles), 'frames', f"{plan['duration']:.1f}s")
shutil.rmtree(tmp, ignore_errors=True)
