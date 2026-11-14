#!/usr/bin/env python3
"""Machine steps of a crime video (GitHub Actions). Usage: run.py <N> <step> [<step> ...]

  prepare  voice (one 11labs job per line, unchanged lines reused), voice check with word times, picture search
           and AI illustrations round 1 (only when the queries changed) → renders/crime/<N>/voice/, img/1/
           (when the voice or its check fails, the lines already read are kept in voice-partial/ for the next run)
  search   every crime/<N>/search-<r>.json whose round is not on renders yet → renders/crime/<N>/img/<r>/
           (crime-voice while it runs; then crime-pick, a comment and a call to Claude)
  render   pictures from picks.json, plan, fonts, Remotion render, loudness, shot sheet
           → renders/crime/<N>/video.mp4, subtitles.srt, credits.txt, sources.json, sheet.jpg, edits.md (the scene
           edit of every scene and why, for the owner)
After prepare/search the issue waits for Claude (crime-pick) unless picks.json exists, then render runs too; not when
prepare searched round 1 again with changed queries (the picks would point at other pictures).
A video over 95 MB is encoded again at a bitrate that lands ~90 MB (GitHub refuses files over 100 MB).
Needs GH_TOKEN, GITHUB_REPOSITORY; prepare needs VN11_API_KEY; AI illustrations need one generator key
(scripts/gen_images.py), without it they are skipped.
Exit code 3: stopped before any work and the owner was told why on the issue (the voice key is missing, or the
issue's files were removed by renders-cleanup.yml after 14 days without activity and picks.json no longer fits).
"""
import json, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ff

N, steps = sys.argv[1], sys.argv[2:]
JOB = os.path.join(ROOT, 'crime', N)
WORK = os.path.join(ROOT, 'out', f'crime-{N}')          # mirror of renders/crime/<N>/ for this run
PUB = os.path.join(ROOT, 'public')
REPO = os.environ['GITHUB_REPOSITORY']
URL = f"https://x-access-token:{os.environ['GH_TOKEN']}@github.com/maihaianh2911-bit/japan-crime-video-factory.git"
GIT = ['git', '-c', 'user.name=render-bot', '-c', 'user.email=render-bot@users.noreply.github.com']
sh = lambda *a, **k: subprocess.run(a, check=True, **k)


def gh(*a, tries=1):
    """gh call; a failure is printed (stderr), and retried once more when tries=2 (label changes)."""
    for i in range(tries):
        r = subprocess.run(['gh', *a], check=False, capture_output=True, text=True)
        if r.returncode == 0:
            return r
        print(f'gh {" ".join(a[:4])} failed ({r.returncode}): {r.stderr.strip()[:300]}', file=sys.stderr, flush=True)
        if i < tries - 1: time.sleep(5)
    return r


def labels(add=(), remove=()):
    """New labels first, then the old ones go: an API error halfway never leaves the issue without a step label."""
    if add: gh('issue', 'edit', N, '--add-label', ','.join(add), tries=2)
    for l in remove:
        if l not in add: gh('issue', 'edit', N, '--remove-label', l, tries=2)


def comment(body):
    gh('issue', 'comment', N, '--body', body)


def fetch_renders(tries=3):
    """Current renders/crime/<N>/ → WORK (empty when nothing was published yet). Only a branch that does not exist
    counts as "nothing yet": a fetch that keeps failing stops the run, because going on with an empty folder would
    read (and pay for) the whole voice again and search round 1 again."""
    os.makedirs(WORK, exist_ok=True)
    for i in range(tries):
        head = subprocess.run(['git', 'ls-remote', '--exit-code', URL, 'refs/heads/renders'], cwd=ROOT, capture_output=True)
        if head.returncode == 2:   # no renders branch yet: the first video of this repo
            return
        if head.returncode == 0 and subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, '+refs/heads/renders:refs/remotes/origin/renders'], cwd=ROOT).returncode == 0:
            break
        print(f'renders: fetch failed (attempt {i + 1}/{tries})', file=sys.stderr, flush=True)
        time.sleep(10 * (i + 1))
    else:
        raise SystemExit('không lấy được nhánh renders (lỗi mạng hoặc GitHub): dừng lại để không đọc lại giọng đã trả tiền')
    ls = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'origin/renders', f'crime/{N}/'], cwd=ROOT, capture_output=True, text=True).stdout
    if ls.strip():
        tar = subprocess.run(['git', 'archive', 'origin/renders', f'crime/{N}'], cwd=ROOT, capture_output=True, check=True).stdout
        tmp = os.path.join(ROOT, 'out', 'renders-tmp'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        subprocess.run(['tar', '-x', '-C', tmp], input=tar, check=True)
        shutil.copytree(os.path.join(tmp, 'crime', N), WORK, dirs_exist_ok=True)


def renders_worktree(wt):
    """A fresh worktree at the current tip of renders (an empty orphan when the branch does not exist yet).
    False when the branch could not be fetched."""
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', 'worktree', 'prune'], cwd=ROOT)
    head = subprocess.run(['git', 'ls-remote', '--exit-code', URL, 'refs/heads/renders'], cwd=ROOT, capture_output=True)
    if head.returncode == 2:   # first video of a new repo: start the branch empty
        sh('git', 'worktree', 'add', '-q', '--detach', wt, cwd=ROOT)
        sh('git', 'checkout', '-q', '--orphan', f'renders-new-{time.time_ns()}', cwd=wt)
        subprocess.run(['git', 'rm', '-rf', '-q', '.'], cwd=wt, capture_output=True); sh('git', 'clean', '-fdq', cwd=wt)
        return True
    if head.returncode or subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, '+refs/heads/renders:refs/remotes/origin/renders'], cwd=ROOT).returncode:
        return False
    sh('git', 'worktree', 'add', '-q', '--detach', wt, 'origin/renders', cwd=ROOT)
    return True


def publish(paths, msg, tries=4, remove=()):
    """Copy WORK-relative paths (files or folders) to renders/crime/<N>/ in one commit and push it. Every attempt
    starts again from the freshly fetched tip of renders (rebasing shallow history can conflict and then push a
    commit without this run's files). A folder replaces the published one, so no stale file stays next to a new
    index.json. remove: published folders deleted in the same commit."""
    wt = os.path.join(ROOT, 'out', 'renders-wt')
    for i in range(tries):
        if i:
            print(f'renders: attempt {i}/{tries} failed (push rejected or fetch error), starting again from the new tip', file=sys.stderr, flush=True)
            time.sleep(5 * i)
        if not renders_worktree(wt):
            continue
        for p in remove:
            shutil.rmtree(os.path.join(wt, 'crime', N, p), ignore_errors=True)
        for p in paths:
            src, dst = os.path.join(WORK, p), os.path.join(wt, 'crime', N, p)
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
        sh(*GIT, 'add', '-A', cwd=wt)
        if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=wt).returncode == 0:
            print(f'crime/{N}: {msg} — already published'); return
        sh(*GIT, 'commit', '-q', '-m', f'crime/{N}: {msg}', cwd=wt)
        if subprocess.run(['git', 'push', '-q', URL, 'HEAD:refs/heads/renders'], cwd=wt).returncode == 0:
            print(f'published crime/{N}: {msg}'); return
    raise SystemExit(f'không đẩy được lên nhánh renders sau {tries} lần thử ({msg})')


def link(p):
    return f'https://github.com/maihaianh2911-bit/japan-crime-video-factory/blob/renders/crime/{N}/{p}'


def keep_paid_lines(new, part):
    """The voice step failed: the lines already read (paid) go to renders/crime/<N>/voice-partial/, where the next
    run finds them (tts_lines.py --prev). The published voice/ stays as it was: a render must never see half a
    voice or lines without their word times."""
    try:
        rows = json.load(open(os.path.join(new, 'lines.json'), encoding='utf-8'))
        rows = [r for r in rows if os.path.exists(os.path.join(new, r['file']))]
        if not rows:
            return
        shutil.rmtree(part, ignore_errors=True); os.makedirs(part)
        for r in rows: shutil.copy(os.path.join(new, r['file']), os.path.join(part, r['file']))
        json.dump(rows, open(os.path.join(part, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        publish(['voice-partial'], f'giọng đọc dở ({len(rows)} câu đã đọc, giữ lại cho lần chạy sau)')
    except (Exception, SystemExit) as e:   # never hide the error that stopped the voice step
        print(f'voice-partial: could not keep the lines already read: {e}', file=sys.stderr, flush=True)


def prepare():
    """Voice, then picture search round 1. Returns (lines.json rows, True when round 1 was searched again with
    changed queries, i.e. the pictures behind existing picks changed)."""
    script = json.load(open(os.path.join(JOB, 'script.json'), encoding='utf-8'))
    labels(add=['crime-voice'], remove=['crime-plan', 'crime-failed'])
    prev, part = os.path.join(WORK, 'voice'), os.path.join(WORK, 'voice-partial')
    new = os.path.join(ROOT, 'out', f'voice-{N}')
    shutil.rmtree(new, ignore_errors=True)
    try:
        sh(sys.executable, os.path.join(HERE, 'tts_lines.py'), os.path.join(JOB, 'script.json'), new, '--prev', prev, '--prev', part)
        for i in range(2):   # the check downloads the Whisper model: one more try before giving up
            if subprocess.run([sys.executable, os.path.join(HERE, 'voice_check.py'), new, os.path.join(new, 'check.md')]).returncode == 0:
                break
            if i: raise SystemExit('kiểm tra giọng đọc (Whisper) lỗi hai lần; các câu đã đọc được giữ lại, chạy lại bước prepare sẽ không đọc lại')
            time.sleep(20)
    except (subprocess.CalledProcessError, SystemExit):
        keep_paid_lines(new, part)
        raise
    shutil.rmtree(prev, ignore_errors=True); shutil.copytree(new, prev)
    had_part = os.path.isdir(part); shutil.rmtree(part, ignore_errors=True)
    # before the picture search: the paid voice is kept even if the search fails
    publish(['voice'], 'giọng đọc', remove=['voice-partial'] if had_part else ())
    q = (script.get('queries') or []) + (script.get('urls') or []) + (script.get('gen') or [])
    old = os.path.join(WORK, 'img', '1', 'queries.json')
    had = os.path.exists(old)
    requeried = False
    if q and (not had or json.load(open(old, encoding='utf-8')) != q):
        requeried = had
        d = os.path.join(WORK, 'img', '1'); shutil.rmtree(d, ignore_errors=True)
        find(d, q)
        json.dump(q, open(os.path.join(d, 'queries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        publish(['img/1'], 'ảnh')
    rows = json.load(open(os.path.join(prev, 'lines.json'), encoding='utf-8'))
    return rows, requeried


def find(d, q, env=None):
    """Picture search (queries, urls), then the AI illustrations ({"gen": …}) of one round into d."""
    spec = os.path.join(ROOT, 'out', f'spec-{N}.json')
    search = [x for x in q if not (isinstance(x, dict) and 'gen' in x)]
    gen = [x for x in q if isinstance(x, dict) and 'gen' in x]
    os.makedirs(d, exist_ok=True)
    if search:
        json.dump(search, open(spec, 'w', encoding='utf-8'), ensure_ascii=False)
        sh(sys.executable, os.path.join(ROOT, 'scripts', 'find_images.py'), d, '--spec', spec, env=env)
    if gen:
        json.dump(gen, open(spec, 'w', encoding='utf-8'), ensure_ascii=False)
        sh(sys.executable, os.path.join(ROOT, 'scripts', 'gen_images.py'), d, '--spec', spec, env=env)


def search():
    """Every search round that is new or whose queries changed. Returns the folders made (['img/2', …])."""
    did = []
    for f in sorted(os.listdir(JOB)):
        if f.startswith('search-') and f.endswith('.json'):
            r = f[len('search-'):-len('.json')]
            sj = json.load(open(os.path.join(JOB, f), encoding='utf-8'))
            q = (sj.get('queries') or []) + (sj.get('urls') or []) + (sj.get('gen') or [])
            d = os.path.join(WORK, 'img', r)
            if os.path.exists(os.path.join(d, 'queries.json')) and json.load(open(os.path.join(d, 'queries.json'), encoding='utf-8')) == q:
                continue
            shutil.rmtree(d, ignore_errors=True)
            earlier = [os.path.join(WORK, 'img', x) for x in sorted(os.listdir(os.path.join(WORK, 'img'))) if x != r] \
                if os.path.isdir(os.path.join(WORK, 'img')) else []
            find(d, q, env={**os.environ, 'FIND_SEEN': ':'.join(earlier)})
            json.dump(q, open(os.path.join(d, 'queries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            did.append(f'img/{r}')
    if did: publish(did, 'tìm thêm ảnh')
    return did


MAX_MB, TARGET_MB = 95, 90   # GitHub refuses files over 100 MB


def encode(raw, dst, rate):
    """Final encode of the Remotion output: H.264 + loudness-normalised AAC. rate = ['-crf', …] or a bitrate."""
    ff.run('-i', raw, '-c:v', 'libx264', '-preset', 'medium', *rate, '-pix_fmt', 'yuv420p',
           '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart', dst)


def render():
    labels(add=['crime-render'], remove=['crime-pick', 'crime-check', 'crime-done', 'crime-fix', 'crime-failed'])
    pub = os.path.join(PUB, 'crime', N); shutil.rmtree(pub, ignore_errors=True)
    shutil.copytree(os.path.join(WORK, 'voice'), os.path.join(pub, 'voice'))
    imgsrc = os.path.join(WORK, 'img')
    if os.path.isdir(os.path.join(JOB, 'own')):
        shutil.copytree(os.path.join(JOB, 'own'), os.path.join(imgsrc, 'own'), dirs_exist_ok=True)
    picks = os.path.join(JOB, 'picks.json')
    sh(sys.executable, os.path.join(HERE, 'prep.py'), picks, imgsrc, os.path.join(pub, 'img'))
    out = os.path.join(ROOT, 'out', f'render-{N}')
    sh(sys.executable, os.path.join(HERE, 'build.py'), JOB, PUB, N, imgsrc, out)
    sh(sys.executable, os.path.join(HERE, 'fonts.py'), os.path.join(out, 'plan.json'), os.environ.get('FONTSOURCE', '/tmp/fontsource'), PUB)
    sh('npx', 'remotion', 'render', 'src/crime/index.ts', 'CrimeV', os.path.join(out, 'raw.mp4'), f'--props={os.path.join(out, "plan.json")}',
       '--gl=swiftshader', '--log=error', cwd=ROOT)
    plan = json.load(open(os.path.join(out, 'plan.json'), encoding='utf-8'))
    raw, video = os.path.join(out, 'raw.mp4'), os.path.join(WORK, 'video.mp4')
    encode(raw, video, ['-crf', '24'])
    mb = os.path.getsize(video) / 1e6
    if mb > MAX_MB:   # long videos only: an average bitrate that lands ~90 MB
        kbps = int(TARGET_MB * 8000 / plan['duration']) - 160
        print(f'video {mb:.1f} MB > {MAX_MB} MB (GitHub limit 100 MB): encoding again at {kbps} kbit/s', flush=True)
        encode(raw, video, ['-b:v', f'{kbps}k', '-maxrate', f'{kbps}k', '-bufsize', f'{2 * kbps}k'])
        mb = os.path.getsize(video) / 1e6
        print(f'video now {mb:.1f} MB', flush=True)
        if mb > 100: raise SystemExit(f'video {mb:.1f} MB, vẫn quá 100 MB')
    sh(sys.executable, os.path.join(HERE, 'sheet.py'), video, os.path.join(out, 'plan.json'), os.path.join(WORK, 'sheet.jpg'))
    for f in ('subtitles.srt', 'credits.txt', 'sources.json', 'plan.json', 'edits.md'): shutil.copy(os.path.join(out, f), os.path.join(WORK, f))
    publish(['video.mp4', 'sheet.jpg', 'subtitles.srt', 'credits.txt', 'sources.json', 'plan.json', 'edits.md'], 'video')
    return plan['duration']


def wake(why):
    """Call the Claude task for this issue. Returns ok | busy (a Claude chat holds the issue) | failed (the script
    then told the owner on the issue how to start Claude)."""
    res = os.path.join(ROOT, 'out', f'wake-{N}.txt')
    os.makedirs(os.path.dirname(res), exist_ok=True)
    if os.path.exists(res): os.remove(res)
    subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'wake_claude.sh'), why, N], env={**os.environ, 'WAKE_RESULT': res})
    try:
        return open(res, encoding='utf-8').read().strip()
    except OSError:
        return 'failed'


def claude(woken, text):
    """A sentence about what Claude does next: only when Claude was really called (no promise after a failed call)."""
    return text if woken != 'failed' else ''


EXPLAINED = 3   # exit code: stopped before any work, and the owner was told why on the issue (crime.yml adds no more)


def stop(body):
    comment(body)
    sys.exit(EXPLAINED)


if __name__ == '__main__':
    if 'prepare' in steps and not os.environ.get('VN11_API_KEY'):
        stop('🤖 Máy chưa tạo được giọng đọc vì repo này **chưa có khóa giọng đọc**. Cách thêm: Settings → Secrets and '
             'variables → Actions → New repository secret, tên `VN11_API_KEY`, giá trị là khóa giọng đọc (cùng khóa như các '
             'repo khác). Thêm xong thì viết một bình luận ở đây (ví dụ "đã thêm khóa") để máy chạy lại.')
    fetch_renders()
    if os.path.exists(os.path.join(JOB, 'picks.json')) and not os.path.exists(os.path.join(WORK, 'voice', 'lines.json')):
        # Pictures were chosen once, but the voice is gone from renders: renders-cleanup.yml removed this issue's files
        # (no activity for 14 days). Making them again would number the pictures anew, and the old picks.json would
        # then show other pictures than the ones Claude chose — so refuse instead of rendering.
        stop('🤖 Không sửa tiếp được trên phiếu này: giọng đọc và ảnh của video đã được dọn (máy tự dọn file của phiếu '
             'không hoạt động quá 14 ngày), nên các ảnh đã chọn không còn khớp. Hãy mở một phiếu mới với kịch bản (đã sửa) '
             'để làm lại video.')
    if 'prepare' in steps:
        rows, requeried = prepare()
        flagged = sum(1 for r in rows if r.get('diff'))
        speech = sum(r['duration'] for r in rows)
        has_picks = os.path.exists(os.path.join(JOB, 'picks.json'))
        requeried = requeried and has_picks
        if not has_picks or requeried:
            # changed round-1 queries renumber the pictures: existing picks would now point at other pictures
            if 'render' in steps: steps.remove('render')
            labels(add=['crime-pick'], remove=['crime-voice'])
            w = wake(f'Phiếu vụ án số {N}: ' + ('từ khóa ảnh đợt 1 đã đổi, phải chọn lại ảnh.' if requeried
                                                 else 'giọng và ảnh đã sẵn sàng, chờ chọn ảnh.'))
            comment(f'🤖 Giọng đọc xong: {len(rows)} câu, {speech:.0f} giây lời đọc'
                    f'{f" ({flagged} câu cần nghe lại cách đọc)" if flagged else ""}. '
                    + ('Từ khóa tìm ảnh đã đổi nên ảnh đợt 1 là ảnh mới: phải chọn lại ảnh trước khi dựng video.'
                       if requeried else 'Ảnh đã tìm xong.' + claude(w, ' Claude sẽ xem và chọn ảnh cho từng cảnh.')))
        elif 'render' not in steps:
            steps.append('render')
    if 'search' in steps:
        # crime-voice while the machine searches (the issue must not look as if it waited for Claude, and AGENT_CRIME.md
        # forbids a picks.json push under crime-voice); crime-pick, a comment and a call to Claude when it is done
        waits = 'render' not in steps
        if waits: labels(add=['crime-voice'], remove=['crime-pick'])
        did = search()
        if waits:
            labels(add=['crime-pick'], remove=['crime-voice'])
            if did:
                idx = [os.path.join(WORK, d, 'index.json') for d in did]
                found = sum(len(g.get('results') or []) for f in idx if os.path.exists(f) for g in json.load(open(f, encoding='utf-8')))
                w = wake(f'Phiếu vụ án số {N}: đã tìm thêm ảnh xong, chờ chọn ảnh.')
                comment(f'🤖 Đã tìm thêm ảnh xong (đợt {", ".join(d.split("/")[-1] for d in did)}: {found} ảnh mới).'
                        + claude(w, ' Claude sẽ xem và chọn ảnh.'))
    if 'render' in steps:
        if not os.path.exists(os.path.join(WORK, 'voice', 'lines.json')):
            raise SystemExit('chưa có giọng đọc cho phiếu này (cần script.json)')
        length = render()
        labels(add=['crime-check'], remove=['crime-render', 'crime-voice'])
        m, s = divmod(round(length), 60)
        w = wake(f'Phiếu vụ án số {N}: video đã dựng, chờ kiểm tra.')
        comment(f'🤖 Đã dựng xong bản video ({m} phút {s:02d} giây).'
                + claude(w, ' Claude đang kiểm tra lại từng cảnh trước khi giao.') + '\n\n'
                f'- Video: {link("video.mp4")}\n- Ảnh các cảnh: {link("sheet.jpg")}\n- Cách edit từng cảnh: {link("edits.md")}')
