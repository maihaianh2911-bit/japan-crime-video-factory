"""Short on-screen captions, as the sample: 2–3 words at a time, timed to the voice.

chunks(line, lang) splits one spoken line into caption chunks (display text without commas and full stops;
? and ! stay). weight(text, lang) is the measure used to place a chunk in time: kana count for Japanese (pykakasi
when installed, else characters), letters for German. voice_check.py stores, per line, an alignment
[[fraction of the line's weight, seconds], …] from Whisper's word times; time_at() reads it (linear when missing).
"""
import re

JA_PUNCT = '、。，．…「」『』（）()'
JA_PART = ('から', 'まで', 'より', 'ので', 'のに', 'けど', 'ても', 'でも', 'には', 'では', 'とは', 'へは', 'も', 'は', 'が', 'を', 'に', 'で', 'と', 'へ', 'の', 'や', 'て', 'た')
DE_MAX_CH, DE_MAX_W = 20, 3     # characters / words per chunk (Anton 86 px: ~24 capitals fit one row)
JA_MIN, JA_MAX = 3, 9           # characters per chunk

try:
    import pykakasi
    _kks = pykakasi.kakasi()
except Exception:   # the preview runs without it: characters are close enough there
    _kks = None


def _clean_de(w):
    return re.sub(r'^[„“"‚‘»«(\[]+|[„“"‚‘»«)\],.;:]+$', '', w)


def _is_kana(c):
    return '぀' <= c <= 'ゟ'


DE_FUNC = set('''der die das den dem des ein eine einen einem einer eines und oder aber doch denn sondern dass ob wenn als wie weil da
in im an am auf aus bei mit nach von vom zu zum zur für über unter vor hinter neben zwischen durch gegen ohne um bis seit während
sich nicht kein keine noch schon auch nur sehr so es er sie wir ihr ich du man'''.split())


def chunks_de(line):
    """Best split into chunks of 1–3 words (≤ 18 characters shown): a chunk ends at punctuation when it can, does
    not end on an article or preposition, and single-word chunks are kept for long words (DP over the words)."""
    words = [w for w in line.split() if _clean_de(w)]
    n = len(words)
    best = [(0.0, 0)] + [(float('inf'), 0)] * n
    for j in range(1, n + 1):
        for k in range(1, DE_MAX_W + 1):
            i = j - k
            if i < 0: break
            shown = ' '.join(_clean_de(w) for w in words[i:j])
            if len(shown) > DE_MAX_CH and k > 1: continue
            c = 1.0
            if k == 1: c += 0 if len(shown) >= 10 else 2.5
            if re.search(r'[,.;:!?]["“”»«]?$', words[j - 1]): c -= 2.0
            elif j < n and _clean_de(words[j - 1]).lower() in DE_FUNC: c += 4.0
            if any(re.search(r'[,.;:!?]["“”»«]?$', w) for w in words[i:j - 1]): c += 6.0   # punctuation inside a chunk
            if j < n and _clean_de(words[j]).lower() in DE_FUNC: c -= 0.5
            if best[i][0] + c < best[j][0]: best[j] = (best[i][0] + c, i)
    cuts, j = [], n
    while j > 0:
        cuts.append(j); j = best[j][1]
    cuts = [0] + cuts[::-1]
    return [(' '.join(words[a:b]), ' '.join(_clean_de(w) for w in words[a:b])) for a, b in zip(cuts, cuts[1:])]


def _run(c):
    if '゠' <= c <= 'ヿ' or c == 'ー': return 'kata'
    if c.isdigit() or c in '０１２３４５６７８９': return 'num'
    if _is_kana(c): return 'hira'
    return 'other'


def chunks_ja(line):
    """Break after punctuation, or after a particle that ends a phrase (next character not kana), 3–9 characters."""
    t = line.strip()
    cuts, i, start = [], 0, 0
    while i < len(t):
        c = t[i]
        if c in JA_PUNCT or c in '？！?!':
            j = i + 1
            while j < len(t) and (t[j] in JA_PUNCT or t[j] in '？！?!'): j += 1
            if j - start >= 1: cuts.append(j); start = j
            i = j; continue
        if i - start + 1 >= JA_MAX:
            # too long: cut at the best earlier particle, else here
            best = None
            for k in range(start + JA_MIN, i + 1):
                if any(t[start:k].endswith(p) for p in JA_PART) and k < len(t) and not _is_kana(t[k]): best = k
            k = best
            if not k:   # no particle: never cut inside a katakana name or a number, cut where the script changes
                k = i + 1
                while k < len(t) and _run(t[k - 1]) == _run(t[k]) and _run(t[k]) in ('kata', 'num'): k += 1
                if k - start > JA_MAX + 6:   # a very long run: cut at a script change instead
                    k = next((m for m in range(i + 1, start + JA_MIN - 1, -1) if _run(t[m - 1]) != _run(t[m])), i + 1)
            cuts.append(k); start = k; i = k; continue
        for p in JA_PART:
            k = i + 1
            if t[start:k].endswith(p) and k - start >= JA_MIN and k < len(t) and not _is_kana(t[k]) and t[k] not in JA_PUNCT:
                cuts.append(k); start = k; break
        i += 1
    if start < len(t): cuts.append(len(t))
    parts, prev = [], 0
    for k in cuts:
        if k > prev: parts.append(t[prev:k]); prev = k
    # merge chunks that are only punctuation or too short into a neighbour
    merged = []
    for p in parts:
        core = ''.join(ch for ch in p if ch not in JA_PUNCT)
        if merged and (len(core) < 2 or len(core.strip('？！?!')) == 0) and len(merged[-1]) + len(p) <= JA_MAX + 3:
            merged[-1] += p
        else:
            merged.append(p)
    if len(merged) > 1 and len(merged[0]) < 2: merged[1] = merged[0] + merged[1]; merged = merged[1:]
    return [(p, ''.join(ch for ch in p if ch not in JA_PUNCT)) for p in merged if p.strip()]


def chunks(line, lang):
    """[(spoken part, shown text)] covering the whole line in order."""
    return chunks_ja(line) if lang == 'ja' else chunks_de(line)


def weight(text, lang):
    if lang == 'ja':
        t = re.sub(r'[\s、。，．,.!?！？「」『』（）()…・—–\-]', '', text)
        if _kks:
            return max(1, len(''.join(x['hira'] for x in _kks.convert(t))))
        return max(1, len(t))
    return max(1, len(re.sub(r'[^\wäöüßÄÖÜ]', '', text)))


def time_at(frac, dur, align=None):
    """Seconds into a line at this fraction of its weight: Whisper's word times when present, else linear."""
    frac = min(1.0, max(0.0, frac))
    if not align or len(align) < 2:
        return frac * dur
    pts = [(0.0, 0.0)] + [(min(1.0, max(0.0, a)), min(dur, max(0.0, b))) for a, b in align] + [(1.0, dur)]
    pts.sort()
    for (a0, t0), (a1, t1) in zip(pts, pts[1:]):
        if a0 <= frac <= a1:
            return t0 if a1 == a0 else t0 + (t1 - t0) * (frac - a0) / (a1 - a0)
    return frac * dur
