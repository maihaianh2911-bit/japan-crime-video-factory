"""Settings of this channel (prompts/channel.json): language, default voice, AI tag, picture generator."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = json.load(open(os.path.join(ROOT, 'prompts', 'channel.json'), encoding='utf-8'))
LANG = CFG.get('lang', 'ja')
assert LANG in ('ja', 'de'), f'prompts/channel.json: lang must be ja or de, not ja'
VOICE = CFG.get('voice') or ''
AI_TAG = CFG.get('ai_tag') or ('イメージ（AI生成）' if LANG == 'ja' else 'KI-Illustration')
REPO = CFG.get('repo', '')
