#!/usr/bin/env python3
"""AI illustrations for a crime video, added to a picture-search round. Usage: gen_images.py <round_dir> --spec <file.json>

The spec is a list of {"gen": "<prompt in English>", "n": 2 (variants, 1–4), "aspect": "3:4" (default) | "4:3"
| "1:1"}. Every variant becomes <round_dir>/<k>-<n>.jpg in its own group k, numbered after the groups already in
<round_dir>/index.json (find_images.py runs first), with a contact sheet sheet_<k>.jpg, and is recorded in
index.json with "ai": true, source "ai/<provider>", licence "AI-generated" and the prompt as title, so the video
prints the AI tag on it and the credits say it is an illustration.

The generator (prompts/channel.json "gen_provider", or auto = the first whose key is set):
  openai      OPENAI_API_KEY             gpt-image-1, 1024×1536 / 1536×1024 / 1024×1024, quality medium
  gemini      GEMINI_API_KEY             gemini-2.5-flash-image, aspect ratio as asked
  cloudflare  CF_ACCOUNT_ID + CF_API_TOKEN  Workers AI flux-1-schnell (free daily allowance), square, cropped
Without a key every group is recorded with an "error" (no pictures): the video then uses real pictures only.
A prompt the generator refuses is recorded with its error; the other prompts go on. Stdlib + Pillow.
"""
import base64, io, json, os, sys, time, urllib.error, urllib.request
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_images as fi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUFFIX = ' Photorealistic photograph. No text, no letters, no captions, no watermark, no logo, no border.'
SIZES = {'3:4': (1024, 1536), '4:3': (1536, 1024), '1:1': (1024, 1024)}


def post(url, body, headers, timeout=180):
    r = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', **headers}, method='POST')
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code}: {e.read()[:300].decode("utf-8", "replace")}') from None


def openai(prompt, aspect, seed):
    w, h = SIZES[aspect]
    d = post('https://api.openai.com/v1/images/generations',
             {'model': os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-1'), 'prompt': prompt, 'size': f'{w}x{h}', 'quality': 'medium', 'n': 1},
             {'Authorization': f"Bearer {os.environ['OPENAI_API_KEY']}"})
    return base64.b64decode(d['data'][0]['b64_json'])


def gemini(prompt, aspect, seed):
    model = os.environ.get('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image')
    d = post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
             {'contents': [{'parts': [{'text': prompt}]}],
              'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspect}}},
             {'x-goog-api-key': os.environ['GEMINI_API_KEY']})
    for c in d.get('candidates') or []:
        for p in (c.get('content') or {}).get('parts') or []:
            data = (p.get('inlineData') or p.get('inline_data') or {}).get('data')
            if data:
                return base64.b64decode(data)
    raise RuntimeError('không có ảnh trong câu trả lời: ' + json.dumps(d)[:300])


def cloudflare(prompt, aspect, seed):
    acct = os.environ['CF_ACCOUNT_ID']
    d = post(f'https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/@cf/black-forest-labs/flux-1-schnell',
             {'prompt': prompt[:2048], 'steps': 8, 'seed': seed}, {'Authorization': f"Bearer {os.environ['CF_API_TOKEN']}"})
    img = (d.get('result') or {}).get('image')
    if not img:
        raise RuntimeError('không có ảnh trong câu trả lời: ' + json.dumps(d)[:300])
    return base64.b64decode(img)


PROVIDERS = {'openai': (openai, ('OPENAI_API_KEY',)), 'gemini': (gemini, ('GEMINI_API_KEY',)),
             'cloudflare': (cloudflare, ('CF_ACCOUNT_ID', 'CF_API_TOKEN'))}


def provider():
    want = json.load(open(os.path.join(ROOT, 'prompts', 'channel.json'), encoding='utf-8')).get('gen_provider', 'auto')
    names = list(PROVIDERS) if want in ('', 'auto') else [want]
    for n in names:
        if n in PROVIDERS and all(os.environ.get(k) for k in PROVIDERS[n][1]):
            return n
    return None


def to_aspect(im, aspect):
    """Centre crop to the asked aspect (flux on Workers AI only makes squares)."""
    a, b = map(int, aspect.split(':')); want = a / b
    W, H = im.size
    if abs(W / H - want) < 0.02:
        return im
    if W / H > want:
        w = round(H * want); return im.crop(((W - w) // 2, 0, (W - w) // 2 + w, H))
    h = round(W / want); return im.crop((0, (H - h) // 2, W, (H - h) // 2 + h))


def main():
    out, spec = sys.argv[1], json.load(open(sys.argv[sys.argv.index('--spec') + 1], encoding='utf-8'))
    os.makedirs(out, exist_ok=True)
    ip = os.path.join(out, 'index.json')
    index = json.load(open(ip, encoding='utf-8')) if os.path.exists(ip) else []
    k0 = max([g['k'] for g in index] or [0])
    name = provider()
    fn = PROVIDERS[name][0] if name else None
    made = 0
    for j, g in enumerate(spec, 1):
        k = k0 + j
        aspect = g.get('aspect', '3:4') if g.get('aspect', '3:4') in SIZES else '3:4'
        prompt = g['gen'].strip().rstrip('.') + '.' + SUFFIX
        group = {'k': k, 'query': f"gen: {g['gen']}", 'ai': True, 'results': []}
        if not fn:
            group['error'] = 'chưa có khóa tạo ảnh AI (OPENAI_API_KEY, GEMINI_API_KEY hoặc CF_ACCOUNT_ID + CF_API_TOKEN)'
            index.append(group); print(f'{k}. gen: no key'); continue
        files, labels, errs = [], {}, []
        for n in range(1, max(1, min(4, int(g.get('n', 2)))) + 1):
            seed = 1000 * k + n
            try:
                raw = None
                for t in range(3):   # rate limits and busy servers
                    try: raw = fn(prompt, aspect, seed); break
                    except RuntimeError as e:
                        if t < 2 and any(c in str(e) for c in ('HTTP 429', 'HTTP 500', 'HTTP 502', 'HTTP 503')): time.sleep(15 * (t + 1)); continue
                        raise
                im = to_aspect(Image.open(io.BytesIO(raw)).convert('RGB'), aspect)
            except Exception as e:
                errs.append(str(e)[:200]); print(f'{k}-{n}: {str(e)[:200]}'); continue
            p = f'{out}/{k}-{len(files) + 1}.jpg'; im.save(p, quality=92)
            group['results'].append({'source': f'ai/{name}', 'title': g['gen'][:160], 'page': '', 'license': 'AI-generated',
                                     'artist': f'AI ({name})', 'date': '', 'description': prompt[:300], 'width': im.width,
                                     'height': im.height, 'ai': True, 'file': os.path.basename(p)})
            files.append(p); labels[p] = f'#{len(files)}  {im.width}x{im.height}  AI\nai/{name}'
            made += 1
        if errs and not files: group['error'] = errs[0]
        fi.sheet(files, f'{out}/sheet_{k}.jpg', labels)
        index.append(group)
        print(f"{k}. gen ({name}): {len(files)} made" + (f', {len(errs)} failed' if errs else ''))
    json.dump(index, open(ip, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{made} AI illustrations')


if __name__ == '__main__':
    main()
