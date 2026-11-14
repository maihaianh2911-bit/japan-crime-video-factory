"""Textures of the desk of the owner's sample, made once per video (seeded, so every render is the same):
bg.jpg — dark brown wood with fine horizontal grain, lighter in the middle, a heavy vignette (sample: ~RGB 62,55,49
in the centre, ~16,14,12 at the corners); grain.png — a grey noise tile laid over the whole frame (overlay blend)."""
import numpy as np
from PIL import Image, ImageFilter


def desk(path, W=1188, H=2112, seed=7):
    rng = np.random.RandomState(seed)
    # horizontal grain: noise stretched along x, several scales
    g = np.zeros((H, W), np.float32)
    for k, amp in ((90, 0.55), (30, 0.3), (8, 0.15)):
        n = rng.rand(H // 3 + 1, max(2, W // k)).astype(np.float32)
        g += amp * np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255
    g = (g - g.mean()) / (g.std() + 1e-6)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.58)) ** 2)
    light = np.clip(1.05 - 0.75 * r ** 1.6, 0.22, 1.0)
    base = np.array([60, 53, 47], np.float32)
    a = base[None, None, :] * (light * (1 + 0.075 * g))[..., None]
    a += rng.normal(0, 2.0, (H, W, 1))
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)).save(path, quality=90)


def grain(path, S=512, seed=11):
    rng = np.random.RandomState(seed)
    n = np.clip(128 + rng.normal(0, 38, (S, S)), 0, 255).astype(np.uint8)
    Image.fromarray(n, 'L').save(path)
