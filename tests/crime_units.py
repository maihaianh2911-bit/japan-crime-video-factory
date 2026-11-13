#!/usr/bin/env python3
"""Unit checks of the crime pipeline without network: caption chunks in both languages, caption timing from word
times, and the AI illustration step with a fake generator. Run from the repo root: python3 tests/crime_units.py"""
import json, os, re, sys, tempfile, io
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'crime')); sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import captions as C

# Japanese: phrases after particles, names and numbers never cut, no 、。 shown
ja = {'彼女の名前は、アンネリーゼ・ミシェル。': ['彼女の', '名前は', 'アンネリーゼ・ミシェル'],
      '1976年7月1日、彼女は栄養失調で亡くなった。': ['1976年7月1日', '彼女は', '栄養失調で', '亡くなった'],
      'なぜ誰も止めなかったのか？': ['なぜ誰も', '止めなかったのか？']}
for line, want in ja.items():
    got = [s for _, s in C.chunks(line, 'ja')]
    assert got == want, (line, got)
    assert ''.join(sp for sp, _ in C.chunks(line, 'ja')) == line
# German: 1–3 words, ≤ 20 characters, ends at punctuation, never on an article or preposition
de = ['Im Jahr 1976 starb in Bayern eine 23-jährige Frau.', 'Zwischen 1975 und 1976 wurden mehr als 60 Exorzismen offiziell genehmigt.',
      'Ihre Eltern und die beiden Priester wurden wegen fahrlässiger Tötung angeklagt.', 'Sie sagte, sie höre ständig Stimmen.', 'Warum hat niemand eingegriffen?']
for line in de:
    ch = C.chunks(line, 'de')
    assert ' '.join(sp for sp, _ in ch) == line, ch
    for sp, shown in ch:
        assert 1 <= len(sp.split()) <= 3 and len(shown) <= 20, ch
        assert not shown.split()[-1].lower() in C.DE_FUNC or shown is ch[-1][1], ch
        assert not re.search(r'[,.;:]$', shown), ch
assert [s for _, s in C.chunks('Sie sagte, sie höre ständig Stimmen.', 'de')][0] == 'Sie sagte'
assert C.chunks('Warum hat niemand eingegriffen?', 'de')[-1][1].endswith('?')
# timing: linear without word times, follows them when present
assert abs(C.time_at(0.5, 4.0) - 2.0) < 1e-9
assert abs(C.time_at(0.5, 4.0, [[0, 0.2], [0.5, 3.0], [1.0, 3.9]]) - 3.0) < 1e-9
assert abs(C.time_at(0.75, 4.0, [[0, 0.2], [0.5, 3.0], [1.0, 3.9]]) - 3.45) < 1e-9

# AI illustrations: a fake generator, one prompt refused, numbering after the search groups, AI flags
import gen_images as G
from PIL import Image
calls = []
def fake(prompt, aspect, seed):
    calls.append((prompt, aspect, seed))
    if 'refuse' in prompt: raise RuntimeError('HTTP 400: refused')
    b = io.BytesIO(); Image.new('RGB', (1024, 1024), (120, 90, 60)).save(b, 'JPEG'); return b.getvalue()
G.PROVIDERS['fake'] = (fake, ())
G.provider = lambda: 'fake'
d = tempfile.mkdtemp(prefix='crime-units-')
json.dump([{'k': 1, 'query': 'x', 'results': []}, {'k': 2, 'query': 'y', 'results': []}], open(os.path.join(d, 'index.json'), 'w'))
spec = os.path.join(d, 'spec.json')
json.dump([{'gen': 'a small bedroom in 1976', 'n': 2}, {'gen': 'please refuse this', 'n': 1}, {'gen': 'a village church', 'aspect': '4:3', 'n': 1}], open(spec, 'w'))
sys.argv = ['gen_images.py', d, '--spec', spec]; G.main()
idx = json.load(open(os.path.join(d, 'index.json')))
assert [g['k'] for g in idx] == [1, 2, 3, 4, 5]
g3, g4, g5 = idx[2:]
assert len(g3['results']) == 2 and all(r['ai'] and r['license'] == 'AI-generated' for r in g3['results']) and g3['ai']
assert g4['error'].startswith('HTTP 400') and not g4['results']
assert Image.open(os.path.join(d, g3['results'][0]['file'])).size == (768, 1024)     # square cropped to 3:4
assert Image.open(os.path.join(d, g5['results'][0]['file'])).size == (1024, 768)     # 4:3
assert os.path.exists(os.path.join(d, 'sheet_3.jpg')) and 'No text' in calls[0][0]
# without any key: recorded as an error, no pictures
G.provider = lambda: None
d2 = tempfile.mkdtemp(prefix='crime-units-'); sys.argv = ['gen_images.py', d2, '--spec', spec]; G.main()
assert all(g.get('error') and not g['results'] for g in json.load(open(os.path.join(d2, 'index.json'))))
print('crime unit checks OK')
