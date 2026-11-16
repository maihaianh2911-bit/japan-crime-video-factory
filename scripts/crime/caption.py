"""The posting caption of a crime video (crime/<N>/caption.txt, written by Claude at the picks step, published by
run.py beside video.mp4): the text the owner pastes when posting the video.

Format (AGENT_CRIME.md §2.9): line 1 a hook title (≤ 80 characters); 2–4 short sentences; a blank line; 5–8 hashtags
with #shorts; a blank line; a picture-credit line, and the AI line (with the channel's AI tag) when the video uses AI
illustrations. UTF-8, ≤ 2000 characters, in the channel's language. problems() checks what a machine can check; the
facts are Claude's to check against the script.
"""
import json, os, re

MAX, TITLE_MAX = 2000, 80
CJK = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
CREDIT = ('Bildquellen', '画像出典')


def problems(text, lang, ai_tag, uses_ai):
    """List of plain-Vietnamese problems of a caption (empty = fine)."""
    out = []
    text = (text or '').strip()
    if not text:
        return ['lời đăng (caption.txt) đang trống']
    if len(text) > MAX: out.append(f'lời đăng dài {len(text)} ký tự, tối đa {MAX}')
    title = text.splitlines()[0].strip()
    if len(title) > TITLE_MAX: out.append(f'dòng tiêu đề dài {len(title)} ký tự, tối đa {TITLE_MAX}')
    # the credit line may name a photographer in any script (a Japanese user name on a German caption)
    cjk = len(CJK.findall('\n'.join(l for l in text.splitlines() if not l.startswith(CREDIT))))
    if lang == 'ja' and cjk < 10: out.append('lời đăng phải viết bằng tiếng Nhật (kênh tiếng Nhật)')
    if lang == 'de' and cjk: out.append('lời đăng của kênh tiếng Đức có chữ Nhật/Trung: phải viết bằng tiếng Đức')
    tags = re.findall(r'#\w+', text)
    if not 5 <= len(tags) <= 9: out.append(f'cần 5–8 hashtag và #shorts (đang có {len(tags)})')
    if '#shorts' not in [t.lower() for t in tags]: out.append('thiếu hashtag #shorts')
    if uses_ai and ai_tag not in text: out.append(f'video có ảnh AI: lời đăng phải có dòng "{ai_tag}"')
    return out


def uses_ai(sources_json):
    """True when the published sources.json of a video lists an AI illustration."""
    if not os.path.exists(sources_json):
        return False
    return any(p.get('ai') for p in json.load(open(sources_json, encoding='utf-8')).get('pictures', []))
