#!/usr/bin/env python3
"""The picture review (owner, 18/11/2026, as in japan-news-video-factory: "đọc lại hình ảnh đã chọn xem đã phù hợp
với nội dung cần thể hiện chưa, chưa thì chọn lại, duyệt lại, khi nào ổn mới lấy").

Every chosen picture on one row: the frame as it will be seen (rendered by the video's own code a moment after the
picture comes in), the whole picture as found, the words spoken while it is on screen (from the moment it comes in
to the next picture of its scene, or the scene's end), and where it comes from (title, page, licence from the
search index, and the query that found it). The portraits of a `roster` are rows too, beside the person's name.
Claude reads every row and checks that the picture shows what the words say at that moment; re-picks and runs this
again until every row passes (AGENT_CRIME.md §2.7).

Usage: review.py <crime/N dir with script.json + picks.json> <renders crime/N dir with voice/ and img/> <out dir>
Writes <out>/review-<page>.jpg (six rows a page) and <out>/review.md (one line a picture, with an empty verdict).
Needs node_modules (npm ci) and the fonts (scripts/crime/get_fonts.sh "$FONTSOURCE"; default /tmp/fontsource)."""
import json, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); ROOT = os.path.dirname(os.path.dirname(HERE))
ROW, STILL_W, WHOLE_W, WIDTH = 520, 292, 420, 1700


class Pen:
    """Text in the review sheet: Japanese in the video's own font (Noto Sans JP chunks of FONTSOURCE, chosen per
    character by unicode-range), everything else (Vietnamese, Latin) in DejaVu Sans."""
    def __init__(self, size):
        import fonts
        self.size, self.cache = size, {}
        try: self.chunks = [(fonts.ranges(ur), path) for fam, path, ur, wt, st in fonts.faces(os.environ.get('FONTSOURCE', '/tmp/fontsource'), 'ja') if fam == 'Noto Sans JP']
        except Exception: self.chunks = []
        latin = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        self.latin = ImageFont.truetype(latin, size) if os.path.exists(latin) else ImageFont.load_default(size)

    def font(self, ch):
        o = ord(ch)
        if o < 0x2000: return self.latin
        for rs, path in self.chunks:
            if any(a <= o <= b for a, b in rs):
                if path not in self.cache:
                    f = ImageFont.truetype(path, self.size)
                    try: f.set_variation_by_axes([700])
                    except Exception: pass
                    self.cache[path] = f
                return self.cache[path]
        return self.latin

    def length(self, text):
        return sum(self.font(c).getlength(c) for c in text)

    def draw(self, d, xy, text, fill):
        x, y = xy
        for c in text:
            f = self.font(c); d.text((x, y + self.size), c, font=f, fill=fill, anchor='ls'); x += f.getlength(c)   # one baseline for both fonts


def wrapped(text, pen, width):
    rows, row = [], ''
    for ch in text:
        if ch == '\n' or pen.length(row + ch) > width:
            rows.append(row); row = '' if ch == '\n' else ch
        else:
            row += ch
    return rows + ([row] if row else [])


def fitted(im, w, h):
    im = im.convert('RGB'); im.thumbnail((w, h)); return im


def main():
    job, rend, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='crime-review-')
    pub = os.path.join(tmp, 'public'); base = os.path.join(pub, 'crime', 'P')
    os.makedirs(base); shutil.copytree(os.path.join(rend, 'voice'), os.path.join(base, 'voice'))
    imgsrc = os.path.join(tmp, 'img'); shutil.copytree(os.path.join(rend, 'img'), imgsrc)
    if os.path.isdir(os.path.join(job, 'own')): shutil.copytree(os.path.join(job, 'own'), os.path.join(imgsrc, 'own'), dirs_exist_ok=True)

    def run(*a):
        if subprocess.run([sys.executable, *a], stdout=subprocess.DEVNULL).returncode: sys.exit(1)
    run(os.path.join(HERE, 'prep.py'), os.path.join(job, 'picks.json'), imgsrc, os.path.join(base, 'img'))
    run(os.path.join(HERE, 'build.py'), job, pub, 'P', imgsrc, os.path.join(tmp, 'out'))
    plan_p = os.path.join(tmp, 'out', 'plan.json')
    run(os.path.join(HERE, 'fonts.py'), plan_p, os.environ.get('FONTSOURCE', '/tmp/fontsource'), pub)
    plan = json.load(open(plan_p, encoding='utf-8'))
    picks = json.load(open(os.path.join(job, 'picks.json'), encoding='utf-8'))

    # where every picture comes from: the search index of its round (title, page, licence, the query)
    found = {}
    for rnd in sorted(os.listdir(imgsrc)):
        ip = os.path.join(imgsrc, rnd, 'index.json')
        if os.path.exists(ip):
            for g in json.load(open(ip, encoding='utf-8')):
                for r in g.get('results', []):
                    if r.get('file'): found[f"{rnd}/{r['file']}"] = {**r, 'query': g.get('query', '')}
    name_of = lambda src: os.path.basename(src)[:-4]
    origin = lambda name: found.get((picks['images'].get(name) or {}).get('src', ''), {})

    def said(s, e):
        return ''.join(c['text'] for c in plan['subs'] if c['e'] > s + 0.05 and c['s'] < e - 0.05)

    rows = []   # (scene, label, picture name, time of the still, words, whole picture path)
    for sc in plan['scenes']:
        photos = [it for it in sc['items'] if it['k'] == 'photo']
        for k, it in enumerate(photos):
            nxt = photos[k + 1]['s'] if k + 1 < len(photos) else sc['e']
            t = min(sc['e'] - 0.1, max(it['s'] + 1.2, (it['s'] + nxt) / 2))
            n = name_of(it['src'])
            rows.append((sc, f"ảnh {k + 1}", n, t, said(it['s'], nxt), os.path.join(base, 'img', n + '.jpg')))
        for it in sc['items']:
            if it['k'] == 'roster':
                for k, p in enumerate(it['people']):
                    if p.get('src'):
                        n = name_of(p['src'])
                        rows.append((sc, f"chân dung {k + 1}", n, min(sc['e'] - 0.1, it['pick_s'] + 1.4) if k == it['pick'] else it['s'] + 2.2,
                                     f"[{p['name']} {p.get('sub', '')}] " + said(sc['s'], sc['e']), os.path.join(base, 'img', n + '.jpg')))
    if not rows:
        print('no picture to review'); return
    times = sorted({round(r[3], 2) for r in rows})
    subprocess.run(['node', os.path.join(HERE, 'stills.mjs'), plan_p, pub, os.path.join(tmp, 'f'), *[f'{t:.2f}' for t in times]],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)

    big, small = Pen(30), Pen(22)
    notes = ['| Cảnh | Ảnh | Lời đọc lúc ảnh hiện | Nguồn | Đạt? |', '|---|---|---|---|---|']
    pages = [rows[i:i + 6] for i in range(0, len(rows), 6)]
    for pn, page in enumerate(pages, 1):
        sheet = Image.new('RGB', (WIDTH, ROW * len(page)), 'white'); d = ImageDraw.Draw(sheet)
        for ri, (sc, what, n, t, words, whole) in enumerate(page):
            top = ri * ROW
            still = os.path.join(tmp, f'f_{t:.2f}.jpg')
            if os.path.exists(still): sheet.paste(fitted(Image.open(still), STILL_W, ROW - 20), (10, top + 10))
            size = 'missing'
            src = origin(n)
            raw = os.path.join(imgsrc, (picks['images'].get(n) or {}).get('src', ''))
            pic = raw if os.path.isfile(raw) else whole
            if os.path.exists(pic):
                im = Image.open(pic); size = f'{im.width}x{im.height}'
                sheet.paste(fitted(im, WHOLE_W, ROW - 20), (STILL_W + 30, top + 10))
            x, y = STILL_W + WHOLE_W + 60, top + 14
            small.draw(d, (x, y), f"Cảnh {sc['scene']} · {sc.get('edit', '')} · {what} · {n} ({size}) · {t:.1f}s", '#555'); y += 38
            for tr in wrapped(f'「{words}」', big, WIDTH - x - 20)[:7]:
                big.draw(d, (x, y), tr, 'black'); y += 42
            y += 10
            for tr in wrapped(f"{src.get('title', '')}  —  {src.get('page', '')}  ({src.get('license', '')}; tìm bằng: {src.get('query', '')})",
                              small, WIDTH - x - 20)[:4]:
                small.draw(d, (x, y), tr, '#246'); y += 30
            d.line((0, top + ROW - 1, WIDTH, top + ROW - 1), fill='#ccc', width=2)
            notes.append(f"| {sc['scene']} {sc.get('edit', '')} | {n} ({what}) | {words[:80]} | {src.get('title', '')[:60]} | [ ] |")
        sheet.save(os.path.join(out, f'review-{pn}.jpg'), quality=85)
    open(os.path.join(out, 'review.md'), 'w', encoding='utf-8').write('\n'.join(notes) + '\n')
    print(f'{len(rows)} pictures, {len(pages)} pages: {out}/review-1.jpg … review.md')
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
