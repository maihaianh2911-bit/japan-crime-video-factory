#!/usr/bin/env python3
"""Unit checks of the crime pipeline without network: caption chunks in both languages, caption timing from word
times, the AI illustration step with a fake generator, and the pipeline's safety nets (calling Claude, paid voice,
picture sources). Run from the repo root: python3 tests/crime_units.py"""
import copy, json, os, re, sys, tempfile, io
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
# wake_claude.sh with a fake curl and gh: three tries, the result word, a comment for the owner only when Claude could
# not be called, and nothing at all while a Claude chat holds the issue (crime-busy added less than 2 hours ago)
import subprocess, datetime, stat
fb = tempfile.mkdtemp(prefix='crime-units-bin-')
open(os.path.join(fb, 'curl'), 'w').write(r"""#!/usr/bin/env bash
n=$(cat "$FAKE_DIR/curl_n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$FAKE_DIR/curl_n"
while [ $# -gt 0 ]; do [ "$1" = -o ] && echo '{"claude_code_session_url": "https://example.invalid/s"}' > "$2"; shift; done
set -- $FAKE_CODES; [ $n -le $# ] && shift $((n - 1)); printf '%s' "$1"
""")
open(os.path.join(fb, 'gh'), 'w').write(r"""#!/usr/bin/env bash
echo "$*" >> "$FAKE_DIR/gh_log"
case "$*" in *"/events"*) echo "$FAKE_BUSY_AT" ;; *"-X POST"*) ;; *) printf '%s\n' $FAKE_LABELS ;; esac
""")
for f in ('curl', 'gh'): os.chmod(os.path.join(fb, f), os.stat(os.path.join(fb, f)).st_mode | stat.S_IEXEC)
def wake_sh(codes='200', secrets=True, issue='7', labels='crime crime-pick', busy_at=''):
    fd = tempfile.mkdtemp(prefix='crime-units-wake-')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('CLAUDE_TASK', 'GITHUB_', 'GH_'))}
    env.update(PATH=fb + os.pathsep + env['PATH'], FAKE_DIR=fd, FAKE_CODES=codes, FAKE_LABELS=labels, FAKE_BUSY_AT=busy_at,
               WAKE_RESULT=os.path.join(fd, 'result'), WAKE_BACKOFF='0', GH_TOKEN='x', GH_REPO='o/r')
    if secrets: env.update(CLAUDE_TASK_URL='https://example.invalid/fire', CLAUDE_TASK_TOKEN='t')
    r = subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'wake_claude.sh'), 'Phiếu vụ án số 7: thử.'] + ([issue] if issue else []),
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    read = lambda f: open(os.path.join(fd, f), encoding='utf-8').read() if os.path.exists(os.path.join(fd, f)) else ''
    return read('result').strip(), int(read('curl_n') or 0), read('gh_log')
ago = lambda h: (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')
res, n, log = wake_sh('503 000 200'); assert (res, n) == ('ok', 3) and 'POST' not in log, (res, n, log)
res, n, log = wake_sh('503 503 503'); assert (res, n) == ('failed', 3) and 'issues/7/comments' in log and '🤖' in log and 'wake.yml' in log, (res, n, log)
res, n, log = wake_sh('401'); assert (res, n) == ('failed', 1) and 'issues/7/comments' in log, (res, n, log)       # a refused key is not retried
res, n, log = wake_sh(secrets=False); assert (res, n) == ('failed', 0) and 'CLAUDE_TASK_URL' in log, (res, n, log)
res, n, log = wake_sh(secrets=False, issue=''); assert (res, n, log) == ('failed', 0, ''), (res, n, log)              # the button: nothing to comment on
res, n, log = wake_sh(labels='crime crime-busy', busy_at=ago(1)); assert (res, n) == ('busy', 0) and 'POST' not in log, (res, n, log)
res, n, log = wake_sh(secrets=False, labels='crime crime-busy', busy_at=ago(1)); assert res == 'busy' and 'POST' not in log, (res, log)
res, n, log = wake_sh(labels='crime crime-busy', busy_at=ago(3)); assert (res, n) == ('ok', 1), (res, n, log)        # a stale claim does not count
res, n, log = wake_sh(labels='crime', busy_at=ago(1)); assert (res, n) == ('ok', 1), (res, n, log)                   # label removed: free
# 11labs client: GET retried on a busy server, the create POST only when refused outright (429), never after a 5xx;
# the balance around a paid job is information only
import urllib.error, argparse
import vn11 as V, tts_lines as T, ff
class _Resp:
    status = 200
    def __init__(self, body): self.body = body
    def read(self): return self.body
    def __enter__(self): return self
    def __exit__(self, *a): return False
def fake_api(seq):
    n = [0]
    def urlopen(r, timeout=None):
        x = seq[min(n[0], len(seq) - 1)]; n[0] += 1
        if isinstance(x, int): raise urllib.error.HTTPError(r.full_url, x, 'x', {}, io.BytesIO(b'{"error": "busy"}'))
        return _Resp(json.dumps(x).encode())
    V.urllib.request.urlopen = urlopen
    return n
real_urlopen, real_sleep = V.urllib.request.urlopen, V.time.sleep
V.time.sleep = lambda s: None
try:
    n = fake_api([502, 429, {'ok': 1}]); assert V.req('GET', 'status.php') == (200, {'ok': 1}) and n[0] == 3
    n = fake_api([429, {'job_id': 'j'}]); assert V.req('POST', 'tts.php', data=b'{}') == (200, {'job_id': 'j'}) and n[0] == 2
    n = fake_api([502, {'job_id': 'j'}]); assert V.req('POST', 'tts.php', data=b'{}')[0] == 502 and n[0] == 1
    n = fake_api([500]); assert V.cmd_balance(None, soft=True) == {} and n[0] == 4
    try: V.cmd_balance(None); raise AssertionError('a plain balance call must stop on an error')
    except SystemExit: pass
finally:
    V.urllib.request.urlopen, V.time.sleep = real_urlopen, real_sleep

# voice lines: a failure at line 3 leaves lines 1–2 on disk with their rows, and the next run reads only what is missing
vd = tempfile.mkdtemp(prefix='crime-units-voice-')
sj = os.path.join(vd, 'script.json'); json.dump({'voice': 'clone_1', 'lines': ['Eins.', 'Zwei.', 'Drei.', 'Vier.']}, open(sj, 'w'))
jobs = []
def fake_tts(a, fail=()):
    text = open(a.text_file, encoding='utf-8').read(); jobs.append(text)
    if text in fail: V.die('11labs: thử lỗi')
    ff.run('-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.6', os.path.join(a.out, 'voice.mp3'))
real_tts, argv = V.cmd_tts, sys.argv
try:
    V.cmd_tts = lambda a: fake_tts(a, fail=('Drei.',))
    sys.argv = ['tts_lines.py', sj, os.path.join(vd, 'a'), '--prev', os.path.join(vd, 'none')]
    try: T.main(); raise AssertionError('line 3 must stop the run')
    except SystemExit: pass
    part = json.load(open(os.path.join(vd, 'a', 'lines.json')))
    assert [r['i'] for r in part] == [1, 2] and all(os.path.exists(os.path.join(vd, 'a', r['file'])) for r in part), part
    V.cmd_tts = fake_tts; jobs.clear()
    sys.argv = ['tts_lines.py', sj, os.path.join(vd, 'b'), '--prev', os.path.join(vd, 'none'), '--prev', os.path.join(vd, 'a')]
    T.main()
    assert jobs == ['Drei.', 'Vier.'] and [r['i'] for r in json.load(open(os.path.join(vd, 'b', 'lines.json')))] == [1, 2, 3, 4], jobs
finally:
    V.cmd_tts, sys.argv = real_tts, argv
# picture search: a source that answers 429 (Library of Congress on the runners) is asked once per run, not per query
import find_images as F
asked = []
def refused(q, n): asked.append(q); raise urllib.error.HTTPError('https://www.loc.gov/', 429, 'Too Many Requests', {}, None)
real_find = dict(F.FIND)
try:
    F.FIND.update({s: (lambda q, n: []) for s in F.SOURCES}); F.FIND['loc'] = refused; F.REFUSED.clear()
    assert F.search('first') == [] and F.search('second') == [] and asked == ['first'] and F.REFUSED == {'loc'}, asked
finally:
    F.FIND.clear(); F.FIND.update(real_find); F.REFUSED.clear()
# scene edits (the catalogue scripts/crime/edits.py): every recipe builds, a scene without "edit" is left alone, the
# template fills only what Claude left out, an unknown name or a missing item is refused with the names / the recipe,
# the list for the owner marks a repeated edit, and AGENT_CRIME.md documents every name
import edits as E
def refuse(m): raise SystemExit(m)
def refused(sc):
    try: E.apply(sc, 3, refuse)
    except SystemExit as e: return str(e)
    raise AssertionError(f'not refused: {sc}')
agent = open(os.path.join(ROOT, 'AGENT_CRIME.md'), encoding='utf-8').read()
for name in E.names():
    ed = E.EDITS[name]; made = E.apply(ed['recipe'], 1, refuse)
    assert made['edit'] == name and made is not ed['recipe'] and all(ed.get(k) for k in ('vi', 'sample', 'look', 'use')), name
    assert f'`{name}`' in agent and E.recipe(name).replace('|', '¦') in agent, f'AGENT_CRIME.md: edit {name} is missing or its recipe is old (python3 scripts/crime/edits.py)'
plain = {'at': 1, 'items': [{'photo': 'a'}]}
assert E.apply(plain, 1, refuse) is plain and plain == {'at': 1, 'items': [{'photo': 'a'}]}
msg = refused({'at': 1, 'edit': 'nope'}); assert 'cảnh 3' in msg and all(n in msg for n in E.names()), msg
msg = refused({'at': 1, 'edit': 'hook', 'items': []}); assert 'hook' in msg and 'Mẫu' in msg and '"edit": "hook"' in msg, msg
hook = copy.deepcopy(E.EDITS['hook']['recipe']); slot = E.EDITS['hook']['slots']['photo'][0]; key = next(iter(slot))
mine = 'wide' if key == 'pos' else slot[key] + 7
hook['items'][0][key] = mine
made = E.apply(hook, 1, refuse)
assert made['items'][0][key] == mine and all(k in made['items'][1] for k in E.EDITS['hook']['slots']['tag' if 'tag' in E.KINDS else 'tape']['*'][0])
rows = [{'at': 1, 'edit': 'hook', 'why': 'vì câu đầu | liệt kê'}, {'at': '2/x', 'edit': 'hook'}, {'at': 3}]
md = E.listing(rows, {1: 'eins', 2: 'zwei', 3: 'drei'}, [0, 4, 8, 12])
assert E.repeats(rows) == [2] and 'vì câu đầu / liệt kê' in md and '⚠️' in md and '| 3 | 8–12 s | drei | — |' in md and '`ending`' in md, md
# template details: a tag the template placed stays inside the frame (moved inwards, shrunk when wider than the frame),
# a tag Claude placed is left alone; the card of "who" is as high as its rows need unless Claude gave "h"
long_ = {'at': 1, 'edit': 'detail', 'items': [{'photo': 'a', 'marks': [{'box': [0, 0, 1, 1]}]}, {'tag': '関孫六'}, {'tag': '前日に同じ包丁を購入した男'},
                                               {'tag': '前日に同じ包丁を購入して画像解析で特定されたという男', 'color': 'red'}, {'tag': '前日に同じ包丁を購入した男', 'x': 1000, 'y': 300}]}
made = E.apply(long_, 1, refuse)['items']
for it in made[1:4]:
    w_ = E.tag_width(it['tag'], it.get('size', 46)); assert it['x'] - w_ / 2 >= E.MARGIN - 1 and it['x'] + w_ / 2 <= E.W - E.MARGIN + 1, it
assert made[1]['x'] == 300 and made[2]['x'] < 770 and made[3]['size'] < 46 and made[4]['x'] == 1000
who = lambda k, **kw: E.apply({'at': 1, 'edit': 'who', 'items': [{'card': {'head': 'x', 'rows': ['r'] * k}, **kw}]}, 1, refuse)['items'][0]
assert who(2)['h'] < who(4)['h'] < who(6)['h'] and who(4)['h'] == E.card_height({'head': 'x', 'rows': ['r'] * 4}, 60) and who(4, h=900)['h'] == 900
print('crime unit checks OK')
