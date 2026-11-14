#!/usr/bin/env python3
"""Fonts of the crime videos and the chunks a plan needs. Usage: fonts.py <plan.json> <fontsource_dir> <public_dir>

Four roles, as the owner's sample (a case file on a desk): sans (subtitle box, big numbers), serif (titles on torn
paper, names on the cards), mono (typed labels and dates), hand (handwritten yellow tags, notes). FAMILIES lists the
pinned npm packages per channel language; scripts/crime/get_fonts.sh downloads them into <fontsource_dir>/<package>.
Only the unicode-range chunks that contain characters of this video are copied to <public_dir>/crime/fonts/ and listed
in plan["fonts"] (CrimeV registers them with FontFace).
"""
import json, os, re, shutil, sys

# role: (CSS family, npm package@version, css files of the package)
FAMILIES = {
    'ja': {'sans': ('Noto Sans JP', '@fontsource-variable/noto-sans-jp@5.3.1', ['index.css']),
           'serif': ('Noto Serif JP', '@fontsource-variable/noto-serif-jp@5.3.1', ['index.css']),
           'mono': ('M PLUS 1 Code', '@fontsource-variable/m-plus-1-code@5.3.1', ['index.css']),
           'hand': ('Yusei Magic', '@fontsource/yusei-magic@5.3.0', ['index.css'])},
    'de': {'sans': ('Source Sans 3', '@fontsource-variable/source-sans-3@5.3.1', ['index.css']),
           'serif': ('Roboto Slab', '@fontsource-variable/roboto-slab@5.3.0', ['index.css']),
           'mono': ('Space Mono', '@fontsource/space-mono@5.3.0', ['400.css', '700.css']),
           'hand': ('Kalam', '@fontsource/kalam@5.3.0', ['400.css', '700.css'])},
}


def pkg_dir(spec):
    """Folder of a package in the fontsource dir: '@fontsource/space-mono@5.3.0' → 'space-mono'."""
    return spec.rsplit('@', 1)[0].split('/')[-1]


def faces(src, lang):
    """[(family, woff2 path, unicode-range, weight, style)] of every @font-face of the channel's fonts."""
    out = []
    for fam, spec, cssl in FAMILIES[lang].values():
        base = os.path.join(src, pkg_dir(spec))
        for css in cssl:
            for blk in re.findall(r'@font-face\s*{(.*?)}', open(os.path.join(base, css)).read(), re.S):
                f = re.search(r"url\(\./files/([^)]+\.woff2)\)", blk).group(1)
                ur = re.search(r'unicode-range:\s*([^;]+);', blk)
                wt = re.search(r'font-weight:\s*([^;]+);', blk)
                st = re.search(r'font-style:\s*([^;]+);', blk)
                out.append((fam, os.path.join(base, 'files', f), ur.group(1).strip() if ur else 'U+0-10FFFF',
                            wt.group(1).strip() if wt else '400', st.group(1).strip() if st else 'normal'))
    return out


def ranges(ur):
    rs = []
    for part in ur.split(','):
        part = part.strip().replace('U+', '').replace('u+', '')
        a, b = part.split('-') if '-' in part else (part, part)
        rs.append((int(a, 16), int(b, 16)))
    return rs


if __name__ == '__main__':
    if sys.argv[1] == '--packages':   # for get_fonts.sh
        print(' '.join(spec for _, spec, _ in FAMILIES[sys.argv[2]].values())); sys.exit()
    plan_path, src, pub = sys.argv[1], sys.argv[2], sys.argv[3]
    plan = json.load(open(plan_path, encoding='utf-8'))
    lang = plan.get('lang', 'ja')
    text = json.dumps(plan, ensure_ascii=False)
    chars = set(text) | set(text.upper()) | set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÄÖÜäöüß—–→✓„“‚‘«».,:;!?()/・「」（）、。 　')
    os.makedirs(f'{pub}/crime/fonts', exist_ok=True); out = []
    for fam, path, ur, wt, st in faces(src, lang):
        if any(any(a <= ord(c) <= b for a, b in ranges(ur)) for c in chars):
            name = os.path.basename(path)
            shutil.copy(path, f'{pub}/crime/fonts/{name}')
            out.append({'family': fam, 'file': f'crime/fonts/{name}', 'range': ur, 'weight': wt, 'style': st})
    plan['fonts'] = out
    plan['families'] = {role: v[0] for role, v in FAMILIES[lang].items()}
    json.dump(plan, open(plan_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(out), 'font chunks')
