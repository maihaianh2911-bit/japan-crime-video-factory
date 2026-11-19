#!/usr/bin/env python3
"""Crop, size and age the pictures chosen in picks.json. Usage: prep.py <picks.json> <img_root> <out_dir>

picks.json "images": {"<name>": {"src": "<round>/<file>" (picture search or AI illustration) or "own/<file>"
(crime/<N>/own/), "rotate": 90 | -90 | 180 (optional, before the crop), "crop": [x0, y0, x1, y1] (0..1, optional:
removes borders, captions, watermarks), "look": "print" (default: the evidence photograph of the owner's sample —
black and white, hard contrast, deep blacks, grain) | "aged" (an old colour print: faded warm colours, dust,
scratches) | "aged-bw" (an old faded black-and-white print) | "clean" (true colours, for documents, maps and scans
that must stay readable) | "color" (true colours, a touch more contrast and colour: the photos of picks.json
"tone": "normal", whose default it is — owner, 19/11/2026: "Để bình thường đi, ko cần làm tối om thế đâu"),
"blur": [[x0, y0, x1, y1], …] (optional: faces or details to blur — children, uninvolved people, names)}}
→ <out_dir>/<name>.jpg. The ageing is seeded by the name, so a picture looks the same in every render.
"""
import json, os, sys, zlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFilter


def age(im, seed, bw=False):
    """Old photographic print, as the sample: lifted blacks, softened whites, warm cast, lower saturation, a soft
    vignette, film grain, dust specks and two or three fine scratches."""
    rng = np.random.RandomState(seed)
    W, H = im.size
    a = np.asarray(im).astype(np.float32) / 255
    l = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    if bw:
        a = np.repeat(l[..., None], 3, axis=2) * np.array([1.0, 0.97, 0.9])
    else:
        a = l[..., None] + (a - l[..., None]) * 0.72                      # less saturated
        a = a * np.array([1.07, 1.0, 0.82]) + np.array([0.025, 0.012, 0.0])  # warm, slightly yellowed
    a = 0.07 + a * 0.86                                                   # faded: lifted blacks, softer whites
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a *= (1 - 0.4 * np.clip(r - 0.5, 0, None) ** 1.5)[..., None]          # vignette
    # uneven fading: a large soft blotch of lighter / warmer tone
    k = max(8, W // 40)
    blot = Image.fromarray((rng.rand(H // k + 2, W // k + 2) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(k * 3))
    b = np.asarray(blot).astype(np.float32) / 255 - 0.5
    a += b[..., None] * np.array([0.07, 0.055, 0.03])
    a += rng.normal(0, 0.028, (H, W))[..., None]                           # grain
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(out, 'RGBA')
    s = max(W, H) / 1400
    for _ in range(int(rng.randint(60, 120) * (W * H) / 2e6) + 25):        # dust: small light and dark specks
        x, y, rad = rng.rand() * W, rng.rand() * H, (0.6 + rng.rand() ** 3 * 3.2) * s
        light = rng.rand() < 0.75
        col = (245, 240, 228, int(120 + rng.rand() * 110)) if light else (30, 22, 15, int(90 + rng.rand() * 100))
        d.ellipse((x - rad, y - rad * (0.6 + rng.rand() * 0.8), x + rad, y + rad), fill=col)
    for _ in range(rng.randint(1, 4)):                                     # fine scratches
        x0, y0 = rng.rand() * W, rng.rand() * H
        pts = [(x0, y0)]
        for _ in range(6):
            x0 += (rng.rand() - 0.5) * 40 * s; y0 += (0.5 + rng.rand()) * 60 * s * (1 if rng.rand() < 0.5 else -1)
            pts.append((x0, y0))
        d.line(pts, fill=(238, 232, 220, int(60 + rng.rand() * 70)), width=max(1, int(1.2 * s)))
    return out.filter(ImageFilter.GaussianBlur(0.35 * s))


def print_look(im, seed):
    """Evidence photograph of the sample: black and white, an S-curve (deep blacks, bright highlights), a soft dark
    vignette and fine grain."""
    rng = np.random.RandomState(seed)
    W, H = im.size
    a = np.asarray(im).astype(np.float32) / 255
    l = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    lo, hi = np.percentile(l, 1.5), np.percentile(l, 99.2)
    l = np.clip((l - lo) / max(0.05, hi - lo), 0, 1)
    l = l * l * (3 - 2 * l)                                                # S-curve
    l = 0.6 * l + 0.4 * l ** 1.25                                          # a little darker in the mids
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    l *= 1 - 0.45 * np.clip(r - 0.55, 0, None) ** 1.4
    l += rng.normal(0, 0.035, (H, W))
    a = np.clip(l, 0, 1)[..., None] * np.array([1.0, 0.99, 0.965]) + np.array([0.012, 0.012, 0.012])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.3 * max(W, H) / 1400))


def prepare(it, root, name='x', default='print'):
    """One picture of picks.json "images", cropped, blurred where asked and aged (PIL image)."""
    im = Image.open(os.path.join(root, it['src'])).convert('RGB')
    if it.get('rotate'):
        im = im.rotate(it['rotate'], expand=True)
    if it.get('crop'):
        x0, y0, x1, y1 = it['crop']; W, H = im.size
        im = im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    for x0, y0, x1, y1 in it.get('blur') or []:   # faces of children / uninvolved people, names
        W, H = im.size; box = (round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H))
        reg = im.crop(box); rad = max(8, (box[2] - box[0]) // 6)
        im.paste(reg.resize((max(1, reg.width // rad), max(1, reg.height // rad))).resize(reg.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(rad / 2)), box)
    W, H = im.size
    if max(W, H) < 1500:   # small sources are enlarged here so the browser never scales them up
        k = 1500 / max(W, H); im = im.resize((round(W * k), round(H * k)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=50, threshold=2))
    if max(im.size) > 2600:
        k = 2600 / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    look = it.get('look', default)
    if look == 'clean':
        return im
    if look == 'color':
        from PIL import ImageEnhance
        return ImageEnhance.Color(ImageEnhance.Contrast(im).enhance(1.06)).enhance(1.06)
    if look == 'print':
        return print_look(im, zlib.crc32(name.encode()))
    return age(im, zlib.crc32(name.encode()), bw=look == 'aged-bw')


if __name__ == '__main__':
    picks, root, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    pk = json.load(open(picks, encoding='utf-8'))
    deep = bool((pk.get('fx') or {}).get('depth'))   # owner 18/11/2026: the picture effects of japan-news
    default = 'color' if pk.get('tone') == 'normal' else 'print'
    for name, it in pk['images'].items():
        im = prepare(it, root, name, default)
        im.save(os.path.join(out, f'{name}.jpg'), quality=92)
        print(name, im.size)
        # depth for the 2.5D effect: not on documents, scans, maps ("look": "clean") nor where Claude said "depth": false
        if deep and it.get('depth', it.get('look') != 'clean'):
            try:
                import depth
                depth.parallax_map(im).save(os.path.join(out, f'{name}.depth.png'))
            except Exception as e:
                print(f'warning: depth effect off for {name}: {type(e).__name__}: {str(e)[:120]}')
