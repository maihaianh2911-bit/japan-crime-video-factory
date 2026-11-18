"""Depth of a picture, for the light 2.5D effect of the crime videos (owner, 18/11/2026: the picture effects of
japan-news-video-factory, where the owner switched them on on 17/11/2026).

The depth comes from Depth Anything V2 Small (Apache-2.0; ONNX export of github.com/fabio-sim/Depth-Anything-ONNX), on
the CPU, about a second a picture; the model file is $DEPTH_MODEL or downloaded once to ~/.cache/crime-depth/.
Needs numpy, onnxruntime and opencv-python-headless (imported only when a picture gets depth).

parallax_map() turns the depth into the map CrimeV.tsx gives an SVG feDisplacementMap: red and green hold how far each
pixel moves sideways and up/down when the camera pushes in (things near the camera move outwards more than things far
away, around the depth FOCUS that stays put); 128 = no move. The video then animates the strength of that move over
the scene, so the picture seems to have depth instead of being a flat print zooming.
"""
from functools import lru_cache
import os
from pathlib import Path
from urllib.request import urlretrieve

from PIL import Image

MODEL_URL = 'https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/depth_anything_v2_vits.onnx'
SIDE = 518      # the model's size (a multiple of its 14-pixel patches)
FOCUS = 0.45    # the depth that stays where it is (0 far, 1 near)
MAP = 512       # longest side of the displacement map (it is stretched over the picture; soft, so small is enough)


@lru_cache(maxsize=1)
def session():
    import onnxruntime
    path = Path(os.environ.get('DEPTH_MODEL') or Path.home() / '.cache/crime-depth/depth_anything_v2_vits.onnx')
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(MODEL_URL, f'{path}.part')
        os.replace(f'{path}.part', path)
    return onnxruntime.InferenceSession(str(path), providers=['CPUExecutionProvider'])


def depth_map(image):
    """Relative depth as a float array of the picture's size: 0 far, 1 near, with soft edges."""
    import cv2
    import numpy as np
    px = np.asarray(image.convert('RGB').resize((SIDE, SIDE), Image.Resampling.BICUBIC), dtype=np.float32) / 255
    px = (px - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    m = session()
    d = m.run(None, {m.get_inputs()[0].name: px.transpose(2, 0, 1)[None].astype(np.float32)})[0].squeeze()
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    d = np.clip((d - lo) / max(1e-6, hi - lo), 0, 1).astype(np.float32)
    d = cv2.resize(d, image.size, interpolation=cv2.INTER_CUBIC)
    return cv2.GaussianBlur(d, (0, 0), max(image.size) / 110)


def parallax_map(image):
    """The displacement map (PIL RGB) of a picture: see the module text."""
    import numpy as np
    small = image.copy(); small.thumbnail((MAP, MAP))
    d = depth_map(small)
    h, w = d.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rx, ry = (xx / max(1, w - 1) - 0.5) * 2, (yy / max(1, h - 1) - 0.5) * 2   # -1 … 1 from the centre
    k = d - FOCUS
    # feDisplacementMap takes the pixel from (x + s·(R-0.5), …): to push near things OUTWARDS, sample inwards
    r = np.clip(0.5 - 0.5 * k * rx, 0, 1); g = np.clip(0.5 - 0.5 * k * ry, 0, 1)
    rgb = np.stack([r, g, np.full_like(r, 0.5)], axis=2)
    return Image.fromarray((rgb * 255).round().astype(np.uint8), 'RGB')
