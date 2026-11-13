"""Frame layout of a crime video, shared by build.py (the plan rendered by src/crime/CrimeV.tsx) and preview.py.

Measured on the owner's sample 00-video-mau/MAU-VU-AN.mp4 (576×1024, scaled ×1.875 to 1080×1920): black frame,
one old photograph almost the full width (portrait 3:4, y ≈ 225–1690), short yellow captions of 2–3 words in the
lower part of the photograph (centre y ≈ 1365). The owner asked (13/11/2026) for the case title on top for the whole
video: it sits in the black band above the photograph, with a small per-shot label (place, date, kind of document)
under it. The credit and, on AI illustrations, the tag sit at the foot of the photograph. Pixels of 1080×1920.
"""
W, H = 1080, 1920
SIDE = 24                    # left/right margin of the photograph
PIC_W = W - 2 * SIDE         # 1032
PIC_Y, PIC_H = 282, 1376     # 3:4 photograph: y 282 → 1658
PIC_CY = PIC_Y + PIC_H / 2
TITLE_Y = 66                 # top of the title row
TITLE_BOX = 1000             # the title stays on one row inside this width
LABEL_Y = 196                # per-shot label under the title
CAP_Y = 1310                 # top of the caption block (sample: glyph centres at ~71 % of the height)
CAP_W = 940                  # captions wrap to a second row beyond this width
CREDIT_Y = 1676
TITLE = {'ja': 78, 'de': 92}           # px, Noto Sans JP black / Anton
CAP = {'ja': 78, 'de': 86}            # the sample's caption: cap height ≈ 2.6 % of the frame


def title_size(title, lang):
    """Largest size ≤ the default that keeps the title on one row (full-width characters count 1, others ~0.5)."""
    if lang == 'ja':
        n = sum(0.55 if ord(c) < 0x2000 else 1.0 for c in (title or ''))
        k = 1.02
    else:   # Anton capitals are narrow: ~0.47 em per character, ~0.25 em per space
        n = sum(0.25 if c == ' ' else 0.47 for c in (title or '').upper())
        k = 1.0
    return int(min(TITLE[lang], TITLE_BOX / max(1.0, n * k)))


def pic_box(aspect, fit='cover'):
    """Box [x, y, w, h] of the photograph. 'cover' (default): always the 3:4 photograph of the sample, the view is
    cropped to it. 'contain': a landscape document keeps its shape (full width, centred on the same height)."""
    if fit == 'contain' and aspect > PIC_W / PIC_H:
        h = PIC_W / aspect
        return [SIDE, round(PIC_CY - h / 2, 1), PIC_W, round(h, 1)]
    return [SIDE, PIC_Y, PIC_W, PIC_H]


def fit_view(view, aspect_px, img_w, img_h):
    """Grow view [x0, y0, x1, y1] (fractions of the picture) around its centre to the box aspect (w/h in pixels),
    then shift/shrink it to stay inside the picture."""
    x0, y0, x1, y1 = view
    vw, vh = (x1 - x0) * img_w, (y1 - y0) * img_h
    if vw / vh < aspect_px: vw = vh * aspect_px
    else: vh = vw / aspect_px
    if vw > img_w: vw = img_w; vh = vw / aspect_px
    if vh > img_h: vh = img_h; vw = vh * aspect_px
    cx, cy = (x0 + x1) / 2 * img_w, (y0 + y1) / 2 * img_h
    cx = min(img_w - vw / 2, max(vw / 2, cx)); cy = min(img_h - vh / 2, max(vh / 2, cy))
    return [round((cx - vw / 2) / img_w, 5), round((cy - vh / 2) / img_h, 5), round((cx + vw / 2) / img_w, 5), round((cy + vh / 2) / img_h, 5)]
