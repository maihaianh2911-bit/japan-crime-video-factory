"""Draw one frame of a plan shot with PIL, laid out as CrimeV (same boxes from layout.py), for the framing preview.
Text uses the video's own fonts when FONTSOURCE holds them (scripts/crime/get_fonts.sh), else a local font; positions,
picture regions, rings, zooms, drifts, the caption and the AI tag are exact. Text is placed as the browser places it
(CrimeV.tsx): the same font size, line height, letter spacing and weight, the font's ascent + descent centred in the
CSS line box, and German captions slanted (skewX -7°) like the video's."""
import math, os, re
from PIL import Image, ImageDraw, ImageFont
import layout as L

FONTS = ['/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
         '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']
YELLOW, RED = (255, 200, 30), (217, 42, 28)
TITLE_C, LABEL_C, CREDIT_C = (245, 239, 227), (189, 180, 164), (141, 136, 128)   # credit: rgba(200,192,180,.7) on black
SKEW = math.tan(math.radians(7))    # German captions: skewX(-7deg) around 40 % of the caption block's height
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
    font. role: head | cap | small; spacing: CSS letter-spacing in em; weight: of a variable font (small text)."""
    def __init__(self, lang, role, px, spacing=0.0, weight=None):
        self.px, self.lang, self.role = px, lang, role
        pkg = {'ja': 'noto-sans-jp', 'de': 'anton' if role in ('head', 'cap') else 'source-sans-3'}[lang]
        self.weight = weight or (900 if lang == 'ja' and role != 'small' else 600 if role == 'small' else None)
        self.sp = spacing * px
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
        """Advance width as the browser measures it: letter spacing after every character, the last one too."""
        return sum(d.textlength(c, font=self.font(c)) + self.sp for c in text)

    def baseline(self, top, line_height=None):
        """Baseline of a CSS line box of this line-height (em; None = normal) whose top is at `top`: the browser
        centres the font's ascent + descent in the box."""
        f = self.font('A')
        asc, desc = f.getmetrics() if hasattr(f, 'getmetrics') else (self.px * 0.9, self.px * 0.25)
        lh = asc + desc if line_height is None else line_height * self.px
        return top + (lh - asc - desc) / 2 + asc

    def draw(self, d, xy, text, fill, stroke=0):
        """Draw text with its left end at x and its baseline at y."""
        x, y = xy
        for c in text:
            f = self.font(c)
            d.text((x, y), c, fill=fill, font=f, anchor='ls', stroke_width=stroke, stroke_fill=(0, 0, 0))
            x += d.textlength(c, font=f) + self.sp


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


def centred(d, top, line_height, text, face, fill, stroke=0):
    """One centred row in a CSS line box (top, line-height in em), not shrunk: a title or label too wide for the
    frame is cut off in the preview as it is in the video."""
    face.draw(d, ((1080 - face.length(d, text)) / 2, face.baseline(top, line_height)), text, fill, stroke)


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
    lang = plan.get('lang', 'ja'); de = lang == 'de'; up = (lambda s: s.upper()) if de else (lambda s: s)
    im = Image.new('RGB', (1080, 1920), (8, 8, 8)); d = ImageDraw.Draw(im)
    if plan.get('title'):
        centred(d, L.TITLE_Y, 1.18, up(plan['title']), Face(lang, 'head', plan['titleSize'], 0.02 if de else 0.04), TITLE_C)
    d.rectangle((480, L.LABEL_Y - 18, 599, L.LABEL_Y - 15), fill=RED)
    if shot['label']: centred(d, L.LABEL_Y, 1.25, up(shot['label']), Face(lang, 'small', 36, 0.12 if de else 0.06), LABEL_C)
    p = shot['pic']; x, y, w, h = p['box']; v = view_at(p, t, shot['s'], shot['e']); src = img_of(p['src'])
    sw, sh = src.size
    reg = src.crop((round(v[0] * sw), round(v[1] * sh), round(v[2] * sw), round(v[3] * sh))).resize((round(w), round(h)), Image.LANCZOS)
    im.paste(reg, (round(x), round(y)))
    for mk in shot['marks']:
        if t < mk['s']: continue
        X = lambda f: x + (f - v[0]) / (v[2] - v[0]) * w; Y = lambda f: y + (f - v[1]) / (v[3] - v[1]) * h
        a, bb, c, e = mk['box']
        (d.rectangle if mk.get('shape') == 'rect' else d.ellipse)((X(a), Y(bb), X(c), Y(e)), outline=RED, width=7)
    if shot.get('ai'):   # top right of the photograph: padding 6/14 px, rgba(0,0,0,.55) under the tag
        f = Face(lang, 'small', 26, 0.03); tag = plan.get('aiTag', 'AI'); tw = f.length(d, tag)
        a, b = f.font('A').getmetrics() if hasattr(f.font('A'), 'getmetrics') else (24, 8)
        bx = (round(x + w - 18 - tw - 28), round(y + 18), round(x + w - 18), round(y + 18 + a + b + 12))
        im.paste(Image.blend(im.crop(bx), Image.new('RGB', (bx[2] - bx[0], bx[3] - bx[1])), 0.55), bx[:2])
        f.draw(d, (bx[0] + 14, bx[1] + 6 + a), tag, (235, 235, 235))
    if cap:   # rows of the caption block (line-height 1.12), outline: the outer half of the 12 / 10 px stroke
        px = L.CAP[lang]; f = Face(lang, 'cap', px, 0.01 if de else 0.02); rows = wrap(d, up(cap), f, L.CAP_W)
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        for k, row in enumerate(rows):
            centred(ld, L.CAP_Y + k * px * 1.12, 1.12, row, f, YELLOW, stroke=5 if de else 6)
        if de:   # skewX(-7deg) around (540, 40 % of the block): the top leans right
            oy = L.CAP_Y + 0.4 * len(rows) * px * 1.12
            layer = layer.transform(im.size, Image.AFFINE, (1, SKEW, -SKEW * oy, 0, 1, 0), resample=Image.BICUBIC)
        im.paste(layer, (0, 0), layer)
    if shot['credit']:   # one row, cut with … where the video's ellipsis cuts it
        f = Face(lang, 'small', 24, 0.04, weight=400); txt = shot['credit']; room = 1080 - 2 * (L.SIDE + 6)
        if f.length(d, txt) > room:
            while txt and f.length(d, txt + '…') > room: txt = txt[:-1]
            txt += '…'
        f.draw(d, (L.SIDE + 6, f.baseline(L.CREDIT_Y, 1.3)), txt, CREDIT_C)
    return im
