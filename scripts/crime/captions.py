"""Short on-screen captions, as the sample: 2–3 words at a time, timed to the voice.

chunks(line, lang) splits one spoken line into caption chunks (display text without commas and full stops;
? and ! stay, and so does the dot of a German ordinal or abbreviation: "1.", "Dr."). weight(text, lang) is the
measure used to place a chunk in time: kana count for Japanese (pykakasi when installed, else characters), letters
for German. voice_check.py stores, per line, an alignment [[fraction of the line's weight, seconds], …] from
Whisper's word times; time_at() reads it (linear when missing).
"""
import re

JA_PUNCT = '、。，．…「」『』（）()'
JA_PART = ('から', 'まで', 'より', 'ので', 'のに', 'けど', 'ても', 'でも', 'には', 'では', 'とは', 'へは', 'も', 'は', 'が', 'を', 'に', 'で', 'と', 'へ', 'の', 'や', 'て', 'た')
JA_PART_KANA = JA_PART[:-6] + ('と', 'へ')   # before more hiragana only these end a phrase (で|きる, の|です, た|ち do not)
# Japanese: one caption row (layout.CAP_W 1000 px, Noto Sans JP 78 px, 0.02 em spacing) holds 12 full-width characters
JA_ROW = 12
JA_NO_START = set('ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶーｰ・、。，．,.…‥？！?!」』）)］】〕〉》々ゝゞヽヾ゛゜ 　')
JA_NO_END = set('「『（(［【〔〈《')
JA_BREAK = set('、。，．…？！?!」』）) 　')
JA_WORD = ('こと', 'もの', 'ところ', 'でしょう', 'だろう', 'のです', 'でき', 'しまっ', 'しまう', 'しまい', 'ください',
           'いった', 'そんな', 'こんな', 'あんな', 'どう', 'ます', 'ません', 'ました')   # hiragana that starts a word
JA_TAIL = ('す', 'ん', 'る', 'かっ', 'った', 'ら', 'れ')                                # hiragana that ends the word before
DE_MAX_CH, DE_MAX_W = 20, 3     # characters / words per chunk (Anton 86 px: ~25 capitals fit one row)
DE_MONTHS = set('januar februar märz april mai juni juli august september oktober november dezember'.split())
# words whose dot is no sentence end (shown on screen): titles, "z. B.", "Nr." …; single letters too (initials, "v. Chr.")
DE_ABBR = set('dr prof st nr hl sel bzw ca vgl ggf sog inkl evtl mio mrd jh chr hr fr frl dipl ing abs str bd kap '
              'ziff tel gebr verh geb gest usw etc'.split())
DE_TITLE = set('dr prof st nr hl sel hr fr frl dipl ing'.split())   # a chunk never ends on these (nor on "z.", "v.")
DE_ORD_BEFORE = set('am im vom zum zur der die das den dem des ab seit bis jeden jedes jeder diesem dieses dieser'.split())
DE_FUNC = set('''der die das den dem des ein eine einen einem einer eines und oder aber doch denn sondern dass ob wenn als wie weil da
in im an am auf aus bei mit nach von vom zu zum zur für über unter vor hinter neben zwischen durch gegen ohne um bis seit während
sich nicht kein keine noch schon auch nur sehr so es er sie wir ihr ich du man'''.split())

try:
    import pykakasi
    _kks = pykakasi.kakasi()
except Exception:   # the preview runs without it: characters are close enough there
    _kks = None


# ---------------------------------------------------------------- German
def _bare_de(w):
    return re.sub(r'^[„“"‚‘»«(\[]+|[„“"‚‘»«)\],.;:!?]+$', '', w)


def de_dot_kept(words, i):
    """True when the dot ending words[i] belongs to the word: an ordinal before a word or a number ("am 1. Juli",
    "der 3. Exorzismus", "bis zum 21. April") or an abbreviation ("Dr.", "St.", "z. B.", "Nr."). Such a dot is shown
    and is no sentence end; "Sie war 23. Niemand half." stays a sentence end."""
    w = re.sub(r'[)\]"“”»«]+$', '', words[i])
    if not w.endswith('.') or w.endswith('..'): return False
    core = re.sub(r'^[„“"‚‘»«(\[]+', '', w[:-1])
    nb = _bare_de(words[i + 1]) if i + 1 < len(words) else ''
    if re.fullmatch(r'\d{1,4}', core): return de_is_ordinal(words[i - 1] if i else '', nb)
    if core.lower() in DE_ABBR: return True
    return bool(nb) and bool(re.fullmatch(r'[A-Za-zÄÖÜäöü]', core))   # an initial: "z. B.", "John F. Kennedy"


def de_is_ordinal(prev, nxt):
    """A number written with a dot ("1.") between the words prev and nxt is an ordinal, not a sentence end: before
    a month, a number or a lower-case word, or after an article or preposition ("am", "der", "bis zum" …).
    voice_check.py uses the same rule to spell numbers out."""
    nb = _bare_de(nxt)
    if not nb: return False
    return nb.lower() in DE_MONTHS or nb[0].isdigit() or nb[0].islower() or _bare_de(prev).lower() in DE_ORD_BEFORE


def _clean_de(words, i):
    """Shown form of words[i]: no quotes, brackets, commas or full stops around it (? and ! stay), but the dot of
    an ordinal or of an abbreviation stays ("1.", "Dr.")."""
    w = re.sub(r'^[„“"‚‘»«(\[]+|[„“"‚‘»«)\],.;:]+$', '', words[i])
    return w + '.' if w and de_dot_kept(words, i) else w


def _ends_de(words, i):
    """words[i] ends a clause or a sentence (comma, ?, !, or a full stop that is no ordinal or abbreviation dot)."""
    w = words[i]
    if not re.search(r'[,.;:!?]["“”»«)\]]?$', w): return False
    return not (re.search(r'\.["“”»«)\]]?$', w) and de_dot_kept(words, i))


def chunks_de(line):
    """Best split into chunks of 1–3 words (≤ 20 characters shown; an ordinal "1." or a title "Dr." does not count
    as a word): a chunk ends at punctuation when it can, does not end on an article, a preposition, a title or an
    initial ("Dr.", "z.", "F.") or an ordinal (so "1. Juli" stays together), and single-word chunks are kept for long
    words (DP over the words)."""
    words = [w for w in line.split() if _bare_de(w)]
    n = len(words)
    shown_w = [_clean_de(words, i) for i in range(n)]
    ordinal = [bool(re.fullmatch(r'\d+\.', s)) for s in shown_w]
    # a title, or an initial not followed by a lower-case word ("z. B.", "F. Kennedy"; "z. B. dieser" may end on "B.")
    title = [s.endswith('.') and (s[:-1].lower() in DE_TITLE or len(s) == 2 and s[0].isalpha()
                                  and not (m + 1 < n and shown_w[m + 1][:1].islower())) for m, s in enumerate(shown_w)]
    light = [o or t for o, t in zip(ordinal, title)]
    best = [(0.0, 0)] + [(float('inf'), 0)] * n
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            if sum(1 for m in range(i, j) if not light[m]) > DE_MAX_W: break
            shown = ' '.join(shown_w[i:j])
            if len(shown) > DE_MAX_CH and j - i > 1: break
            c = 1.0
            if j - i == 1: c += 0 if len(shown) >= 10 else 2.5
            if _ends_de(words, j - 1): c -= 2.0
            elif j < n and (ordinal[j - 1] or title[j - 1]): c += 8.0
            elif j < n and shown_w[j - 1].lower() in DE_FUNC: c += 4.0
            if any(_ends_de(words, m) for m in range(i, j - 1)): c += 6.0   # punctuation inside a chunk
            if j < n and _bare_de(words[j]).lower() in DE_FUNC: c -= 0.5
            if best[i][0] + c < best[j][0]: best[j] = (best[i][0] + c, i)
    cuts, j = [], n
    while j > 0:
        cuts.append(j); j = best[j][1]
    cuts = [0] + cuts[::-1]
    return [(' '.join(words[a:b]), ' '.join(shown_w[a:b])) for a, b in zip(cuts, cuts[1:])]


# ---------------------------------------------------------------- Japanese
def _is_kana(c):
    return '぀' <= c <= 'ゟ'


def _run(c):
    if c == '・': return 'dot'
    if '゠' <= c <= 'ヿ' or c in 'ーｰ': return 'kata'
    if c.isdigit() or c in '０１２３４５６７８９': return 'num'
    if _is_kana(c): return 'hira'
    if c.isascii() and c.isalpha(): return 'lat'
    return 'han'


def _ja_width(s):
    """Width in full-width characters (digits and Latin letters are about half)."""
    return sum(0.6 if c.isascii() else 1.0 for c in s)


def _ja_shown(p):
    return ''.join(ch for ch in p if ch not in JA_PUNCT).strip('・ 　')


# cost of a cut between two kinds of characters (lower = a better place to cut)
_JA_PAIR = {('hira', 'han'): 0.5, ('hira', 'kata'): 0.5, ('num', 'num'): 99, ('num', 'han'): 20, ('num', 'hira'): 3, ('num', 'kata'): 4, ('han', 'num'): 6,
            ('kata', 'num'): 2, ('kata', 'kata'): 25, ('lat', 'lat'): 25, ('han', 'han'): 3, ('han', 'hira'): 3,
            ('kata', 'hira'): 4, ('lat', 'hira'): 4, ('kata', 'han'): 2, ('han', 'kata'): 1, ('hira', 'hira'): 2.5}


def _ja_cut(t, b):
    """Cost of a cut between t[b-1] and t[b]; None where a chunk may not start or end."""
    a, c = t[b - 1], t[b]
    if c in JA_NO_START or a in JA_NO_END: return None
    if a in '」』' and c == 'と': return 3.0      # 「…」と言った: the quote particle stays with the quote
    if a in JA_BREAK: return -4.0
    if a == '・': return 8.0                     # inside a name: only when it is wider than the row
    ra, rc = _run(a), _run(c)
    cost = _JA_PAIR.get((ra, rc), 0.0 if ra == 'hira' else 1.0)
    if ra == 'han' and rc == 'hira' and c not in 'はがをのにでともへや': cost += 3.0   # 裂|き, 起|きた: okurigana
    if ra == 'hira':
        if rc != 'hira' and t[:b].endswith(JA_PART): cost -= 3.0           # after a particle
        elif rc != 'hira' and b >= 2 and _run(t[b - 2]) == 'han': cost += 5.0   # 切り|裂き: inside a compound verb
        if rc == 'hira':
            if t[:b].endswith(JA_PART_KANA): cost -= 1.5
            if t[b:].startswith(JA_WORD): cost -= 1.5
            if t[b:].startswith(JA_TAIL): cost += 4.0
    return cost


def _ja_chunk(s):
    """Cost of one chunk: short ones flicker, long ones read slowly, one wider than the row wraps."""
    w = _ja_width(_ja_shown(s))
    c = 2.0
    if w > JA_ROW: c += 50 + 10 * (w - JA_ROW)
    if w < 1.5: c += 10
    elif w < 3: c += 4
    if w > 7: c += 0.5 * (min(w, 9) - 7)
    if w > 9: c += 1.5 * (w - 9)
    return c


def chunks_ja(line):
    """Best split into phrases of ~3–9 characters, never wider than one caption row (DP over the cut points): cut
    after punctuation or a particle; never before a small kana, ー or punctuation, inside a number, a katakana name
    (a name longer than the row is cut at its ・) or a word ending (思いま|すか, できな|かった); a short tail (か？)
    stays with the chunk before it."""
    t = line.strip()
    n = len(t)
    if not n: return []
    cut = [0.0] + [_ja_cut(t, b) for b in range(1, n)] + [0.0]
    best = [(0.0, 0)] + [(float('inf'), 0)] * n
    for j in range(1, n + 1):
        if cut[j] is None: continue
        for i in range(j - 1, -1, -1):
            if cut[i] is None or best[i][0] == float('inf'): continue
            c = best[i][0] + _ja_chunk(t[i:j]) + cut[j]
            if c < best[j][0]: best[j] = (c, i)
    cuts, j = [], n
    while j > 0:
        cuts.append(j); j = best[j][1]
    cuts = [0] + cuts[::-1]
    return [(p, _ja_shown(p)) for p in (t[a:b] for a, b in zip(cuts, cuts[1:])) if p.strip()]


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
