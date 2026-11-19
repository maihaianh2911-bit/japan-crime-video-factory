#!/usr/bin/env python3
"""Plan of a crime video for the CrimeV composition, plus music bed, desk textures, subtitles and picture credits.

Usage: build.py <job_dir crime/N> <public_dir> <N> <img_src_dir> <out_dir>
Reads <job_dir>/script.json (title, lines), <job_dir>/picks.json (images, scenes), <public_dir>/crime/<N>/voice/
lines.json (measured line lengths, Whisper word times) and the prepared pictures in <public_dir>/crime/<N>/img/.
Writes <out_dir>/plan.json, subtitles.srt, credits.txt, sources.json, edits.md and <public_dir>/crime/<N>/bed.wav, bg.jpg,
grain.png.

Layout of the owner's sample (scripts/crime/layout.py): a scene is a desk on which items are laid down one by one as
the voice names them — photo, tag, header, card, stamp, big, text, line (see AGENT_CRIME.md §2 for the fields). A
scene starts at its "at" (line number, fractional = part-way through the line) and lasts until the next one. An
item's "at" is a line number, or "<line>:<words>" = the moment those words of that line are spoken (Whisper word
times), or nothing = the start of its scene. The voice is shown in the subtitle box, a clause at a time
(captions.subs). A scene with "edit": "<name>" first gets the places of that scene edit (scripts/crime/edits.py, the
catalogue); <out_dir>/edits.md lists every scene with its edit and Claude's "why" for the owner, and under the list
how many different pictures the video shows, the pictures shown in more than two scenes and the scenes with text alone.

Timing: every line starts after the previous one plus a pause (0.45 s after a sentence end, 0.25 s otherwise),
both divided by script.json "speed" (the pace of the voice, default 1.0: a faster voice gets shorter pauses).
"""
import json, os, re, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import music_gen as mg
import ff
import layout as L
import captions as C
import edits as E
import board
from channel import LANG, AI_TAG

MOVES = ['push-in', 'pan-right', 'pull-back', 'pan-left', 'rise', 'fall']   # the moves of a picture, CrimeV.tsx
KINDS = ('photo', 'tag', 'header', 'card', 'stamp', 'big', 'text', 'line', 'roster')
COLORS = ('yellow', 'red', 'white', 'black')


def fail(msg):
    raise SystemExit(f'picks.json: {msg}')


QUOTE_ROW = 13                       # characters a row of a big quote holds before it wraps
QUOTE_BREAK = set('」』）)をにはがでとへも')   # a row may end after these (a particle or a closing bracket)


def quote_rows(text):
    """The rows of a quote printed big: one row per clause (after 、), a clause longer than QUOTE_ROW wrapped after the
    last particle or closing bracket that fits and leaves at least 4 characters on both sides (a clause only a little
    too long, with no such place, stays whole; a long one without it is cut at QUOTE_ROW), short rows joined."""
    rows = []
    for r in (x for x in re.split(r'(?<=[、，,])', text.strip()) if x):
        while len(r) > QUOTE_ROW:
            cut = max((i + 1 for i, ch in enumerate(r[:QUOTE_ROW]) if ch in QUOTE_BREAK and i + 1 >= 4 and len(r) - i - 1 >= 4), default=0)
            if not cut:
                if len(r) <= QUOTE_ROW + 3: break
                cut = QUOTE_ROW
            rows.append(r[:cut]); r = r[cut:]
        rows.append(r)
    joined = []
    for r in rows:
        if joined and len(joined[-1]) + len(r) <= QUOTE_ROW: joined[-1] += r
        else: joined.append(r)
    return joined


def main(job, pub, N, imgsrc, out):
    base = f'crime/{N}'
    spec = json.load(open(f'{job}/script.json', encoding='utf-8'))
    picks = json.load(open(f'{job}/picks.json', encoding='utf-8'))
    lines = json.load(open(f'{pub}/{base}/voice/lines.json', encoding='utf-8'))
    dur = {r['i']: r['duration'] for r in lines}
    text = {r['i']: r['text'] for r in lines}
    align = {r['i']: r.get('align') or [] for r in lines}
    os.makedirs(out, exist_ok=True)
    END = ('。', '」', '？', '！', '.', '?', '!', '"', '“', '”', '»')
    images = picks.get('images') or {}

    # ---- index of every searched / generated picture (licences, authors, AI flag)
    idx = {}
    for rnd in sorted(os.listdir(imgsrc)) if os.path.isdir(imgsrc) else []:
        ip = os.path.join(imgsrc, rnd, 'index.json')
        if os.path.exists(ip):
            for q in json.load(open(ip, encoding='utf-8')):
                for r in q['results']:
                    if r.get('file'): idx[f"{rnd}/{r['file']}"] = r
    def is_ai(name):
        it = images[name]
        return bool(it.get('ai', (idx.get(it['src']) or {}).get('ai', False)))
    size = {}
    def img_size(name):
        if name not in size:
            if name not in images: fail(f'không có ảnh "{name}" trong "images"')
            size[name] = Image.open(f'{pub}/{base}/img/{name}.jpg').size
        return size[name]

    # ---- voice timeline and subtitles
    LEAD, TAIL = 0.4, 2.0
    pace = min(1.3, max(0.8, float(spec.get('speed') or 1.0)))
    P_END, P_MID = 0.45 / pace, 0.25 / pace
    t = LEAD; starts = {}; subs = []; voice = []; srt = []
    for i in range(1, len(lines) + 1):
        starts[i] = t
        voice.append({'s': round(t, 3), 'src': f'{base}/voice/{lines[i - 1]["file"]}'})
        parts = C.subs(text[i], LANG)
        total_w = sum(C.weight(sp, LANG) for sp, _ in parts) or 1
        acc = 0
        for k, (sp, shown) in enumerate(parts):
            cs = t + C.time_at(acc / total_w, dur[i], align[i]) - (0.1 if k == 0 else 0.05)
            acc += C.weight(sp, LANG)
            subs.append({'s': round(max(0, cs), 3), 'e': round(t + dur[i] + 0.2, 3), 'text': shown, 'line': i})
        srt.append({'s': round(t, 3), 'e': round(t + dur[i], 3), 'text': text[i]})
        t += dur[i] + (P_END if text[i].rstrip().endswith(END) else P_MID)
    total = round(t - P_MID + TAIL, 3)
    for x, y in zip(subs, subs[1:]):   # a clause stays until the next one, or a moment after its line ends
        x['e'] = round(min(y['s'], x['e']) if y['line'] != x['line'] else y['s'], 3)
    subs = [c for c in subs if c['e'] - c['s'] > 0.05]
    for x, y in zip(srt, srt[1:]): x['e'] = round(min(y['s'], x['e'] + 0.5), 3)

    def at_time(at, where=''):
        """Moment of `at`: a line number (fractional = part-way through the line) or "<line>:<words>" (when those
        words of the line are spoken)."""
        if isinstance(at, str):
            m = re.fullmatch(r'\s*(\d+)\s*[:：]\s*(.+?)\s*', at)
            if not m: fail(f'{where}: "at" "{at}" không đúng dạng "<câu>:<chữ>"')
            k, words = int(m.group(1)), m.group(2)
            if k not in starts: fail(f'{where}: "at" "{at}": không có câu {k}')
            pos = text[k].find(words)
            if pos < 0: fail(f'{where}: "at" "{at}": câu {k} không có "{words}" ({text[k]})')
            frac = C.weight(text[k][:pos], LANG) / C.weight(text[k], LANG) if pos else 0.0
            return starts[k] + C.time_at(frac, dur[k], align[k]) - 0.08
        k = int(at); k = min(max(starts), max(min(starts), k))
        return starts[k] + (at - int(at)) * dur[k]

    fx = picks.get('fx') or {}   # owner 18/11/2026: the picture effects of japan-news (motion, depth, text)

    # ---- quotes: a line printed big on the frame while it is spoken (picks.json "quotes": [line numbers]), as the hook
    # line of japan-news; its subtitle is not shown meanwhile
    quotes = []
    for qn in picks.get('quotes') or []:
        if qn not in starts: fail(f'"quotes": không có câu {qn}')
        qs, qe = starts[qn], starts[qn] + dur[qn]
        qt = text[qn].strip()
        qt = '\n'.join(quote_rows(qt))
        quotes.append({'s': round(qs - 0.1, 3), 'e': round(qe + 0.35, 3), 'text': qt})
        subs = [c for c in subs if c['line'] != qn]

    # ---- scenes
    scenes_in = picks.get('scenes')
    if not scenes_in: fail('chưa có "scenes"')
    bounds = [0.0] + [at_time(p.get('at', 1), f'cảnh {j + 2}') - 0.12 for j, p in enumerate(scenes_in[1:])] + [total]
    scenes, used = [], []
    uses, bare = {}, []   # picture file -> number of scenes that show it; scenes with text alone
    for j, sc in enumerate(scenes_in):
        s, e = bounds[j], bounds[j + 1]
        where = f'cảnh {j + 1}'
        sc = E.apply(sc, j + 1, fail)   # "edit": the template's places for what Claude left out; untouched without it
        if e - s < 1.0: fail(f'{where} ("at" {sc.get("at")}): chỉ hiện {e - s:.2f} s (kiểm tra "at")')
        items = []
        for n, it in enumerate(sc.get('items') or []):
            w_ = f'{where}, mục {n + 1}'
            kind = next((k for k in KINDS if k in it), None)
            if not kind: fail(f'{w_}: thiếu loại ({", ".join(KINDS)})')
            d = L.DEF.get(kind, {})
            def when(at, ww):
                """Time of an "at" inside this scene: refused when it falls after the scene (the item would never
                be seen), moved to the scene start when it falls before."""
                tt = at_time(at, ww)
                if tt > e - 0.3: fail(f'{ww}: "at" {json.dumps(at, ensure_ascii=False)} rơi vào {tt:.1f} s, sau khi cảnh kết thúc ({e:.1f} s)')
                return max(s, tt)
            st = round(when(it['at'], w_) if it.get('at') is not None else s, 3)
            o = {'k': kind, 's': st, 'x': it.get('x', d.get('x', 540)), 'y': it.get('y', d.get('y', 900)),
                 'rot': it.get('rot', 0)}
            if it.get('until') is not None: o['e'] = round(at_time(it['until'], w_), 3)
            if kind == 'photo':
                # one picture, or a list shown one after the other in the same frame (owner 18/11/2026: "quá ít hình
                # ảnh, 1 ảnh dừng lại quá lâu, chuyển động gần như bằng không": a new picture every 3–4 s, each moving)
                entries = it['photo'] if isinstance(it['photo'], list) else [it['photo']]
                entries = [{'img': x} if isinstance(x, str) else {**x, 'img': x.get('img') or x.get('photo')} for x in entries]
                if not entries or not all(x['img'] for x in entries): fail(f'{w_}: "photo" trống')
                name = entries[0]['img']; used.extend(x['img'] for x in entries)
                iw, ih = img_size(name)
                view = entries[0].get('view') or it.get('view') or [0, 0, 1, 1]
                vasp = (view[2] - view[0]) * iw / ((view[3] - view[1]) * ih)
                w = it.get('w', d['w']); h = it.get('h', round(w / vasp))
                if not (it.get('h') or it.get('w')) and h > 900: h = 900; w = round(h * vasp)   # a tall picture stays on the desk
                v = L.fit_view(view, w / h, iw, ih)
                o.update({'src': f'{base}/img/{name}.jpg', 'iw': iw, 'ih': ih, 'w': w, 'h': h, 'view': v,
                          'drift': 0 if it.get('still') else it.get('drift', 0.05), 'ai': is_ai(name),
                          'frame': 'none' if it.get('frame') == 'none' else 'white'})
                if fx.get('depth') and it.get('depth', True) and os.path.exists(f'{pub}/{base}/img/{name}.depth.png'):
                    o['depth'] = f'{base}/img/{name}.depth.png'   # the 2.5D map made by prep.py
                z = it.get('zoom')
                if z:
                    zs = when(z['at'], w_) if z.get('at') is not None else st + 0.5
                    o['zoom'] = {'to': L.fit_view(z['to'], w / h, iw, ih), 's': round(zs, 3), 'e': round(zs + z.get('dur', 1.6), 3)}
                    o['drift'] = 0
                o['marks'] = [{'s': round(max(st, when(m['at'], w_)) if m.get('at') is not None else st + 0.4, 3), 'box': m['box'],
                               'shape': m.get('shape', 'ellipse'), 'color': m.get('color', 'yellow')} for m in it.get('marks', [])]

                def credit_of(nm, given=None):
                    rec = images[nm]; r = idx.get(rec['src']) or {}
                    if given is not None: return given
                    return '' if is_ai(nm) else ' / '.join(x for x in (re.sub(r'\s+', ' ', rec.get('artist') or r.get('artist') or '').strip()[:60],
                                                                     rec.get('license') or r.get('license') or '') if x)
                o['credit'] = credit_of(name, it.get('credit'))
                # the slides: their start times (an "at" of their own, else shared evenly), view, move, depth
                times = [st] + [when(x['at'], w_) if x.get('at') is not None else None for x in entries[1:]]
                known = [k for k, x in enumerate(times) if x is not None] + [len(entries)]
                for ka, kb in zip(known, known[1:]):
                    end = times[kb] if kb < len(entries) else e
                    for k in range(ka + 1, kb): times[k] = times[ka] + (end - times[ka]) * (k - ka) / (kb - ka)
                seed = sum(map(ord, name)) + j
                slides = []
                for k, x in enumerate(entries):
                    nm = x['img']; siw, sih = img_size(nm)
                    sv = L.fit_view(x.get('view') or (view if k == 0 else [0, 0, 1, 1]), w / h, siw, sih)
                    mv = x.get('move') or (it.get('move') if k == 0 else None) or ('hold' if it.get('still') or z else MOVES[(seed + k) % len(MOVES)])
                    if mv not in MOVES + ['hold']: fail(f'{w_}: "move" phải là một trong {", ".join(MOVES + ["hold"])}')
                    sl = {'src': f'{base}/img/{nm}.jpg', 'iw': siw, 'ih': sih, 'view': sv, 's': round(times[k], 3), 'move': mv,
                          'ai': is_ai(nm), 'credit': credit_of(nm, x.get('credit', it.get('credit') if k == 0 else None))}
                    if fx.get('depth') and x.get('depth', it.get('depth', True)) and os.path.exists(f'{pub}/{base}/img/{nm}.depth.png'):
                        sl['depth'] = f'{base}/img/{nm}.depth.png'
                    slides.append(sl)
                for k, sl in enumerate(slides):
                    sl['e'] = round(slides[k + 1]['s'] if k + 1 < len(slides) else e, 3)
                    if sl['e'] - sl['s'] > 5.5:
                        print(f'chú ý: {w_}: ảnh "{os.path.basename(sl["src"])[:-4]}" đứng {sl["e"] - sl["s"]:.1f} s (nên đổi ảnh mỗi 3–4 s: "photo": [ … ])')
                o['slides'] = slides
            elif kind == 'tag':
                o.update({'text': it['tag'], 'color': it.get('color', 'yellow'), 'size': it.get('size', d['size']),
                          'font': it.get('font', 'hand' if it.get('color', 'yellow') in ('yellow', 'red') else 'serif' if it.get('color') == 'white' else 'mono')})
                if o['color'] not in COLORS: fail(f'{w_}: "color" phải là {", ".join(COLORS)}')
            elif kind == 'header':
                o.update({'title': it['header'], 'kicker': it.get('kicker', ''), 'size': it.get('size', d['size'])})
            elif kind == 'card':
                c = it['card'] if isinstance(it['card'], dict) else {'rows': it['card']}
                rows, t0 = [], st + (0.5 if c.get('head') else 0.25)
                for k, r in enumerate(c.get('rows') or []):
                    r = {'text': r} if isinstance(r, str) else dict(r)
                    rs = when(r['at'], w_) if r.get('at') is not None else t0
                    t0 = rs + 0.6
                    row = {'s': round(min(e - 0.3, max(st, rs)), 3), 'text': r.get('text', ''), 'right': r.get('right', ''),
                           'color': r.get('color', ''), 'check': bool(r.get('check'))}
                    if r.get('strike') is not None: row['strike'] = round(max(row['s'], when(r['strike'], w_)), 3)
                    rows.append(row)
                o.update({'style': c.get('style', 'paper'), 'head': c.get('head', ''), 'rows': rows,
                          'w': it.get('w', d['w']), 'h': it.get('h', d['h']), 'size': it.get('size', d['size'])})
            elif kind == 'stamp':
                o.update({'text': it['stamp'], 'size': it.get('size', d['size']), 'rot': it.get('rot', -8)})
            elif kind == 'big':
                o.update({'num': str(it['big']), 'text': it.get('text', ''), 'size': it.get('size', d['size'])})
            elif kind == 'text':
                rows, t0 = [], st
                for r in (it['text'] if isinstance(it['text'], list) else [it['text']]):
                    r = {'text': r} if isinstance(r, str) else dict(r)
                    rs = when(r['at'], w_) if r.get('at') is not None else t0
                    t0 = rs + 0.5
                    rows.append({'s': round(min(e - 0.3, max(st, rs)), 3), 'text': r.get('text', ''), 'color': r.get('color', 'white')})
                o.update({'rows': rows, 'size': it.get('size', d['size'])})
            elif kind == 'roster':   # the opening of a "Top" series episode: a grid of round portraits, one picked
                ppl = []
                for k, pr in enumerate(it['roster'][:9]):
                    q = {'name': pr.get('name', ''), 'sub': pr.get('sub', ''), 's': round(st + (0.1 + 0.05 * k if it.get('done') else 0.35 + 0.16 * k), 3)}
                    if pr.get('img'):
                        name = pr['img']; used.append(name); iw, ih = img_size(name)
                        q.update({'src': f'{base}/img/{name}.jpg', 'iw': iw, 'ih': ih, 'focus': pr.get('focus', [0.5, 0.35])})
                    ppl.append(q)
                if not ppl: fail(f'{w_}: "roster" trống')
                pick = int(it.get('pick', 0))
                if not 0 <= pick < len(ppl): fail(f'{w_}: "pick" {pick} ngoài danh sách (0–{len(ppl) - 1})')
                o.update({'people': ppl, 'title': it.get('title', ''), 'kicker': it.get('kicker', ''), 'pick': pick,
                          'pick_s': round(when(it['pick_at'], w_) if it.get('pick_at') is not None else e - 2.2, 3),
                          'note': it.get('note', ''), 'rank': it.get('rank', ''), 'done': [int(d) for d in it.get('done') or []]})
            elif kind == 'line':
                (x0, y0), (x1, y1) = it['line']
                o.update({'pts': [[x0, y0], [x1, y1]], 'color': it.get('color', 'red')})
            items.append(o)
        scenes.append({'s': round(s, 3), 'e': round(e, 3), 'scene': j + 1, 'bg': sc.get('bg', 'wood'),
                       'push': sc.get('push', 0.07), 'items': items, **({'edit': sc['edit']} if sc.get('edit') else {})})
        for src in {images[x if isinstance(x, str) else (x.get('img') or x.get('photo'))]['src'] for it in sc.get('items') or [] if 'photo' in it for x in (it['photo'] if isinstance(it['photo'], list) else [it['photo']])}:   # two crops of one file = one picture
            uses[src] = uses.get(src, 0) + 1
        if not any(o['k'] in ('photo', 'card', 'big') for o in items): bare.append(j + 1)
    # how many different pictures the video shows (owner, 17/11/2026: the videos were short of pictures): the count, the
    # pictures shown in more than two scenes and the scenes with text alone go to the log and under the list of edits
    often = {k: v for k, v in uses.items() if v > 2}
    pic_note = [f'{len(uses)} ảnh khác nhau cho {len(scenes)} cảnh' + (' (ít: nên có ít nhất 3 ảnh cho mỗi 4 cảnh)' if len(uses) * 4 < len(scenes) * 3 else '')]
    if often: pic_note.append('ảnh dùng quá 2 lần: ' + ', '.join(f'{k} ({v} cảnh)' for k, v in sorted(often.items())))
    if len(bare) * 6 > len(scenes): pic_note.append(f'{len(bare)} cảnh chỉ có chữ (cảnh ' + ', '.join(map(str, bare)) + '): nhiều hơn 1/6 số cảnh')
    print('ảnh: ' + '; '.join(pic_note))
    open(f'{out}/edits.md', 'w', encoding='utf-8').write(E.listing(scenes_in, text, bounds) + '\nẢnh: ' + '; '.join(pic_note) + '.\n')
    if E.repeats(scenes_in):
        print('chú ý: cảnh ' + ', '.join(map(str, E.repeats(scenes_in))) + ' dùng cùng kiểu edit với cảnh ngay trước nó (nên đổi kiểu)')

    # ---- music: a recording found with music:<words> (picks.json "music": {"pick": "<round>/<k>-<n>.<ext>", "volume",
    # "start"}; owner 18/11/2026, as in japan-news-video-factory), else the made dark bed
    pm, music_row = picks.get('music'), None
    if pm:
        pm = {'pick': pm} if isinstance(pm, str) else pm
        src_audio = os.path.join(imgsrc, pm['pick'])
        if not os.path.isfile(src_audio): fail(f'"music": không có bản nhạc "{pm["pick"]}" (tìm bằng music:<từ khóa>)')
        ff.run('-ss', str(pm.get('start', 0)), '-i', src_audio, '-af', 'loudnorm=I=-23:TP=-2:LRA=11', '-ar', '44100', '-ac', '2',
               '-c:a', 'libmp3lame', '-q:a', '3', f'{pub}/{base}/music.mp3')
        rnd, fname = pm['pick'].split('/', 1)
        music_row = next((r for g in json.load(open(os.path.join(imgsrc, rnd, 'index.json'), encoding='utf-8')) for r in g['results']
                          if r.get('file') == fname), {'title': fname})
        music_file, music_vol, music_loop = f'{base}/music.mp3', 0.3 * float(pm.get('volume', 1)), True
    else:
        mu = {'style': 'tension', 'key': 'D', 'mode': 'minor', 'bpm': 70, 'energy': 0.3, **spec.get('music', {})}
        music = mg.render([{'from': 0, 'to': total, **mu}], lambda v: v, total)
        bed = music / (np.abs(music).max() or 1) * 0.8
        mg.write_wav(f'{pub}/{base}/bed.wav', bed)
        music_file, music_vol, music_loop = f'{base}/bed.wav', spec.get('music_volume', 0.16), False
    # ---- voice volume (owner, 19/11/2026: "cho voice tăng 40%" = louder, not faster): picks.json "voice": {"volume": 1.4}
    # makes the voice 1.4× louder in the finished video while the music keeps its level: the music goes 1.4× under the
    # voice in the mix, and the final loudness target (run.py encode) goes up by 20·log10(1.4) ≈ 2.9 dB from -15 LUFS
    vv = float((picks.get('voice') or {}).get('volume', 1))
    if not 0.5 <= vv <= 2: fail('"voice": "volume" phải từ 0.5 đến 2 (1.4 = to hơn 40%)')
    music_vol, loudness = music_vol / vv, round(-15 + 20 * float(np.log10(vv)), 1)
    tone = 'normal' if picks.get('tone') == 'normal' else 'dark'
    board.desk(f'{pub}/{base}/bg.jpg', light=tone == 'normal'); board.grain(f'{pub}/{base}/grain.png')

    plan = {'duration': total, 'lang': LANG, 'title': spec.get('title', ''), 'aiTag': AI_TAG,
            'bg': f'{base}/bg.jpg', 'grain': f'{base}/grain.png', 'scenes': scenes, 'subs': subs, 'voice': voice,
            'music': music_file, 'musicVolume': music_vol, 'musicLoop': music_loop, 'fonts': [], 'families': {},
            'fx': {k: bool(fx.get(k)) for k in ('motion', 'depth', 'text')}, 'quotes': quotes, 'tone': tone,
            'loudness': loudness}
    json.dump(plan, open(f'{out}/plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    def ts(v):
        ms = int(round(v * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
        return f'{h:02d}:{m:02d}:{s_:02d},{ms:03d}'
    with open(f'{out}/subtitles.srt', 'w', encoding='utf-8') as f:
        for k, sb in enumerate(srt, 1): f.write(f"{k}\n{ts(sb['s'])} --> {ts(sb['e'])}\n{sb['text']}\n\n")

    # ---- sources: every picture used (title, author, date, licence, page, AI or not)
    seen, rows, ai_rows, src_rows = set(), [], [], []
    for name, it in images.items():
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
        src_rows.append({'name': name, 'src': it['src'], 'title': ttl, 'artist': artist, 'date': date, 'license': lic, 'page': page, 'ai': ai})
        if ai: ai_rows.append(f'- {ttl} ({srcname or "AI"})')
        else: rows.append(f"- {ttl} — {artist}{f' ({date})' if date else ''} — {lic}{f' [{srcname}]' if srcname else ''}" + (f"\n  {page}" if page else ''))
    txt = 'Nguồn ảnh (ảnh CC BY và CC BY-SA phải ghi tên tác giả và giấy phép trong mô tả video):\n\n' + ('\n'.join(rows) or '(không có ảnh thật)') + '\n'
    if ai_rows:
        note = {'ja': '※一部の画像はAIで生成したイメージです（実際の写真ではありません）。',
                'de': 'Hinweis: Einige Bilder sind KI-generierte Illustrationen (keine echten Fotos).'}[LANG]
        txt += f'\nẢnh minh họa tạo bằng AI (không phải ảnh thật, có chữ "{AI_TAG}" trên video). Nên ghi trong mô tả video:\n{note}\n\n' + '\n'.join(ai_rows) + '\n'
    if music_row:
        txt += f"\nNhạc: {music_row.get('title', '')} — {music_row.get('artist', '')} — {music_row.get('license', '')}\n  {music_row.get('page', '')}\n"
    open(f'{out}/credits.txt', 'w', encoding='utf-8').write(txt)
    scene_rows = []
    for sc in scenes:
        said = [c['text'] for c in subs if sc['s'] - 0.01 <= c['s'] < sc['e']]
        photos = [sl for i in sc['items'] if i['k'] == 'photo' for sl in (i.get('slides') or [i])]
        scene_rows.append({'scene': sc['scene'], 'start': sc['s'], 'end': sc['e'], 'said': said, **({'edit': sc['edit']} if sc.get('edit') else {}),
                           'photos': [{'image': os.path.basename(p['src'])[:-4], 'ai': p['ai'], 'credit': p['credit'],
                                       'page': next((x['page'] for x in src_rows if x['name'] == os.path.basename(p['src'])[:-4]), '')} for p in photos],
                           'texts': [i.get('text') or i.get('title') or i.get('num') or '' for i in sc['items'] if i['k'] in ('tag', 'header', 'stamp', 'big')]})
    json.dump({'pictures': src_rows, 'scenes': scene_rows}, open(f'{out}/sources.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'total {total} s; {len(scenes)} scenes; {sum(len(s["items"]) for s in scenes)} items; {len(subs)} subtitles')
    return plan


if __name__ == '__main__':
    main(*sys.argv[1:6])
