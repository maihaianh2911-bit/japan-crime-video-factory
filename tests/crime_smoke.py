#!/usr/bin/env python3
"""Smoke test of the crime pipeline on made-up data (no 11labs, no picture search, no generator, no network):
pictures → prep.py → build.py → fonts.py (when FONTSOURCE is set) → preview.py → checks, and with --still two
Remotion frames of the CrimeV composition (a caption chunk, then a ring on an AI illustration). Uses the channel's
language (prompts/channel.json). Run from the repo root: python3 tests/crime_smoke.py [--still]"""
import json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'crime'))
import ff, layout, captions
from channel import LANG

N = '0'
tmp = tempfile.mkdtemp(prefix='crime-smoke-')
job, pub, imgsrc, out = (os.path.join(tmp, d) for d in ('job', 'public', 'imgsrc', 'out'))
voice = os.path.join(pub, 'crime', N, 'voice')
for d in (job, os.path.join(imgsrc, '1'), voice, out): os.makedirs(d)
run = lambda *a: subprocess.run(a, check=True, cwd=ROOT)

# pictures: a landscape street photo, a portrait AI illustration, a landscape newspaper page
rng = np.random.RandomState(1)
for name, (w, h) in {'1-1.jpg': (1600, 1200), '2-1.jpg': (1024, 1536), '1-2.jpg': (2000, 1300)}.items():
    yy, xx = np.mgrid[0:h, 0:w]
    a = np.stack([150 + 60 * np.sin(xx / 70.0), 110 + 50 * np.cos(yy / 50.0), 80 + 0 * xx], axis=2) + rng.normal(0, 10, (h, w, 3))
    Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(os.path.join(imgsrc, '1', name), quality=90)
json.dump([{'k': 1, 'query': 'test', 'results': [
    {'title': 'Street.jpg', 'source': 'commons', 'page': 'https://commons.wikimedia.org/wiki/File:Street.jpg', 'license': 'CC BY-SA 4.0', 'artist': 'A', 'date': '1976', 'file': '1-1.jpg'},
    {'title': 'Paper.jpg', 'source': 'europeana', 'page': 'https://www.europeana.eu/item/x', 'license': 'Public domain', 'artist': 'B', 'date': '', 'file': '1-2.jpg'}]},
    {'k': 2, 'query': 'gen: a small bedroom', 'ai': True, 'results': [
    {'title': 'a small bedroom', 'source': 'ai/openai', 'page': '', 'license': 'AI-generated', 'artist': 'AI (openai)', 'ai': True, 'file': '2-1.jpg'}]}],
    open(os.path.join(imgsrc, '1', 'index.json'), 'w'))

# voice: silent lines of known length, with word times for line 2
if LANG == 'ja':
    lines = ['1976年、ドイツで23歳の女性が亡くなった。', '彼女の名前は、アンネリーゼ・ミシェル。', '部屋の壁には、十字架が並んでいた。', 'なぜ誰も止めなかったのか？']
    title = 'アンネリーゼ・ミシェル事件'
else:
    lines = ['Im Jahr 1976 starb in Bayern eine 23-jährige Frau.', 'Ihr Name war Anneliese Michel.', 'An den Wänden hingen Kreuze.', 'Warum hat niemand eingegriffen?']
    title = 'Der Fall Anneliese Michel'
durs = [4.2, 2.6, 3.0, 2.4]; rows = []
for i, (t, d) in enumerate(zip(lines, durs), 1):
    f = f'line_{i:02d}.mp3'
    ff.run('-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', str(d), '-c:a', 'libmp3lame', '-q:a', '5', os.path.join(voice, f))
    rows.append({'i': i, 'text': t, 'tts': t, 'voice': 'clone_x', 'file': f, 'duration': round(ff.duration(os.path.join(voice, f)), 3)})
rows[1]['align'] = [[0.0, 0.1], [0.5, 1.6], [1.0, 2.5]]   # the second half of line 2 starts late
json.dump(rows, open(os.path.join(voice, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False)

json.dump({'title': title, 'lines': lines, 'queries': ['test'], 'gen': [{'gen': 'a small bedroom'}]},
          open(os.path.join(job, 'script.json'), 'w', encoding='utf-8'), ensure_ascii=False)
json.dump({'images': {'street': {'src': '1/1-1.jpg'}, 'room': {'src': '1/2-1.jpg'},
                      'paper': {'src': '1/1-2.jpg', 'look': 'clean', 'blur': [[0.1, 0.1, 0.3, 0.3]]}},
           'shots': [
               {'at': 1, 'img': 'street', 'label': 'Klingenberg, 1976'},
               {'at': 2, 'img': 'room', 'label': 'Illustration'},
               {'at': 3, 'img': 'room', 'view': [0.2, 0.1, 0.8, 0.6], 'still': True, 'marks': [{'at': 3.4, 'box': [0.3, 0.2, 0.7, 0.4]}]},
               {'at': 4, 'img': 'paper', 'fit': 'contain', 'zoom': {'to': [0.5, 0.5, 0.9, 0.9]}, 'credit': 'B / Public domain'}]},
          open(os.path.join(job, 'picks.json'), 'w', encoding='utf-8'), ensure_ascii=False)

S = os.path.join(ROOT, 'scripts', 'crime')
run(sys.executable, os.path.join(S, 'prep.py'), os.path.join(job, 'picks.json'), imgsrc, os.path.join(pub, 'crime', N, 'img'))
run(sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, out)
plan_p = os.path.join(out, 'plan.json')
if os.environ.get('FONTSOURCE'):
    run(sys.executable, os.path.join(S, 'fonts.py'), plan_p, os.environ['FONTSOURCE'], pub)
rend = os.path.join(tmp, 'renders'); os.makedirs(rend)
shutil.copytree(voice, os.path.join(rend, 'voice')); shutil.copytree(imgsrc, os.path.join(rend, 'img'))
run(sys.executable, os.path.join(S, 'preview.py'), job, rend, os.path.join(out, 'preview.jpg'))

plan = json.load(open(plan_p, encoding='utf-8'))
speech = sum(r['duration'] for r in rows)
assert speech + 1 < plan['duration'] < speech + 4, plan['duration']
sh = plan['shots']
assert len(sh) == 4 and plan['lang'] == LANG and plan['title'] == title
assert sh[0]['s'] == 0 and sh[-1]['e'] == plan['duration'] and all(a['e'] == b['s'] for a, b in zip(sh, sh[1:]))   # no gaps
assert [x['ai'] for x in sh] == [False, True, True, False]                                    # AI flag from the index
assert sh[0]['credit'] == 'A / CC BY-SA 4.0' and sh[1]['credit'] == ''                        # automatic credits
assert sh[0]['pic']['box'] == [layout.SIDE, layout.PIC_Y, layout.PIC_W, layout.PIC_H]           # the 3:4 photograph
v = sh[0]['pic']['view']; w, h = sh[0]['pic']['w'], sh[0]['pic']['h']
assert abs((v[2] - v[0]) * w / ((v[3] - v[1]) * h) - layout.PIC_W / layout.PIC_H) < 0.01          # view cropped to it
assert sh[3]['pic']['box'][3] < layout.PIC_H and sh[3]['pic']['zoom'] and sh[3]['pic']['drift'] == 0   # contain + zoom
assert sh[0]['pic']['drift'] > 0 and sh[2]['pic']['drift'] == 0
v3 = plan['voice'][2]['s']; assert abs(sh[2]['marks'][0]['s'] - (v3 + 0.4 * rows[2]['duration'])) < 0.01
caps = plan['caps']
assert all(a['s'] < a['e'] <= b['s'] + 1e-6 for a, b in zip(caps, caps[1:])), 'captions overlap'
assert len(caps) >= 8 and all(len(c['text']) <= (12 if LANG == 'ja' else 22) for c in caps), [c['text'] for c in caps]
assert not any(ch in c['text'] for c in caps for ch in '、。,.'), 'punctuation in a caption'
l2 = [c for c in caps if c['line'] == 2]
assert l2[-1]['s'] > plan['voice'][1]['s'] + 1.05, 'word times not used'                      # Whisper times of line 2
joined = ''.join(c['text'] for c in caps).replace(' ', '')
assert joined == re.sub(r'[、。,.\s]', '', ''.join(lines)), joined
srt = open(os.path.join(out, 'subtitles.srt'), encoding='utf-8').read(); assert srt.count('-->') == len(lines)
cred = open(os.path.join(out, 'credits.txt'), encoding='utf-8').read()
assert 'Street.jpg' in cred and 'AI' in cred and 'a small bedroom' in cred
src = json.load(open(os.path.join(out, 'sources.json'), encoding='utf-8'))
assert len(src['shots']) == 4 and src['shots'][2]['marks'] and src['shots'][1]['ai'] and src['shots'][0]['page']
assert os.path.getsize(os.path.join(pub, 'crime', N, 'bed.wav')) > 100000
assert Image.open(os.path.join(out, 'preview.jpg')).size[0] > 1000
if os.environ.get('FONTSOURCE'):
    plan = json.load(open(plan_p, encoding='utf-8')); assert len(plan['fonts']) >= 2 and all(os.path.exists(os.path.join(pub, f['file'])) for f in plan['fonts'])

if '--still' in sys.argv:
    t_cap = caps[1]['s'] + 0.2
    t_ring = sh[2]['marks'][0]['s']
    ts = [f'{t_cap:.2f}', f'{t_ring - 0.3:.2f}', f'{t_ring + 0.6:.2f}']
    run('node', os.path.join(S, 'stills.mjs'), plan_p, pub, os.path.join(out, 'still'), *ts)
    c = np.asarray(Image.open(os.path.join(out, f'still_{ts[0]}.png')).convert('RGB')).astype(int)
    a = np.asarray(Image.open(os.path.join(out, f'still_{ts[1]}.png')).convert('RGB')).astype(int)
    b = np.asarray(Image.open(os.path.join(out, f'still_{ts[2]}.png')).convert('RGB')).astype(int)
    assert a.shape[:2] == (960, 540), a.shape
    assert a[5:20, 5:60].mean() < 30, 'black frame expected'
    bx = sh[2]['pic']['box']; y0, y1, x0, x1 = int(bx[1] / 2) + 6, int((bx[1] + bx[3]) / 2) - 6, int(bx[0] / 2) + 6, int((bx[0] + bx[2]) / 2) - 6
    assert a[y0:y1, x0:x1].std() > 15, 'picture missing'
    assert (np.abs(a[y0:y1, x0:x1] - b[y0:y1, x0:x1]).sum(axis=2) > 80).sum() > 300, 'ring was not drawn'
    cy = int(layout.CAP_Y / 2)
    yellow = (c[cy:cy + 70, :, 0] > 200) & (c[cy:cy + 70, :, 1] > 170) & (c[cy:cy + 70, :, 2] < 90)
    assert yellow.mean() > 0.01, 'no yellow caption'
    ty = int(layout.TITLE_Y / 2)
    assert (c[ty:ty + 40] > 200).all(axis=2).mean() > 0.01, 'no title'
print(f'crime smoke test OK (ja):', round(plan['duration'], 1), 's,', len(caps), 'captions,', tmp)
