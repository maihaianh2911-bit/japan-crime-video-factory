#!/usr/bin/env python3
"""Unit checks of the crime pipeline without network: caption chunks in both languages, caption timing from word
times, and the AI illustration step with a fake generator. Run from the repo root: python3 tests/crime_units.py"""
import json, os, re, sys, tempfile, io
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'crime')); sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import captions as C

# Japanese: phrases after particles, names and numbers never cut, no 、。 shown, never a chunk wider than the row,
# never a cut inside a word (思いま|すか, 食べることがで|きなかった) or before a small kana, ー or ？
ja = {'彼女の名前は、アンネリーゼ・ミシェル。': ['彼女の', '名前は', 'アンネリーゼ・ミシェル'],
      '1976年7月1日、彼女は栄養失調で亡くなった。': ['1976年7月1日', '彼女は', '栄養失調で', '亡くなった'],
      'なぜ誰も止めなかったのか？': ['なぜ誰も', '止めなかったのか？'],
      'あなたはどう思いますか？': ['あなたは', 'どう思いますか？'],
      'この少女はいったい誰なのでしょうか？': ['この少女は', 'いったい誰なの', 'でしょうか？'],
      '彼女は何も食べることができなかった。': ['彼女は何も', '食べることが', 'できなかった'],
      'なぜ両親はそんなことをしてしまったのでしょうか？': ['なぜ両親は', 'そんなことを', 'してしまったの', 'でしょうか？'],
      '本当に悪魔はいたのだろうか？': ['本当に', '悪魔はいたの', 'だろうか？'],
      'アンネリーゼ・ミシェルは、1976年に亡くなった。': ['アンネリーゼ・ミシェルは', '1976年に', '亡くなった'],
      'クリンゲンベルク・アム・マインの小さな村で起きた。': ['クリンゲンベルク', 'アム・マインの', '小さな村で', '起きた']}
more = ['自宅の小さな部屋で、悪魔祓いが続けられていた。', '両親と二人の神父は、過失致死罪で起訴された。', 'ちょっと待ってください。',
        '彼女は67回もの悪魔祓いを受けていた。', 'ローマ・カトリック教会は、正式に悪魔祓いを許可した。', 'フランクフルト・アム・マインの裁判所',
        'それは本当に起きたことなのです。', '名古屋妊婦切り裂き殺人事件の真相は、いまも分かっていない。']
for line in list(ja) + more:
    ch = C.chunks(line, 'ja'); got = [s for _, s in ch]
    assert ja.get(line, got) == got, (line, got)
    assert ''.join(sp for sp, _ in ch) == line, ch
    for k, (sp, shown) in enumerate(ch):
        assert C._ja_width(shown) <= C.JA_ROW, (line, got)                                     # one caption row
        assert k == 0 or sp[0] not in C.JA_NO_START, (line, got)                                 # ょ, ー, ？ start nothing
        assert len(ch) == 1 or C._ja_width(shown) >= 2, (line, got)                              # no lone か？ tail
        assert not any(c in shown for c in '、。'), (line, got)
    for (a, _), (b, _) in zip(ch, ch[1:]):
        assert not (C._run(a[-1]) == C._run(b[0]) and C._run(b[0]) in ('kata', 'num')), (line, got)   # 名前 / 数字
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
# German: the dot of an ordinal or an abbreviation is no sentence end, stays on screen, and "1. Juli" stays together
de2 = {'Am 1. Juli 1976 starb sie.': ['Am 1. Juli 1976', 'starb sie'],
       'Sie starb am 1. Juli. Niemand half.': ['Sie starb', 'am 1. Juli', 'Niemand half'],
       'Dr. Müller untersuchte sie.': ['Dr. Müller', 'untersuchte sie'],
       'Sie lebte in St. Pauli.': ['Sie lebte', 'in St. Pauli'],
       'Das zeigt z. B. dieser Brief.': ['Das zeigt z. B.', 'dieser Brief'],
       'Akte Nr. 12 blieb geheim.': ['Akte Nr. 12', 'blieb geheim'],
       'Prof. Dr. Hans Meier sagte aus.': ['Prof. Dr. Hans Meier', 'sagte aus'],
       'Es war der 3. Exorzismus.': ['Es war', 'der 3. Exorzismus'],
       'Sie war 23. Niemand half.': ['Sie war 23', 'Niemand half']}
for line, want in de2.items():
    ch = C.chunks(line, 'de')
    assert [s for _, s in ch] == want, (line, [s for _, s in ch])
    assert ' '.join(sp for sp, _ in ch) == line, ch
got = [s for _, s in C.chunks('Der Prozess dauerte bis zum 21. April 1978.', 'de')]
assert any('21. April' in s for s in got) and not any(s.endswith('21.') for s in got), got
try:   # the voice check spells the same ordinals out (num2words, installed on GitHub)
    import voice_check as VC
    assert VC.words_de('Am 1. Juli starb sie.')[:3] == ['am', 'erste', 'juli']
    assert VC.words_de('Es war der 3. Exorzismus.')[3] == 'dritte' and 'dreiundzwanzig' in VC.words_de('Sie war 23. Niemand half.')
except ImportError as e:
    print('voice check of ordinals skipped:', e)
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
