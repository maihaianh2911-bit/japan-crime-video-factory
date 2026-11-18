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
# picture search: an archive that answers 429 (too many requests) is asked once per run, not per query
import contextlib
import find_images as F
asked = []
def refused(q, n): asked.append(q); raise urllib.error.HTTPError('https://api.openverse.org/', 429, 'Too Many Requests', {}, None)
real_find = dict(F.FIND)
try:
    assert 'loc' not in F.SOURCES and 'loc' in F.FIND                                   # the Library of Congress only when asked for by name
    F.FIND.update({s: (lambda q, n: []) for s in F.SOURCES}); F.FIND['openverse'] = refused; F.REFUSED.clear()
    assert F.search('first') == [] and F.search('second') == [] and asked == ['first'] and F.REFUSED == {'openverse'}, asked
    # every archive failing is an error of the query, not "nothing found"
    F.REFUSED.clear(); F.FIND.update({s: refused for s in F.SOURCES})
    try: F.search('third'); raise AssertionError('search with every archive down must fail')
    except RuntimeError: pass
    # results of several archives are mixed one from each in turn, and know their place in their archive (the ranking uses it)
    F.REFUSED.clear(); F.FIND.update({s: (lambda q, n, s=s: [{'source': s, 'i': i} for i in range(2)]) for s in F.SOURCES})
    mixed = F.search('fourth')
    assert [(r['source'], r['rank']) for r in mixed] == [(s, i) for i in range(2) for s in F.SOURCES], mixed
    # a ranked query asks every archive for more than it keeps
    depth = []
    F.FIND.update({s: (lambda q, n: depth.append(n) or []) for s in F.SOURCES})
    F.search('fifth'); F.search('sixth', deep=True)
    assert depth == [8] * len(F.SOURCES) + [F.DEEP] * len(F.SOURCES), depth
    # a prefix asks one source; wiki: and geo: are sources too
    assert F.source_of('wiki: 三億円事件') == ('wiki', '三億円事件') and F.source_of('geo: 35.68,139.47 800')[0] == 'geo'
    assert F.source_of('commons: incategory:"Fuchu Prison"') == ('commons', 'incategory:"Fuchu Prison"')
    assert F.source_of('Dr. Müller: Akte') == (None, 'Dr. Müller: Akte') and F.source_of('snowy field') == (None, 'snowy field')
finally:
    F.FIND.clear(); F.FIND.update(real_find); F.REFUSED.clear()
# Commons pictures are taken in the standard sizes: the largest up to 1920 px (3840 for an exact file); a file under
# 960 px is taken whole; its 330 px version is the preview; a licence that does not allow the video is left out
def _pg(title, w, h, lic='CC BY-SA 4.0', mime='image/jpeg', i=0):
    name = title[5:].replace(' ', '_')
    small = f'lossy-page1-330px-{name}.jpg' if mime == 'image/tiff' else f'330px-{name}'
    return {'title': title, 'index': i, 'imageinfo': [{'mime': mime, 'width': w, 'height': h, 'descriptionurl': 'https://commons.wikimedia.org/wiki/' + name,
            'url': f'https://upload.wikimedia.org/wikipedia/commons/a/ab/{name}?utm=1',
            'thumburl': (f'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/{name}/{small}' if w > 330 else f'https://upload.wikimedia.org/wikipedia/commons/a/ab/{name}'),
            'extmetadata': {'LicenseShortName': {'value': lic}}}]}
res = F.commons_items([_pg('File:Big.jpg', 5100, 3000, i=1), _pg('File:Mid.jpg', 1400, 900, i=2), _pg('File:Small.jpg', 640, 480, i=3),
                       _pg('File:Tiny.jpg', 300, 300, i=4), _pg('File:Press.jpg', 3000, 2000, lic='All rights reserved', i=5),
                       _pg('File:Map.svg', 800, 600, mime='image/svg+xml', i=6)])
assert [r['title'] for r in res] == ['Big.jpg', 'Mid.jpg', 'Small.jpg', 'Tiny.jpg'], res
assert res[0]['thumb'].endswith('/1920px-Big.jpg') and res[0]['preview'].endswith('/330px-Big.jpg'), res[0]
assert res[1]['thumb'].endswith('/1280px-Mid.jpg') and res[2]['thumb'].endswith('/ab/Small.jpg') and res[2]['preview'].endswith('/330px-Small.jpg'), res[1:3]
assert res[3]['thumb'] == res[3]['preview'] and '?' not in res[3]['thumb'], res[3]
assert F.commons_items([_pg('File:Big.jpg', 5100, 3000)], exact=True)[0]['thumb'].endswith('/3840px-Big.jpg')
# a TIFF scan is taken as its JPEG rendering in a standard size (its thumbnails are called lossy-page1-<width>px-…)
tif = F.commons_items([_pg('File:Scan.tif', 6000, 4000, mime='image/tiff')])[0]
assert tif['thumb'].endswith('/Scan.tif/lossy-page1-1920px-Scan.tif.jpg') and tif['preview'].endswith('/lossy-page1-330px-Scan.tif.jpg'), tif
# a list of titles comes back in the order asked, not in the API's
assert [r['title'] for r in F.commons_items([_pg('File:B.jpg', 2000, 2000), _pg('File:A.jpg', 2000, 2000)], order=['File:A.jpg', 'File:B.jpg'])] == ['A.jpg', 'B.jpg']
assert F.ICON.search('File:Commons-logo.svg') and F.ICON.search('File:Japan location map.jpg') and not F.ICON.search('File:Fuchu Prison wall.jpg')
try: F.geo('府中刑務所', 5); raise AssertionError('geo: without coordinates must be refused')
except ValueError: pass
# wiki: and geo: against a fake Wikipedia / Wikidata / Commons. The Japanese Wikipedia cannot be reached (as in a
# Claude cloud session): the item is then found by its name on Wikidata and the English article is read. Order: the
# item's own picture, the article's pictures (page furniture left out), the Commons category, photos taken there
# (one of a numbered series, none shown already)
import urllib.parse as UP
api_calls = []
def fake_js(url):
    host = UP.urlsplit(url).netloc; p_ = dict(UP.parse_qsl(UP.urlsplit(url).query)); api_calls.append((host, p_))
    if host == 'ja.wikipedia.org': raise urllib.error.URLError('Tunnel connection failed: 403 Forbidden')
    if host == 'en.wikipedia.org' and p_.get('prop') == 'pageprops': return {'query': {'pages': {'-1': {'title': p_['titles'], 'missing': ''}}}}
    if p_.get('action') == 'wbsearchentities': return {'search': [{'id': 'Q4634328'}] if p_['language'] == 'ja' else []}
    if p_.get('action') == 'wbgetentities':
        snak = lambda v: [{'mainsnak': {'datavalue': {'value': v}}}]
        return {'entities': {'Q4634328': {'labels': {'ja': {'value': '三億円事件'}, 'en': {'value': '300 million yen robbery'}}, 'descriptions': {'en': {'value': '1968 robbery'}},
                'claims': {'P18': snak('A.jpg'), 'P373': snak('Cat'), 'P625': snak({'latitude': 35.68611, 'longitude': 139.473})},
                'sitelinks': {'jawiki': {'title': '三億円事件'}, 'enwiki': {'title': '300 million yen robbery'}}}}}
    if host == 'en.wikipedia.org' and p_.get('prop') == 'images':
        return {'query': {'pages': {'1': {'images': [{'title': 'File:B.jpg'}, {'title': 'File:Commons-logo.svg'}, {'title': 'File:A.jpg'}]}}}}
    if p_.get('list') == 'categorymembers':
        return {'query': {'categorymembers': [{'title': 'File:C.jpg'}, {'title': 'File:B.jpg'}] if p_['cmtype'] == 'file' else []}}
    if p_.get('generator') == 'geosearch':
        return {'query': {'pages': {str(i): _pg(t, 2000, 1500) for i, t in enumerate(('File:D 1.jpg', 'File:D 2.jpg', 'File:C.jpg'))}}}
    if host == 'commons.wikimedia.org' and p_.get('titles'):
        return {'query': {'pages': {str(i): _pg(t, 2000, 1500) for i, t in enumerate(reversed(p_['titles'].split('|')))}}}
    raise AssertionError(f'unexpected request: {url}')
real_js = F.js
try:
    F.js = fake_js
    with contextlib.redirect_stdout(io.StringIO()) as said_: got = F.wiki('三億円事件', 60)
    assert [(r['title'], r['source']) for r in got] == [('A.jpg', 'commons/wiki'), ('B.jpg', 'commons/wiki'), ('C.jpg', 'commons/category'), ('D 1.jpg', 'commons/geo')], got
    assert F.WIKI_FOUND['三億円事件'] == {'id': 'Q4634328', 'label': '三億円事件', 'description': '1968 robbery', 'coord': [35.68611, 139.473]}, F.WIKI_FOUND
    assert [h for h, p_ in api_calls if p_.get('prop') in ('pageprops', 'images')] == ['ja.wikipedia.org', 'en.wikipedia.org'] * 2 and 'jawiki' in said_.getvalue(), api_calls
    assert next(p_ for h, p_ in api_calls if p_.get('generator') == 'geosearch')['ggscoord'] == '35.68611|139.473'
    api_calls.clear()
    with contextlib.redirect_stdout(io.StringIO()): F.wiki('Q4634328', 60)               # an item number is taken as it is: nothing is looked up
    assert not any(p_.get('prop') == 'pageprops' or p_.get('action') == 'wbsearchentities' for h, p_ in api_calls), api_calls
    api_calls.clear(); assert [r['title'] for r in F.geo('35.6861,139.473 600', 5)] == ['D 1.jpg', 'C.jpg']
    assert (api_calls[-1][1]['ggscoord'], api_calls[-1][1]['ggsradius']) == ('35.6861|139.473', '600')
    F.geo('35.6861, 139.473', 5); F.geo('-33.86 151.21 99999m', 5)
    assert [p_['ggsradius'] for h, p_ in api_calls[-2:]] == ['500', '10000'] and api_calls[-1][1]['ggscoord'] == '-33.86|151.21', api_calls[-2:]
finally:
    F.js = real_js; F.WIKI_FOUND.clear()
# this channel's Wikipedia is read first by wiki:, then the English one; this repo's own User-Agent; an outside picture
# given by its page only takes the page's og:image (owner 18/11/2026: press photos allowed on this channel)
assert F.LANGS[0] == json.load(open(os.path.join(ROOT, 'prompts', 'channel.json'), encoding='utf-8'))['lang'] and F.LANGS[-1] == 'en', F.LANGS
assert 'japan-crime-video-factory' in F.UA and F.WEB_IMAGES and 'web' in F.FIND
real_pi = F.page_image; F.page_image = lambda page: page + '/photo.jpg'
try: assert F.outside({'page': 'https://example.invalid/news', 'license': '© 新聞'})['thumb'] == 'https://example.invalid/news/photo.jpg'
finally: F.page_image = real_pi
# a whole run without network (fake archives, ranking off): old plain-string queries and {"q", "want", "keep"} entries
# side by side, a failing query and a url-less entry recorded as errors without stopping the others, a picture seen
# under an earlier query not shown again, the index without the working fields
import random
def _jpg(seed, size=(900, 700)):
    rnd = random.Random(seed); im = Image.new('L', (9, 8)); im.putdata([rnd.randrange(256) for _ in range(72)])
    b = io.BytesIO(); im.resize(size, Image.NEAREST).convert('RGB').save(b, 'JPEG'); return b.getvalue()
pics = {f'https://example.invalid/{n}.jpg': _jpg(n) for n in range(1, 12)}
pics['https://example.invalid/small.jpg'] = _jpg(99, (300, 300))
def fake_get(url, tries=4, raw=True, timeout=60):
    if url not in pics: raise urllib.error.URLError('Tunnel connection failed: 403 Forbidden')
    return pics[url]
def fake_src(name, by_query):
    """An archive that answers each query with the pictures listed for it (all of them for "*")."""
    return lambda q, n: [F.item(name, f'{name} {i}', f'https://example.invalid/page/{i}', f'https://example.invalid/{i}.jpg', 'CC BY 4.0', 'A', '1968')
                         for i in by_query.get(q, by_query.get('*', ()))]
def down(q, n): raise urllib.error.URLError('down')
def run_find(spec):
    d_ = tempfile.mkdtemp(prefix='crime-units-find-')
    json.dump(spec, open(os.path.join(d_, 'spec.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    sys.argv = ['find_images.py', os.path.join(d_, 'o'), '--spec', os.path.join(d_, 'spec.json')]
    with contextlib.redirect_stdout(io.StringIO()) as said_: F.main()
    idx_ = json.load(open(os.path.join(d_, 'o', 'index.json'), encoding='utf-8'))
    assert all(os.path.exists(os.path.join(d_, 'o', r['file'])) and not {'preview', 'rank', 'error'} & set(r) for g in idx_ for r in g['results'])
    return idx_, said_.getvalue(), os.path.join(d_, 'o')
titles = lambda g: [r['title'] for r in g['results']]
real_find, real_get, argv, rank_env = dict(F.FIND), F.get, sys.argv, os.environ.get('FIND_RANK')
real_ready, real_scores = F.Clip.__dict__['ready'], F.Clip.__dict__['scores']
try:
    os.environ['FIND_RANK'] = '0'; F.Clip.model, F.Clip.failed = None, False
    F.get = fake_get; F.REFUSED.clear()
    F.FIND.update({s: (lambda q, n: []) for s in F.SOURCES})
    F.FIND.update(commons=fake_src('commons', {'*': (1, 2, 3)}), openverse=fake_src('openverse', {'*': (4, 'small', 'gone')}), met=down,
                  wiki=fake_src('commons/wiki', {'*': (1, 5, 6)}))
    idx_, said_, o_ = run_find(['Fuchu Prison wall', {'q': 'police motorcycle', 'want': 'a white police motorcycle', 'keep': 1}, 'met: nothing',
                                {'q': 'wiki: 三億円事件', 'keep': 2}, {'page': 'https://example.invalid/still', 'title': 'still'},
                                {'url': 'https://example.invalid/6.jpg', 'page': 'https://example.invalid/p', 'title': 'own', 'license': 'CC BY 4.0'}])
    assert [g['query'] for g in idx_] == ['Fuchu Prison wall', 'police motorcycle', 'met: nothing', 'wiki: 三億円事件', 'still', 'own'], idx_
    # query 1: one from each archive in turn; the 300 px file is left out by its size, the dead address is skipped
    assert titles(idx_[0]) == ['commons 1', 'openverse 4', 'commons 2', 'commons 3'] and idx_[0]['candidates'] == 6, idx_[0]
    assert os.path.exists(os.path.join(o_, 'sheet_1.jpg')) and not any('match' in r for g in idx_ for r in g['results'])
    # query 2: every picture it finds was kept under query 1 already → nothing new; its wish is kept in the index
    assert idx_[1]['results'] == [] and idx_[1]['want'] == 'a white police motorcycle' and 'error' not in idx_[1], idx_[1]
    assert 'error' in idx_[2] and not idx_[2]['results']                                  # the archive is down: this query only
    assert titles(idx_[3]) == ['commons/wiki 5', 'commons/wiki 6'], idx_[3]              # "keep": 2; picture 1 was shown before
    assert 'url' in idx_[4]['error'] and not idx_[4]['results'], idx_[4]                  # no "page"-only pictures in this repo
    assert [r['source'] for r in idx_[5]['results']] == ['page'] and idx_[5]['results'][0]['license'] == 'CC BY 4.0', idx_[5]   # an exact picture is kept even if seen
    assert 'ranking off' in said_ and 'dropped: 2 too small, 5 duplicates' in said_, said_
    # the same with the ranking on (a fake scorer in place of CLIP): a query in Japanese keeps the archive's order
    # unless it has an English "want"; a "want" drops what does not show it; an unsuitable picture is left out;
    # wiki: keeps its order and says which item it found
    scored = []
    def fake_scores(cls, images, text):
        scored.append(text)
        return [0.10, 0.35, 0.25][:len(images)], ([0.1, 0.1, 0.3] if text == 'prison wall' else [0.1, 0.1, 0.1])[:len(images)]
    F.Clip.ready, F.Clip.scores = classmethod(lambda cls: True), classmethod(fake_scores)
    F.FIND.update(commons=fake_src('commons', {'府中刑務所': (1, 2, 3), '白バイ': (4, 5, 6), 'prison wall': (7, 8, 9)}), openverse=lambda q, n: [],
                  wiki=fake_src('commons/wiki', {'*': (10, 11)}))
    F.WIKI_FOUND['三億円事件'] = {'id': 'Q1', 'label': '三億円事件', 'description': '1968年の窃盗事件'}
    idx_, said_, o_ = run_find(['府中刑務所', {'q': '白バイ', 'want': 'a white police motorcycle'}, 'prison wall', 'wiki: 三億円事件'])
    assert titles(idx_[0]) == ['commons 1', 'commons 2', 'commons 3'] and 'match' not in idx_[0]['results'][0], idx_[0]
    assert titles(idx_[1]) == ['commons 5', 'commons 6'] and [r['match'] for r in idx_[1]['results']] == [0.35, 0.25], idx_[1]
    assert titles(idx_[2]) == ['commons 8', 'commons 7'], idx_[2]
    assert titles(idx_[3]) == ['commons/wiki 10', 'commons/wiki 11'] and idx_[3]['wikidata']['id'] == 'Q1' and 'match' not in idx_[3]['results'][0], idx_[3]
    assert scored == ['a white police motorcycle', 'prison wall'], scored
    assert '1 not showing what was asked, 1 unsuitable' in said_, said_
finally:
    F.FIND.clear(); F.FIND.update(real_find); F.REFUSED.clear(); F.WIKI_FOUND.clear(); F.get, sys.argv = real_get, argv
    F.Clip.ready, F.Clip.scores, F.Clip.model, F.Clip.failed = real_ready, real_scores, None, False
    if rank_env is None: os.environ.pop('FIND_RANK', None)
    else: os.environ['FIND_RANK'] = rank_env
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
assert who(2)['h'] < who(4)['h'] < who(6)['h'] and who(4)['h'] == E.card_height({'head': 'x', 'rows': ['r'] * 4}, who(4)['size']) and who(4, h=900)['h'] == 900
# who / span: the tag the template placed sits just under the fitted card; board: a tag without its photo is dropped
# with a note, the closing white tag follows the last row of photos
w2, w6 = (E.apply({'at': 1, 'edit': 'who', 'items': [{'card': {'head': 'x', 'rows': ['r'] * k}}, {'tag': 't'}]}, 1, refuse)['items'] for k in (2, 6))
assert w2[1]['y'] == round(w2[0]['y'] + w2[0]['h'] / 2 + 80) < w6[1]['y'] and w2[0]['y'] == w6[0]['y']
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    bd = E.apply({'at': 1, 'edit': 'board', 'items': [{'photo': 'a'}, {'photo': 'b'}, {'photo': 'c'}, {'tag': '1'}, {'tag': '2'}, {'tag': '3'}, {'tag': 'lonely'},
                                                      {'tag': 'own', 'x': 500, 'y': 1300}, {'tag': 'end', 'color': 'white'}]}, 1, refuse)['items']
assert 'lonely' in buf.getvalue() and buf.getvalue().startswith('chú ý') and [i['tag'] for i in bd if 'tag' in i] == ['1', '2', '3', 'own', 'end'] and bd[-1]['y'] == 790 + 145 + 150
# posting caption (caption.txt): the checks, the workflow's to-do for a push of caption.txt alone (no voice, no
# search, no render), and the caption step of run.py (published beside the video, link in a comment)
import caption as CAP, subprocess as sp_
de_ok = 'Der Täter ließ fast alles zurück – nur keinen Namen\nVier Menschen starben. Bis heute fehlt ein Name.\n\n#TrueCrime #Kriminalfall #Ungelöst #Japan #Mordfall #shorts\n\nBildquellen: siehe credits.txt'
ja_ok = '犯人はほぼすべてを残した――名前を除いて\n2000年の大みそか、東京・世田谷で一家4人が殺害された。犯人は今も分かっていない。\n\n#未解決事件 #事件 #世田谷 #日本の事件 #ミステリー #shorts\n\n画像出典: Wikimedia Commons ほか'
assert CAP.problems(de_ok, 'de', 'KI-Illustration', False) == [] and CAP.problems(ja_ok, 'ja', 'イメージ（AI生成）', False) == []
assert any('tiếng Đức' in p for p in CAP.problems(ja_ok, 'de', 'KI-Illustration', False))
assert any('tiếng Nhật' in p for p in CAP.problems(de_ok, 'ja', 'イメージ（AI生成）', False))
assert any('KI-Illustration' in p for p in CAP.problems(de_ok, 'de', 'KI-Illustration', True))
assert CAP.problems(de_ok + '\nEinige Bilder: KI-Illustration', 'de', 'KI-Illustration', True) == []
assert CAP.problems(de_ok.replace('siehe credits.txt', '珈琲牛乳 (CC BY 3.0)'), 'de', 'KI-Illustration', False) == []   # a name in the credit line
assert any('#shorts' in p for p in CAP.problems(de_ok.replace(' #shorts', ''), 'de', 'KI-Illustration', False))
assert any('2000' in p for p in CAP.problems(de_ok + 'x' * 2000, 'de', 'KI-Illustration', False)) and CAP.problems('', 'de', '', False)
wf = open(os.path.join(ROOT, '.github', 'workflows', 'crime.yml'), encoding='utf-8').read()   # no yaml module on the runner
todo_py = wf.split("python3 -c '", 1)[1].split("' < /tmp/files.txt")[0]
todo_py = '\n'.join(l[10:] if l.startswith(' ' * 10) else l for l in todo_py.split('\n'))   # the block's indentation in the YAML
todo = lambda files: sp_.run([sys.executable, '-c', todo_py], input='\0'.join(files).encode(), capture_output=True).stdout.decode().strip()
assert todo(['crime/3/caption.txt']) == '3 caption' and todo(['crime/3/picks.json', 'crime/3/caption.txt']) == '3 render caption'
assert todo(['crime/3/caption.txt', 'crime/4/caption.txt']) == '3 caption\n4 caption'
os.environ.setdefault('GITHUB_REPOSITORY', 'o/r'); os.environ.setdefault('GH_TOKEN', 'x')
argv_ = sys.argv; sys.argv = ['run.py', '9', 'caption']
import run as RUN
sys.argv = argv_
RUN.JOB, RUN.WORK = tempfile.mkdtemp(), tempfile.mkdtemp()
sent, said = [], []
RUN.publish = lambda paths, msg, **k: sent.append(list(paths)); RUN.comment = said.append
def stopped(body): said.append(body); raise SystemExit(3)
RUN.stop = stopped
open(os.path.join(RUN.JOB, 'caption.txt'), 'w', encoding='utf-8').write(ja_ok if RUN.LANG == 'ja' else de_ok)
RUN.caption_only(); assert sent == [] and said == []                                       # no video yet: kept for the render
open(os.path.join(RUN.WORK, 'video.mp4'), 'wb').write(b'x')
RUN.caption_only(); assert sent == [['caption.txt']] and 'caption.txt' in said[-1] and '/raw/' in said[-1], said
open(os.path.join(RUN.JOB, 'caption.txt'), 'w', encoding='utf-8').write('kurz')
try: RUN.caption_only(); raise AssertionError('a bad caption must be refused')
except SystemExit: assert len(sent) == 1 and 'hashtag' in said[-1], said
print('crime unit checks OK')
