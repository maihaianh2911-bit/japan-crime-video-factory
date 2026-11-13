"""Draw one frame of a plan shot with PIL, laid out as CrimeV (same boxes from layout.py), for the framing preview.
Text uses the video's own fonts when FONTSOURCE holds them (scripts/crime/get_fonts.sh), else a local font; positions,
picture regions, rings, zooms, drifts, the caption and the AI tag are exact."""
import os, re
from PIL import Image, ImageDraw, ImageFont
import layout as L

FONTS = ['/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
         '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']
YELLOW, RED = (255, 210, 26), (217, 42, 28)
_fonts, _chunks = {}, {}


def chunks(pkg):
    """[(ranges, woff2 path)] of a fontsource package in FONTSOURCE (the video's own fonts), [] when absent."""
    if pkg not in _chunks:
        base = os.path.join(os.environ.get('FONTSOURCE', '/tmp/fontsource'), pkg); out = []
        if os.path.exists(os.path.join(base, 'index.css')):
            for blk in re.findall(r'@font-face\s*{(.*?)}', open(os.path.join(base, 'index.css')).read(), re.S):
                f = re.search(r"url\(\./files/([^)]+\.woff2)\)", blk).group(1)
                rs = []
                for part in re.search(r'unicode-range:\s*([^;]+);', blk).group(1).split(','):
                    part = part.strip().replace('U+', ''); a, b = part.split('-') if '-' in part else (part, part)
                    rs.append((int(a, 16), int(b, 16)))
                out.append((rs, os.path.join(base, 'files', f)))
        _chunks[pkg] = out
    return _chunks[pkg]


class Face:
    """Text in the video's fonts when FONTSOURCE holds them (per character: the chunk that covers it), else a local
    font. role: head | cap | small."""
    def __init__(self, lang, role, px):
        self.px, self.lang, self.role = px, lang, role
        pkg = {'ja': 'noto-sans-jp', 'de': 'anton' if role in ('head', 'cap') else 'source-sans-3'}[lang]
        self.weight = 900 if lang == 'ja' and role != 'small' else 600 if role == 'small' else None
        self.chunks = chunks(pkg)

    def font(self, ch):
        o = ord(ch)
        for rs, path in self.chunks:
            if any(a <= o <= b for a, b in rs):
                key = (path, self.px, self.weight)
                if key not in _fonts:
                    f = ImageFont.truetype(path, self.px)
                    if self.weight:
                        try: f.set_variation_by_axes([self.weight])
                        except Exception: pass
                    _fonts[key] = f
                return _fonts[key]
        return font(self.px)

    def length(self, d, text):
        return sum(d.textlength(c, font=self.font(c)) for c in text)

    def draw(self, d, xy, text, fill, stroke=0):
        x, y = xy
        for c in text:
            f = self.font(c)
            d.text((x, y), c, fill=fill, font=f, stroke_width=stroke, stroke_fill=(0, 0, 0)); x += d.textlength(c, font=f)


def font(px):
    if px not in _fonts:
        f = next((p for p in FONTS if os.path.exists(p)), None)
        _fonts[px] = ImageFont.truetype(f, px) if f else ImageFont.load_default()
    return _fonts[px]


def ease(x):
    p = min(1, max(0, x)); return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def view_at(p, t, s, e):
    z = p.get('zoom')
    if z:
        k = ease((t - z['s']) / max(0.1, z['e'] - z['s']))
        return [v + (w - v) * k for v, w in zip(p['view'], z['to'])]
    if not p.get('drift'): return p['view']
    k = min(1, max(0, (t - s) / max(0.5, e - s))) * p['drift'] / 2
    a, b, c, d = p['view']; w, h = c - a, d - b
    return [a + w * k, b + h * k, c - w * k, d - h * k]


def centred(d, y, text, face, fill, stroke=0, max_w=None):
    while max_w and face.length(d, text) > max_w and face.px > 20:
        face = Face(face.lang, face.role, face.px - 4)
    face.draw(d, ((1080 - face.length(d, text)) / 2, y), text, fill, stroke)


def wrap(d, text, face, max_w):
    """Rows of a caption as the browser wraps it (between words; Japanese anywhere)."""
    if face.length(d, text) <= max_w: return [text]
    sep = ' ' if ' ' in text else ''
    parts = text.split(' ') if sep else list(text)
    rows, cur = [], ''
    for p in parts:
        nxt = cur + (sep if cur else '') + p
        if cur and face.length(d, nxt) > max_w: rows.append(cur); cur = p
        else: cur = nxt
    return rows + [cur]


def draw(plan, shot, t, cap, img_of):
    """Full 1080×1920 frame of `shot` at time t. img_of(src) → PIL image of a prepared picture."""
    lang = plan.get('lang', 'ja'); up = (lambda s: s.upper()) if lang == 'de' else (lambda s: s)
    im = Image.new('RGB', (1080, 1920), (8, 8, 8)); d = ImageDraw.Draw(im)
    if plan.get('title'): centred(d, L.TITLE_Y, up(plan['title']), Face(lang, 'head', plan['titleSize']), (245, 239, 227), max_w=1040)
    d.rectangle((480, L.LABEL_Y - 18, 600, L.LABEL_Y - 14), fill=RED)
    if shot['label']: centred(d, L.LABEL_Y, up(shot['label']), Face(lang, 'small', 36), (189, 180, 164), max_w=1040)
    p = shot['pic']; x, y, w, h = p['box']; v = view_at(p, t, shot['s'], shot['e']); src = img_of(p['src'])
    sw, sh = src.size
    reg = src.crop((round(v[0] * sw), round(v[1] * sh), round(v[2] * sw), round(v[3] * sh))).resize((round(w), round(h)), Image.LANCZOS)
    im.paste(reg, (round(x), round(y)))
    for mk in shot['marks']:
        if t < mk['s']: continue
        X = lambda f: x + (f - v[0]) / (v[2] - v[0]) * w; Y = lambda f: y + (f - v[1]) / (v[3] - v[1]) * h
        a, bb, c, e = mk['box']
        (d.rectangle if mk.get('shape') == 'rect' else d.ellipse)((X(a), Y(bb), X(c), Y(e)), outline=RED, width=7)
    if shot.get('ai'):
        f = Face(lang, 'small', 26); tag = plan.get('aiTag', 'AI'); tw = f.length(d, tag)
        d.rectangle((x + w - 18 - tw - 28, y + 18, x + w - 18, y + 18 + 44), fill=(30, 30, 30))
        f.draw(d, (x + w - 18 - tw - 14, y + 24), tag, (235, 235, 235))
    if cap:
        f = Face(lang, 'cap', L.CAP[lang]); rows = wrap(d, up(cap), f, L.CAP_W)
        for k, row in enumerate(rows):
            centred(d, L.CAP_Y + k * L.CAP[lang] * 1.12, row, f, YELLOW, stroke=7)
    if shot['credit']: Face(lang, 'small', 24).draw(d, (L.SIDE + 6, L.CREDIT_Y), shot['credit'][:90], (170, 164, 154))
    return im
