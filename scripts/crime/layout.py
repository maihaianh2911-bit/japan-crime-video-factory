"""Frame layout of a crime video, shared by build.py (the plan rendered by src/crime/CrimeV.tsx) and the tests.

Measured on the owner's sample 00-video-mau/MAU-VU-AN.mp4 (576×1024, scaled ×1.875 to 1080×1920; the case file of
the Setagaya family murder, 2000): a dark wooden desk (the opening scene on black), on it the evidence of a scene —
black-and-white photographs with a white print border, slightly turned; yellow tape labels written by hand; paper
cards with typed lines; torn-paper titles; red stamps; big numbers — each laid down as the voice names it. A scene
holds 5–15 s, the board pushes in slowly. The voice is shown in a small white subtitle box (black text, a clause at
a time) centred at y ≈ 1588. Pixels of 1080×1920; items are placed by their centre (x, y).
"""
W, H = 1080, 1920
SUB_Y = 1588                 # centre of the subtitle box (sample: 82.7 % of the height)
SUB_MAX_W = 960              # the box wraps beyond this width
SUB_SIZE = {'ja': 40, 'de': 40}
SAFE_TOP, SAFE_BOTTOM = 90, 1500   # items stay between these (app buttons on top, subtitle box below)
PHOTO_BORDER = 12            # white print border, px

# defaults of the items (centre x, y; size)
DEF = {'photo': {'x': 540, 'y': 760, 'w': 760}, 'tag': {'x': 540, 'y': 1250, 'size': 46},
       'header': {'x': 540, 'y': 300, 'size': 64}, 'card': {'x': 540, 'y': 820, 'w': 820, 'h': 980, 'size': 52},
       'stamp': {'x': 700, 'y': 1180, 'size': 52}, 'big': {'x': 540, 'y': 1000, 'size': 160},
       'text': {'x': 540, 'y': 900, 'size': 96}}


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
