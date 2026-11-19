#!/usr/bin/env python3
"""Smoke test of the crime pipeline on made-up data (no 11labs, no picture search, no generator, no network):
pictures → prep.py → build.py → fonts.py (when FONTSOURCE is set) → checks, and with --still the Remotion preview
(preview.py) and four frames of the CrimeV composition (the black opening scene with its subtitle, a ring drawn on an
AI illustration, a paper card on the desk). Uses the channel's
language (prompts/channel.json). Run from the repo root: python3 tests/crime_smoke.py [--still]"""
import json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'crime'))
import ff, layout
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
ja = LANG == 'ja'
json.dump({'images': {'street': {'src': '1/1-1.jpg'}, 'room': {'src': '1/2-1.jpg'},
                      'paper': {'src': '1/1-2.jpg', 'look': 'clean', 'blur': [[0.1, 0.1, 0.3, 0.3]]}},
           'scenes': [
               # a scene edit: the catalogue (scripts/crime/edits.py) gives the black ground and the places of the photo and the
               # tags; what Claude writes himself (here the photo's size) wins
               {'at': 1, 'edit': 'hook', 'why': 'câu đầu là điều lạ của vụ án', 'items': [
                   {'photo': 'street', 'w': 620, 'h': 820},
                   {'tag': '1976', 'at': 1.5},
                   {'tag': ('ミシェル' if ja else 'Michel'), 'at': ('2:名前' if ja else '2:Name'), 'color': 'red'}]},
               {'at': 2.6, 'items': [
                   {'header': title, 'kicker': ('ファイル 1976' if ja else 'AKTE 1976'), 'y': 260},
                   {'card': {'head': '1976', 'rows': [{'text': 'Anneliese', 'right': '23'}, {'text': 'Klingenberg', 'strike': 2.9}]}, 'y': 980, 'h': 900}]},
               {'at': 3, 'items': [
                   {'photo': 'room', 'w': 640, 'h': 760, 'y': 620, 'still': True, 'marks': [{'at': 3.4, 'box': [0.3, 0.2, 0.7, 0.4]}]},
                   {'big': '67', 'text': 'x', 'y': 1180}, {'stamp': 'X', 'at': 3.5},
                   {'line': [[200, 1300], [880, 1350]], 'at': 3.6}]},
               {'at': 4, 'items': [
                   {'photo': ['paper', {'img': 'street', 'move': 'pan-left'}], 'zoom': {'to': [0.5, 0.5, 0.9, 0.9]}, 'credit': 'B / Public domain', 'y': 600},
                   {'text': ['?', {'text': '!', 'color': 'red'}], 'y': 1200}]}]},
          open(os.path.join(job, 'picks.json'), 'w', encoding='utf-8'), ensure_ascii=False)

S = os.path.join(ROOT, 'scripts', 'crime')
run(sys.executable, os.path.join(S, 'prep.py'), os.path.join(job, 'picks.json'), imgsrc, os.path.join(pub, 'crime', N, 'img'))
run(sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, out)
plan_p = os.path.join(out, 'plan.json')
if os.environ.get('FONTSOURCE'):
    run(sys.executable, os.path.join(S, 'fonts.py'), plan_p, os.environ['FONTSOURCE'], pub)

plan = json.load(open(plan_p, encoding='utf-8'))
speech = sum(r['duration'] for r in rows)
assert speech + 1 < plan['duration'] < speech + 4, plan['duration']
sc = plan['scenes']
assert len(sc) == 4 and plan['lang'] == LANG and plan['title'] == title
assert sc[0]['s'] == 0 and sc[-1]['e'] == plan['duration'] and all(a['e'] == b['s'] for a, b in zip(sc, sc[1:]))   # no gaps
ph = [i for x in sc for i in x['items'] if i['k'] == 'photo']
assert [p['ai'] for p in ph] == [False, True, False]                                          # AI flag from the index
assert ph[0]['credit'] == 'A / CC BY-SA 4.0' and ph[1]['credit'] == ''                        # automatic credits
v = ph[0]['view']; assert abs((v[2] - v[0]) * ph[0]['iw'] / ((v[3] - v[1]) * ph[0]['ih']) - 620 / 820) < 0.01   # view fitted to the box
assert ph[2]['h'] == round(ph[2]['w'] / (2000 / 1300)) and ph[2]['zoom'] and ph[2]['drift'] == 0   # whole picture + zoom
assert ph[0]['drift'] > 0 and ph[1]['drift'] == 0
sl = ph[2]['slides']   # a list of pictures in one frame: shown in turn, the scene shared evenly, each with its move
assert [os.path.basename(x['src']) for x in sl] == ['paper.jpg', 'street.jpg'] and sl[1]['move'] == 'pan-left' and sl[0]['move'] == 'hold'
assert sl[0]['s'] == ph[2]['s'] and sl[0]['e'] == sl[1]['s'] and sl[1]['e'] == sc[3]['e'] and abs((sl[1]['s'] - sl[0]['s']) - (sl[1]['e'] - sl[1]['s'])) < 0.01
assert all(len(x['slides']) == 1 and x['slides'][0]['move'] in ('push-in', 'pan-right', 'pull-back', 'pan-left', 'rise', 'fall', 'hold') for x in ph[:2])
v3 = plan['voice'][2]['s']; assert abs(ph[1]['marks'][0]['s'] - (v3 + 0.4 * rows[2]['duration'])) < 0.01
tag2 = sc[0]['items'][2]; assert tag2['k'] == 'tag' and tag2['color'] == 'red'
assert plan['voice'][1]['s'] + 0.1 < tag2['s'] < plan['voice'][1]['s'] + 1.6, tag2['s']      # "2:<words>": when the words are spoken
card = sc[1]['items'][1]; assert card['k'] == 'card' and len(card['rows']) == 2 and card['rows'][1]['strike'] >= card['rows'][1]['s']
assert all(i['s'] >= x['s'] and i['s'] < x['e'] for x in sc for i in x['items'])              # items inside their scene
subs = plan['subs']
assert all(a['s'] < a['e'] <= b['s'] + 1e-6 for a, b in zip(subs, subs[1:])), 'subtitles overlap'
assert len(subs) >= len(lines) and all(len(c['text']) <= (19 if ja else 40) for c in subs), [c['text'] for c in subs]
assert ''.join(c['text'] for c in subs).replace(' ', '') == ''.join(lines).replace(' ', '')
bad = json.load(open(os.path.join(job, 'picks.json'), encoding='utf-8'))
bad['scenes'][0]['items'][1]['at'] = 4                                                       # after its scene: refused
json.dump(bad, open(os.path.join(tmp, 'bad.json'), 'w'))
shutil.copy(os.path.join(job, 'picks.json'), os.path.join(tmp, 'good.json')); shutil.copy(os.path.join(tmp, 'bad.json'), os.path.join(job, 'picks.json'))
r = subprocess.run([sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, os.path.join(tmp, 'out2')], capture_output=True, text=True, cwd=ROOT)
assert r.returncode and 'sau khi cảnh kết thúc' in r.stderr, r.stderr
bad = json.load(open(os.path.join(tmp, 'good.json'), encoding='utf-8')); bad['scenes'][2]['edit'] = 'no-such-edit'   # unknown scene edit
json.dump(bad, open(os.path.join(job, 'picks.json'), 'w'))
r = subprocess.run([sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, os.path.join(tmp, 'out2')], capture_output=True, text=True, cwd=ROOT)
assert r.returncode and 'cảnh 3' in r.stderr and 'hook' in r.stderr and 'ending' in r.stderr, r.stderr
shutil.copy(os.path.join(tmp, 'good.json'), os.path.join(job, 'picks.json'))
# scene edits: the name is in the plan, the template's places and ground are used, a scene without "edit" has no key,
# and edits.md lists every scene with its edit and why for the owner
assert sc[0]['edit'] == 'hook' and sc[0]['bg'] == 'black' and all('edit' not in x for x in sc[1:])
assert (ph[0]['x'], ph[0]['y'], ph[0]['rot']) == (540, 640, -1) and (sc[0]['items'][1]['x'], sc[0]['items'][1]['y']) == (250, 1150) and tag2['x'] == 540
md = open(os.path.join(out, 'edits.md'), encoding='utf-8').read()
assert '`hook`' in md and 'câu đầu là điều lạ của vụ án' in md and '| 4 |' in md, md
assert md.rstrip().endswith('Ảnh: 3 ảnh khác nhau cho 4 cảnh.'), md[-200:]      # the picture count under the list (three files, four scenes)
srt = open(os.path.join(out, 'subtitles.srt'), encoding='utf-8').read(); assert srt.count('-->') == len(lines)
cred = open(os.path.join(out, 'credits.txt'), encoding='utf-8').read()
assert 'Street.jpg' in cred and 'AI' in cred and 'a small bedroom' in cred
src = json.load(open(os.path.join(out, 'sources.json'), encoding='utf-8'))
assert len(src['scenes']) == 4 and src['scenes'][2]['photos'][0]['ai'] and src['scenes'][0]['photos'][0]['page']
assert os.path.getsize(os.path.join(pub, 'crime', N, 'bed.wav')) > 100000
# a recording found with music: replaces the made bed, loops, and is credited
os.makedirs(os.path.join(imgsrc, 'm'))
ff.run('-f', 'lavfi', '-i', 'sine=frequency=220:duration=5', '-c:a', 'libvorbis', os.path.join(imgsrc, 'm', '1-1.ogg'))
json.dump([{'k': 1, 'query': 'music:test', 'results': [{'file': '1-1.ogg', 'title': 'Test piece.ogg', 'artist': 'Someone', 'license': 'Public domain',
           'page': 'https://commons.wikimedia.org/wiki/File:Test_piece.ogg', 'audio': True, 'seconds': 5.0}]}], open(os.path.join(imgsrc, 'm', 'index.json'), 'w'))
pk = json.load(open(os.path.join(job, 'picks.json'), encoding='utf-8')); pk['music'] = {'pick': 'm/1-1.ogg', 'volume': 1}
json.dump(pk, open(os.path.join(job, 'picks.json'), 'w', encoding='utf-8'), ensure_ascii=False)
run(sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, os.path.join(tmp, 'outm'))
pm_ = json.load(open(os.path.join(tmp, 'outm', 'plan.json'), encoding='utf-8'))
assert pm_['music'].endswith('music.mp3') and pm_['musicLoop'] and os.path.getsize(os.path.join(pub, pm_['music'])) > 10000, pm_['music']
assert 'Test piece.ogg' in open(os.path.join(tmp, 'outm', 'credits.txt'), encoding='utf-8').read()
assert pm_['loudness'] == -15, pm_['loudness']
# "voice": {"volume": 1.4} (owner 19/11: the voice 40% louder): the music 1.4× under the voice, the final target +2.9 dB
pk['voice'] = {'volume': 1.4}; json.dump(pk, open(os.path.join(job, 'picks.json'), 'w', encoding='utf-8'), ensure_ascii=False)
run(sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, os.path.join(tmp, 'outv'))
pv_ = json.load(open(os.path.join(tmp, 'outv', 'plan.json'), encoding='utf-8'))
assert pv_['loudness'] == -12.1 and abs(pv_['musicVolume'] * 1.4 - pm_['musicVolume']) < 1e-9, (pv_['loudness'], pv_['musicVolume'])
del pk['music'], pk['voice']; json.dump(pk, open(os.path.join(job, 'picks.json'), 'w', encoding='utf-8'), ensure_ascii=False)
if os.environ.get('FONTSOURCE'):
    plan = json.load(open(plan_p, encoding='utf-8')); assert len(plan['fonts']) >= 2 and all(os.path.exists(os.path.join(pub, f['file'])) for f in plan['fonts'])

if '--still' in sys.argv:
    rend = os.path.join(tmp, 'renders'); os.makedirs(rend)
    shutil.copytree(voice, os.path.join(rend, 'voice')); shutil.copytree(imgsrc, os.path.join(rend, 'img'))
    run(sys.executable, os.path.join(S, 'preview.py'), job, rend, os.path.join(out, 'preview.jpg'))
    assert Image.open(os.path.join(out, 'preview.jpg')).size[0] > 1000 and '`hook`' in open(os.path.join(out, 'preview.jpg.edits.md'), encoding='utf-8').read()
    t_ring = ph[1]['marks'][0]['s']
    ts = [f'{sc[0]["s"] + 0.6:.2f}', f'{t_ring - 0.3:.2f}', f'{t_ring + 0.6:.2f}', f'{sc[1]["e"] - 0.2:.2f}']
    run('node', os.path.join(S, 'stills.mjs'), plan_p, pub, os.path.join(out, 'still'), *ts)
    im = lambda t: np.asarray(Image.open(os.path.join(out, f'still_{t}.jpg')).convert('RGB')).astype(int)
    c, a, b, d = (im(t) for t in ts)
    assert a.shape[:2] == (960, 540), a.shape
    assert c[5:40, 5:60].mean() < 30, 'black opening scene expected'
    assert 25 < d[400:560, 10:60].mean() < 110, 'wooden desk expected'
    x, y, w, h = ph[1]['x'], ph[1]['y'], ph[1]['w'], ph[1]['h']
    y0, y1, x0, x1 = int((y - h / 2) / 2) + 8, int((y + h / 2) / 2) - 8, int((x - w / 2) / 2) + 8, int((x + w / 2) / 2) - 8
    assert a[y0:y1, x0:x1].std() > 15, 'picture missing'
    assert (np.abs(a[y0:y1, x0:x1] - b[y0:y1, x0:x1]).sum(axis=2) > 80).sum() > 300, 'ring was not drawn'
    sy = int(layout.SUB_Y / 2)
    white = (c[sy - 14:sy + 14, :] > 225).all(axis=2)
    assert white.mean() > 0.05, 'no subtitle box'
    cx, cy = int(card['x'] / 2), int(card['y'] / 2)
    assert d[cy - 100:cy + 100, cx - 150:cx + 150].mean() > 150, 'no paper card'
print(f'crime smoke test OK ({LANG}):', round(plan['duration'], 1), 's,', len(subs), 'subtitles,', tmp)
