#!/usr/bin/env python3
"""Plan of a crime video for the CrimeV composition, plus music bed, subtitles and picture credits.

Usage: build.py <job_dir crime/N> <public_dir> <N> <img_src_dir> <out_dir>
Reads <job_dir>/script.json (title, lines), <job_dir>/picks.json (images, shots), <public_dir>/crime/<N>/voice/
lines.json (measured line lengths, Whisper word times) and the prepared pictures in <public_dir>/crime/<N>/img/.
Writes <out_dir>/plan.json, subtitles.srt, credits.txt, sources.json and <public_dir>/crime/<N>/bed.wav.

Timing: every line starts after the previous one plus a pause (0.4 s after a sentence end, 0.22 s otherwise). A
shot starts at its "at" (line number, fractional = part-way through the line; the first shot at the start) and
lasts until the next shot: hard cuts, as the sample (a new picture every ~3–4 s). The captions show 2–3 words at a
time (scripts/crime/captions.py), each when its first word is spoken (Whisper word times; linear without them).
"""
import json, os, re, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import music_gen as mg
import layout as L
import captions as C
from channel import LANG, AI_TAG

job, pub, N, imgsrc, out = sys.argv[1:6]
base = f'crime/{N}'
spec = json.load(open(f'{job}/script.json', encoding='utf-8'))
picks = json.load(open(f'{job}/picks.json', encoding='utf-8'))
lines = json.load(open(f'{pub}/{base}/voice/lines.json', encoding='utf-8'))
dur = {r['i']: r['duration'] for r in lines}
text = {r['i']: r['text'] for r in lines}
align = {r['i']: r.get('align') or [] for r in lines}
os.makedirs(out, exist_ok=True)
END = ('。', '」', '？', '！', '.', '?', '!', '"', '“', '”', '»')

# ---- index of every searched / generated picture (licences, authors, AI flag)
idx = {}
for rnd in sorted(os.listdir(imgsrc)) if os.path.isdir(imgsrc) else []:
    ip = os.path.join(imgsrc, rnd, 'index.json')
    if os.path.exists(ip):
        for q in json.load(open(ip, encoding='utf-8')):
            for r in q['results']:
                if r.get('file'): idx[f"{rnd}/{r['file']}"] = r
def is_ai(name):
    it = picks['images'][name]
    return bool(it.get('ai', (idx.get(it['src']) or {}).get('ai', False)))

size = {}
def img_size(name):
    if name not in size:
        if name not in picks['images']: raise SystemExit(f'picks.json: không có ảnh "{name}" trong "images"')
        size[name] = Image.open(f'{pub}/{base}/img/{name}.jpg').size
    return size[name]

# ---- voice timeline and captions
LEAD, TAIL = 0.3, 1.6
t = LEAD; starts = {}; caps = []; voice = []; srt = []
for i in range(1, len(lines) + 1):
    starts[i] = t
    voice.append({'s': round(t, 3), 'src': f'{base}/voice/{lines[i - 1]["file"]}'})
    parts = C.chunks(text[i], LANG)
    total_w = sum(C.weight(sp, LANG) for sp, _ in parts) or 1
    acc = 0
    for k, (sp, shown) in enumerate(parts):
        cs = t + C.time_at(acc / total_w, dur[i], align[i]) - (0.12 if k == 0 else 0.04)
        acc += C.weight(sp, LANG)
        caps.append({'s': round(max(0, cs), 3), 'e': round(t + dur[i] + 0.25, 3), 'text': shown, 'line': i})
    srt.append({'s': round(t, 3), 'e': round(t + dur[i], 3), 'text': text[i]})
    t += dur[i] + (0.4 if text[i].rstrip().endswith(END) else 0.22)
total = round(t - 0.22 + TAIL, 3)
for x, y in zip(caps, caps[1:]):   # a chunk stays until the next one, or a moment after its line ends
    x['e'] = round(min(y['s'], x['e']) if y['line'] != x['line'] else y['s'], 3)
caps[-1]['e'] = round(min(total - 0.4, caps[-1]['e'] + 0.6), 3)
caps = [c for c in caps if c['e'] - c['s'] > 0.05]
for x, y in zip(srt, srt[1:]): x['e'] = round(min(y['s'], x['e'] + 0.5), 3)

def at_time(li):
    """Moment of line number li (fractional = part-way through the line), on the voice timeline."""
    k = int(li); k = min(max(starts), max(min(starts), k))
    return starts[k] + (li - int(li)) * dur[k]

# ---- shots
shots_in = picks['shots']
if not shots_in: raise SystemExit('picks.json: chưa có "shots"')
bounds = [0.0] + [at_time(p['at']) - 0.12 for p in shots_in[1:]] + [total]
title = spec.get('title', '')
shots = []
for j, p in enumerate(shots_in):
    s, e = bounds[j], bounds[j + 1]
    if e - s < 0.6: raise SystemExit(f'ảnh {j + 1} ("at" {p.get("at")}): chỉ hiện {e - s:.2f} s (kiểm tra "at")')
    name = p['img']; w, h = img_size(name)
    view = p.get('view') or [0, 0, 1, 1]
    vasp = (view[2] - view[0]) * w / ((view[3] - view[1]) * h)
    box = L.pic_box(vasp, p.get('fit', 'cover'))
    basp = box[2] / box[3]
    pic = {'src': f'{base}/img/{name}.jpg', 'w': w, 'h': h, 'box': box, 'view': L.fit_view(view, basp, w, h),
           'drift': 0 if p.get('still') else p.get('drift', 0.07)}
    z = p.get('zoom')
    if z:
        zs = at_time(z['at']) if z.get('at') else s + 0.4
        pic['zoom'] = {'to': L.fit_view(z['to'], basp, w, h), 's': round(zs, 3), 'e': round(zs + z.get('dur', 1.6), 3)}
        pic['drift'] = 0
    marks = [{'s': round(at_time(m['at']) if m.get('at') else s, 3), 'box': m['box'], 'shape': m.get('shape', 'ellipse')}
             for m in p.get('marks', [])]
    r = idx.get(picks['images'][name]['src']) or {}
    it = picks['images'][name]
    ai = is_ai(name)
    credit = p.get('credit')
    if credit is None:
        credit = '' if ai else ' / '.join(x for x in (re.sub(r'\s+', ' ', it.get('artist') or r.get('artist') or '').strip()[:60],
                                                     it.get('license') or r.get('license') or '') if x)
    shots.append({'s': round(s, 3), 'e': round(e, 3), 'shot': j + 1, 'label': p.get('label', ''), 'credit': credit,
                  'ai': ai, 'pic': pic, 'marks': marks})

# ---- music bed: a quiet, dark score made for this length (the sample keeps its music far under the voice)
mu = {'style': 'tension', 'key': 'D', 'mode': 'minor', 'bpm': 70, 'energy': 0.3, **spec.get('music', {})}
music = mg.render([{'from': 0, 'to': total, **mu}], lambda v: v, total)
bed = music / (np.abs(music).max() or 1) * 0.8
mg.write_wav(f'{pub}/{base}/bed.wav', bed)

plan = {'duration': total, 'lang': LANG, 'title': title, 'titleSize': L.title_size(title, LANG), 'aiTag': AI_TAG,
        'shots': shots, 'caps': caps, 'voice': voice, 'music': f'{base}/bed.wav',
        'musicVolume': spec.get('music_volume', 0.14), 'fonts': []}
json.dump(plan, open(f'{out}/plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def ts(v):
    ms = int(round(v * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s_:02d},{ms:03d}'
with open(f'{out}/subtitles.srt', 'w', encoding='utf-8') as f:
    for k, sb in enumerate(srt, 1): f.write(f"{k}\n{ts(sb['s'])} --> {ts(sb['e'])}\n{sb['text']}\n\n")

# ---- sources: every picture used (title, author, date, licence, page, AI or not)
seen, rows, ai_rows, src_rows = set(), [], [], []
used = {p['img'] for p in shots_in}
for name, it in picks['images'].items():
    if name not in used: continue
    r = idx.get(it['src']) or {}
    ai = is_ai(name)
    page = it.get('page') or r.get('page') or ''
    key = page or it['src']
    if key in seen: continue
    seen.add(key)
    date = re.sub(r'date QS.*', '', r.get('date') or '').strip()
    artist = it.get('artist') or re.sub(r'\s+', ' ', r.get('artist') or '').strip()
    lic = it.get('license') or r.get('license') or ('AI-generated' if ai else '?')
    ttl = it.get('title') or r.get('title') or it['src']
    srcname = r.get('source', 'own' if it['src'].startswith('own/') else '')
    row = {'name': name, 'src': it['src'], 'title': ttl, 'artist': artist, 'date': date, 'license': lic, 'page': page, 'ai': ai}
    src_rows.append(row)
    if ai: ai_rows.append(f'- {ttl} ({srcname or "AI"})')
    else: rows.append(f"- {ttl} — {artist}{f' ({date})' if date else ''} — {lic}{f' [{srcname}]' if srcname else ''}" + (f"\n  {page}" if page else ''))
txt = 'Nguồn ảnh (ảnh CC BY và CC BY-SA phải ghi tên tác giả và giấy phép trong mô tả video):\n\n' + ('\n'.join(rows) or '(không có ảnh thật)') + '\n'
if ai_rows:
    note = {'ja': '※一部の画像はAIで生成したイメージです（実際の写真ではありません）。',
            'de': 'Hinweis: Einige Bilder sind KI-generierte Illustrationen (keine echten Fotos).'}[LANG]
    txt += f'\nẢnh minh họa tạo bằng AI (không phải ảnh thật, có chữ "{AI_TAG}" trên video). Nên ghi trong mô tả video:\n{note}\n\n' + '\n'.join(ai_rows) + '\n'
open(f'{out}/credits.txt', 'w', encoding='utf-8').write(txt)
shot_rows = []
for sh, ps in zip(shots, shots_in):
    said = [c['text'] for c in caps if sh['s'] - 0.01 <= c['s'] < sh['e']]
    shot_rows.append({'shot': sh['shot'], 'start': sh['s'], 'end': sh['e'], 'said': said, 'label': sh['label'], 'image': ps['img'],
                      'ai': sh['ai'], 'page': next((x['page'] for x in src_rows if x['name'] == ps['img']), ''),
                      'credit': sh['credit'], 'view': ps.get('view'), 'zoom': ps.get('zoom'),
                      'marks': [{'at_s': m['s'], 'box': m['box']} for m in sh['marks']]})
json.dump({'pictures': src_rows, 'shots': shot_rows}, open(f'{out}/sources.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'total {total} s; {len(shots)} shots; {len(caps)} captions; ' + ', '.join(f"{x['shot']}:{x['s']:.1f}–{x['e']:.1f}{' AI' if x['ai'] else ''}" for x in shots))
