#!/usr/bin/env python3
"""The catalogue of scene edits ("bảng cách edit") of this channel, and the mechanism that applies one to a scene.

Every entry is one scene layout of the owner's sample 00-video-mau/MAU-VU-AN.mp4 (the time in "sample" is where it
can be seen there), built from this repo's own desk items (photo, tag, header, card, stamp, big, text, line; centre
x, y in pixels of 1080×1920). In picks.json a scene names its edit — {"at": 6, "edit": "who", "why": "câu 6–8 giới
thiệu bốn nạn nhân", "items": […]} — and lists only the content: which picture, which words, on which spoken words
each appears. apply() then gives every item the template's x, y, size, tilt (and the scene its ground) unless Claude
wrote them himself, and refuses a scene that lacks the items the template is made of, with the recipe to copy.
"why" is a short Vietnamese reason for the owner; it is never drawn. A scene without "edit" is built exactly as
before.

An entry: vi (Vietnamese name), sample (m:ss in the sample), look, use (WHEN: by the meaning of the scene's lines),
needs / most ({"photo" | "card:note" …: count}), check (a function → error text), scene (defaults of the scene
itself, e.g. the black ground), slots (defaults of the n-th item of a kind: a list, or for tags a dict by colour
with "*" for the others), all (defaults of every item of a kind), recipe (the JSON Claude copies; AGENT_CRIME.md
§2.4 prints the same table: python3 scripts/crime/edits.py). A template has a fixed number of places: an item beyond
them must carry its own x and y. In a scene with an edit, {"line": [0, 2]} joins the 1st and 3rd photo of the scene
with a red string (without an edit a line is two points, as before).
"""
import copy, json, re

KINDS = ('photo', 'tag', 'header', 'card', 'stamp', 'big', 'text', 'line')
PICS = ('photo',)                      # "pic": a picture
COLOR0 = 'yellow'                      # colour of a tag that names none
CYCLE = False                          # places are pixels: they are never used twice
PLACE = ('x', 'y')                     # what an item beyond the template's places must carry
GROUPS = {'photo': {'w': ('h',), 'h': ('w',)}}   # Claude sized the photo himself: the other side follows the picture
LABEL = {'photo': 'ảnh (photo)', 'pic': 'ảnh (photo)', 'tag': 'nhãn (tag)', 'header': 'tiêu đề (header)', 'card': 'tờ giấy (card)',
         'stamp': 'dấu đỏ (stamp)', 'big': 'số lớn (big)', 'text': 'chữ lớn (text)', 'line': 'dây đỏ (line)'}


def style_of(it):
    c = it.get('card')
    return (c.get('style', 'paper') if isinstance(c, dict) else 'paper') if 'card' in it else None


def finish(sc, n, fail):
    """{"line": [0, 2]} → the red string between the 1st and 3rd photo of the scene (pinned near their top edge)."""
    photos = [it for it in sc.get('items') or [] if 'photo' in it]
    for it in sc.get('items') or []:
        v = it.get('line')
        if isinstance(v, list) and len(v) == 2 and all(isinstance(q, int) for q in v):
            if not all(0 <= q < len(photos) and 'x' in photos[q] and 'y' in photos[q] for q in v):
                fail(f'cảnh {n}: "line" {v} phải nối hai ảnh có trong cảnh (đánh số từ 0 theo thứ tự ảnh)')
            it['line'] = [[photos[q]['x'], round(photos[q]['y'] - photos[q].get('h', 0) / 2 + 30)] for q in v]
    return sc


def _marks(sc):
    if not any(it.get('marks') or it.get('zoom') for it in sc.get('items') or [] if 'photo' in it):
        return 'ảnh phải có "marks" (vòng khoanh chi tiết) hoặc "zoom" (phóng vào chi tiết)'


def _rows(key, what):
    def f(sc):
        rows = [r for it in sc.get('items') or [] if isinstance(it.get('card'), dict) for r in it['card'].get('rows') or []]
        if not any(isinstance(r, dict) and r.get(key) is not None for r in rows): return what
    return f


GRID = [{'x': x, 'y': y} for y in (1030, 1130, 1230) for x in (230, 540, 850)]
BOARD = [{'x': 290, 'y': 380, 'w': 400, 'h': 290, 'rot': -2}, {'x': 790, 'y': 420, 'w': 400, 'h': 290, 'rot': 2.5},
         {'x': 290, 'y': 790, 'w': 400, 'h': 290, 'rot': 1.5}, {'x': 790, 'y': 830, 'w': 400, 'h': 290, 'rot': -1.5},
         {'x': 290, 'y': 1200, 'w': 400, 'h': 290, 'rot': -1}, {'x': 790, 'y': 1240, 'w': 400, 'h': 290, 'rot': 2}]
EDITS = {
 'hook': {
  'vi': 'mở đầu', 'sample': '0:00–0:11',
  'look': 'nền đen, một ảnh đứng lớn; nhãn dán dần thành hai hàng dưới ảnh, mỗi thứ giọng đọc kể một nhãn; nhãn trắng con số ở mép trên ảnh',
  'use': 'MỞ ĐẦU: 2–3 câu đầu kể điều lạ của vụ án, liệt kê những thứ để lại, rồi con số gây tò mò',
  'needs': {'photo': 1, 'tag': 2}, 'most': {'photo': 1}, 'scene': {'bg': 'black'},
  'slots': {'photo': [{'x': 540, 'y': 640, 'w': 700, 'h': 880, 'rot': -1}],
            'tag': {'white': [{'x': 540, 'y': 215, 'size': 60}], '*': [{'x': x, 'y': y} for y in (1150, 1250, 1350) for x in (250, 540, 830)]}},
  'recipe': {'at': 1, 'edit': 'hook', 'why': '…', 'items': [
      {'photo': 'house'}, {'tag': '血痕', 'color': 'red', 'at': '2:血痕'}, {'tag': 'DNA', 'at': '2:DNA'}, {'tag': '指紋', 'at': '2:指紋'},
      {'tag': '25年以上', 'color': 'white', 'at': '3:25年'}]}},
 'chapter': {
  'vi': 'tiêu đề chương', 'sample': '0:12, 3:18',
  'look': 'tiêu đề giấy xé một mình giữa mặt bàn, dòng nhỏ đánh máy ở trên (loại hồ sơ + năm)',
  'use': 'CHUYỂN PHẦN: câu gọi tên vụ án, hoặc mở một phần mới (phân tích năm 2025, phiên tòa…)',
  'needs': {'header': 1}, 'most': {'photo': 0, 'card': 0},
  'slots': {'header': [{'x': 540, 'y': 800, 'size': 76}], 'tag': {'*': [{'x': 540, 'y': 1010}]}},
  'recipe': {'at': 4, 'edit': 'chapter', 'why': '…', 'items': [{'header': '世田谷一家', 'kicker': 'ファイル 2000'}]}},
 'where': {
  'vi': 'tiêu đề + ảnh nơi xảy ra', 'sample': '0:14–0:17',
  'look': 'tiêu đề giấy xé ở trên, một ảnh ngang của nơi xảy ra; nhãn đen tên nơi chốn bên trái dưới ảnh, nhãn đỏ tình trạng bên phải',
  'use': 'NƠI CHỐN: câu nói vụ án xảy ra ở đâu (thành phố, khu, ngôi nhà) và tình trạng của nó (chưa có lời giải)',
  'needs': {'photo': 1, 'tag': 1}, 'most': {'photo': 1},
  'slots': {'header': [{'x': 540, 'y': 230, 'size': 62}], 'photo': [{'x': 540, 'y': 780, 'w': 780, 'h': 560, 'rot': 1.2}],
            'tag': {'red': [{'x': 800, 'y': 1180, 'size': 56}], '*': [{'x': 290, 'y': 1150}, {'x': 330, 'y': 1260}]}},
  'recipe': {'at': 4, 'edit': 'where', 'why': '…', 'items': [
      {'header': '世田谷一家殺害事件', 'kicker': 'ファイル 2000'}, {'photo': 'house'},
      {'tag': '東京・世田谷区', 'color': 'black', 'at': '4:東京'}, {'tag': '未解決', 'color': 'red', 'at': '5:未解決'}]}},
 'who': {
  'vi': 'tờ giấy tên và tuổi', 'sample': '0:18–0:31',
  'look': 'tờ giấy kem: dòng đầu đánh máy ngày giờ, rồi từng dòng tên + tuổi hiện ra khi được đọc; một nhãn đỏ ở góc dưới',
  'use': 'NGƯỜI / NGÀY THÁNG: câu giới thiệu nạn nhân, những người liên quan, tên, tuổi, ngày xảy ra',
  'needs': {'card:paper': 1}, 'most': {'photo': 0},
  'slots': {'header': [{'x': 540, 'y': 200}], 'card': [{'x': 540, 'y': 760, 'w': 860, 'h': 660, 'rot': -0.6}],
            'tag': {'*': [{'x': 780, 'y': 1200}]}},
  'recipe': {'at': 6, 'edit': 'who', 'why': '…', 'items': [
      {'card': {'head': '12月30日 → 31日', 'rows': [{'text': '宮澤みきお', 'right': '44歳', 'at': '7:宮澤'}, {'text': '泰子', 'right': '41歳', 'at': '7:泰子'}]}},
      {'tag': '自宅で', 'color': 'red', 'at': '8:自宅'}]}},
 'place': {
  'vi': 'ảnh hiện trường + giờ', 'sample': '0:32–0:35',
  'look': 'một ảnh ngang ở nửa trên; nhãn trắng giờ hoặc ngày ngay dưới ảnh bên trái, nhãn đỏ bên phải',
  'use': 'THỜI ĐIỂM / HIỆN TRƯỜNG: câu nói việc xảy ra lúc mấy giờ, ngày nào, ở chỗ nào của hiện trường; cơ quan điều tra hôm nay',
  'needs': {'photo': 1, 'tag': 1}, 'most': {'photo': 1},
  'slots': {'photo': [{'x': 540, 'y': 620, 'w': 820, 'h': 600, 'rot': -1}],
            'tag': {'white': [{'x': 330, 'y': 1020, 'size': 58}], 'red': [{'x': 740, 'y': 1130, 'size': 54}], '*': [{'x': 300, 'y': 250}, {'x': 780, 'y': 280}]}},
  'recipe': {'at': 9, 'edit': 'place', 'why': '…', 'items': [
      {'photo': 'street'}, {'tag': '午後11時ごろ', 'color': 'white', 'at': '9:11時'}, {'tag': '警視庁', 'color': 'black', 'at': '9:警視庁'}]}},
 'figure': {
  'vi': 'bóng người', 'sample': '0:36–0:43, 2:02–2:07',
  'look': 'một ảnh đứng ở giữa (bóng người, hành lang); nhãn ở hai góc trên, nhãn trắng dưới ảnh, nhãn đỏ dưới cùng',
  'use': 'CON NGƯỜI BÍ ẨN: câu nói về hung thủ chưa rõ mặt, nghi phạm, một nhận định về hắn (tàn bạo, bình tĩnh)',
  'needs': {'photo': 1, 'tag': 1}, 'most': {'photo': 1},
  'slots': {'photo': [{'x': 540, 'y': 700, 'w': 600, 'h': 860, 'rot': -1.5}],
            'tag': {'white': [{'x': 540, 'y': 1210, 'size': 58}], 'red': [{'x': 540, 'y': 1320, 'size': 54}], '*': [{'x': 260, 'y': 240}, {'x': 830, 'y': 270}]}},
  'recipe': {'at': 10, 'edit': 'figure', 'why': '…', 'items': [
      {'photo': 'hall', 'view': [0.2, 0, 0.8, 1]}, {'tag': '容疑者?', 'color': 'black', 'at': '10:容疑'},
      {'tag': '名前は不明', 'color': 'red', 'at': '11:名前'}]}},
 'fact': {
  'vi': 'bằng chứng + chữ lớn', 'sample': '0:44–0:51',
  'look': 'một ảnh rộng ở nửa trên; nhãn đỏ ở góc trên trái, rồi một chữ/số lớn bên dưới (kết quả), nhãn trắng ở góc dưới phải',
  'use': 'MỘT SỰ VIỆC CÓ BẰNG CHỨNG: câu nói điều gì đã xảy ra và cảnh sát tìm được gì (bị thương → máu → nhóm máu → DNA)',
  'needs': {'photo': 1, 'big': 1}, 'most': {'photo': 1, 'big': 1},
  'slots': {'photo': [{'x': 540, 'y': 640, 'w': 860, 'h': 560, 'rot': -2}], 'big': [{'x': 430, 'y': 1080, 'size': 150}],
            'tag': {'red': [{'x': 300, 'y': 330}], 'white': [{'x': 780, 'y': 1280}], '*': [{'x': 800, 'y': 330}, {'x': 300, 'y': 1300}]}},
  'recipe': {'at': 12, 'edit': 'fact', 'why': '…', 'items': [
      {'photo': 'lab'}, {'tag': '手のけが', 'color': 'red', 'at': '12:手'}, {'big': 'A型', 'text': '血液型', 'at': '13:A型'},
      {'tag': 'DNA 採取', 'color': 'white', 'at': '13:DNA'}]}},
 'pair': {
  'vi': 'ảnh lớn + ảnh nhỏ', 'sample': '0:52–0:57',
  'look': 'một ảnh lớn, ảnh thứ hai nhỏ nghiêng đè lên góc dưới phải khi được nhắc; hai nhãn vàng bên trái, nhãn đỏ kết luận ở trên cùng',
  'use': 'HAI THỨ ĐI CÙNG NHAU: câu nêu hai dấu vết, hai người, hai nơi (vân tay và dấu giày) rồi rút ra một kết luận',
  'needs': {'photo': 2, 'tag': 1}, 'most': {'photo': 2},
  'slots': {'photo': [{'x': 540, 'y': 700, 'w': 780, 'h': 560, 'rot': 1}, {'x': 820, 'y': 1160, 'w': 300, 'h': 300, 'rot': 6}],
            'tag': {'red': [{'x': 540, 'y': 250, 'size': 56}], '*': [{'x': 330, 'y': 1170}, {'x': 330, 'y': 1270}]}},
  'recipe': {'at': 14, 'edit': 'pair', 'why': '…', 'items': [
      {'photo': 'dusting'}, {'photo': 'finger', 'at': '14:指紋'}, {'tag': '家族以外の指紋', 'at': '14:指紋'},
      {'tag': '足跡は1種類', 'at': '14:一種類'}, {'tag': '犯人は1人', 'color': 'red', 'at': '15:一人'}]}},
 'list': {
  'vi': 'ảnh + lưới nhãn', 'sample': '1:02–1:11',
  'look': 'một ảnh ngang ở nửa trên; bên dưới là lưới nhãn ba cột, mỗi món được đọc hiện một nhãn; nhãn trắng ở dưới cùng',
  'use': 'LIỆT KÊ: câu đọc một dãy đồ vật hoặc chi tiết (áo, mũ, khăn, túi, giày…), từ 3 món trở lên',
  'needs': {'photo': 1, 'tag': 3}, 'most': {'photo': 1},
  'slots': {'photo': [{'x': 540, 'y': 560, 'w': 800, 'h': 600, 'rot': -1}], 'tag': {'white': [{'x': 540, 'y': 1350, 'size': 50}], '*': GRID}},
  'recipe': {'at': 16, 'edit': 'list', 'why': '…', 'items': [
      {'photo': 'clothes'}, {'tag': 'トレーナー', 'at': '16:トレーナー'}, {'tag': '帽子', 'at': '16:帽子'}, {'tag': 'マフラー', 'at': '16:マフラー'},
      {'tag': 'ポーチ', 'at': '17:ポーチ'}, {'tag': '靴は27.5cm', 'color': 'white', 'at': '17:27.5'}]}},
 'number': {
  'vi': 'số lớn', 'sample': '1:12–1:23',
  'look': 'nhãn trắng tên món đồ ở trên; các con số lớn hiện lần lượt bên dưới (đếm lên), mỗi số một dòng chú thích; nhãn đỏ ở góc dưới',
  'use': 'CON SỐ: câu có số đếm, số lượng, tỉ lệ (130 chiếc, 10 chiếc ở Tokyo) — tối đa 3 số',
  'needs': {'big': 1}, 'most': {'photo': 0, 'big': 3},
  'slots': {'big': [{'x': 500, 'y': 640}, {'x': 480, 'y': 940}, {'x': 480, 'y': 1230}],
            'tag': {'white': [{'x': 540, 'y': 320, 'size': 58}], 'red': [{'x': 820, 'y': 1400}], '*': [{'x': 800, 'y': 460}]}},
  'recipe': {'at': 18, 'edit': 'number', 'why': '…', 'items': [
      {'tag': '犯人のトレーナー', 'color': 'white', 'at': '18:トレーナー'}, {'big': '130', 'text': '着\n全国', 'at': '18:130'},
      {'big': '10', 'text': '着\n東京', 'at': '19:10着'}, {'tag': 'わずか', 'color': 'red', 'at': '19:わずか'}]}},
 'object': {
  'vi': 'một đồ vật', 'sample': '1:38–1:49, 3:04–3:15',
  'look': 'một ảnh đồ vật lớn, hơi nghiêng; nhãn vàng tên gọi ở góc trên, nhãn trắng số đo hoặc tên riêng dưới ảnh, nhãn đỏ dưới cùng',
  'use': 'MỘT ĐỒ VẬT: câu tả một vật chứng (con dao, cái túi, chiếc giày), tên gọi, kích thước, nơi sản xuất',
  'needs': {'photo': 1, 'tag': 1}, 'most': {'photo': 1},
  'slots': {'photo': [{'x': 540, 'y': 680, 'w': 820, 'h': 620, 'rot': 2}],
            'tag': {'white': [{'x': 540, 'y': 1130, 'size': 58}], 'red': [{'x': 540, 'y': 1250}], '*': [{'x': 300, 'y': 270}, {'x': 780, 'y': 300}, {'x': 540, 'y': 1350}]}},
  'recipe': {'at': 20, 'edit': 'object', 'why': '…', 'items': [
      {'photo': 'knife'}, {'tag': '柳刃包丁', 'at': '20:柳刃'}, {'tag': '関孫六 銀寿', 'color': 'white', 'at': '20:関孫六'}]}},
 'detail': {
  'vi': 'khoanh chi tiết', 'sample': '1:50–2:01',
  'look': 'một ảnh lớn; vòng vàng (hoặc đỏ) khoanh chi tiết đúng lúc được nhắc; nhãn vàng dưới ảnh hai bên, nhãn trắng dưới cùng',
  'use': 'CHỈ VÀO MỘT CHI TIẾT: câu nói "trên đó có…", một vết, một chỗ đáng chú ý trong ảnh hoặc tài liệu',
  'needs': {'photo': 1}, 'most': {'photo': 1}, 'check': _marks,
  'slots': {'photo': [{'x': 540, 'y': 640, 'w': 820, 'h': 820, 'rot': -1}],
            'tag': {'white': [{'x': 330, 'y': 1300, 'size': 54}], 'red': [{'x': 780, 'y': 1300}], '*': [{'x': 300, 'y': 1160}, {'x': 770, 'y': 1160}]}},
  'recipe': {'at': 21, 'edit': 'detail', 'why': '…', 'items': [
      {'photo': 'cloth', 'marks': [{'at': '21:ハンカチ', 'box': [0.1, 0.5, 0.45, 0.8]}]},
      {'tag': '黒いハンカチ', 'at': '21:ハンカチ'}, {'tag': '切れ目 約3cm', 'color': 'white', 'at': '21:切れ目'}]}},
 'compare': {
  'vi': 'so sánh + dấu đỏ', 'sample': '2:08–2:15',
  'look': 'tờ giấy kem với hai dòng đối chiếu hiện lần lượt, rồi dấu đỏ kết luận đóng xuống dưới tờ giấy',
  'use': 'SO SÁNH / MÂU THUẪN: câu đối chiếu hai thứ và có kết luận (DNA không trùng, lời khai không khớp, chưa xác nhận)',
  'needs': {'card': 1, 'stamp': 1}, 'most': {'photo': 0},
  'slots': {'header': [{'x': 540, 'y': 230, 'size': 60}], 'card': [{'x': 540, 'y': 700, 'w': 820, 'h': 420, 'size': 52}],
            'stamp': [{'x': 620, 'y': 1040, 'size': 60}], 'tag': {'*': [{'x': 330, 'y': 1250}]}},
  'recipe': {'at': 22, 'edit': 'compare', 'why': '…', 'items': [
      {'card': {'head': 'DNA 鑑定', 'rows': [{'text': '包丁を買った男', 'at': '22:男'}, {'text': '現場のDNA', 'at': '23:現場'}]}},
      {'stamp': '不一致', 'at': '23:一致'}]}},
 'statement': {
  'vi': 'một câu then chốt', 'sample': '2:16–2:19',
  'look': 'mặt bàn trống, chỉ một nhãn đỏ to ở giữa',
  'use': 'CÂU CHUYỂN: một câu ngắn báo điều sắp tới, bước ngoặt ("そして犯人は、すぐには逃げなかった") — không có vật gì để cho xem',
  'needs': {'tag': 1}, 'most': {'photo': 0, 'card': 0, 'tag': 2},
  'slots': {'tag': {'*': [{'x': 540, 'y': 820, 'size': 76, 'color': 'red', 'rot': -2}, {'x': 540, 'y': 980, 'size': 50, 'color': 'white'}]}},
  'recipe': {'at': 24, 'edit': 'statement', 'why': '…', 'items': [{'tag': 'すぐには逃げなかった', 'at': '24:すぐ'}]}},
 'actions': {
  'vi': 'giấy ghi việc hắn làm', 'sample': '2:20–2:35',
  'look': 'nhãn đỏ ở trên; tờ giấy kẻ dòng chữ viết tay xanh, mỗi việc được đọc là một dòng có dấu ✓; có thể thêm một ảnh nhỏ ở góc dưới',
  'use': 'CHUỖI HÀNH ĐỘNG: câu kể lần lượt những việc một người đã làm (ăn, dùng máy tính, lục giấy tờ)',
  'needs': {'card:note': 1}, 'most': {'photo': 1},
  'slots': {'card': [{'x': 540, 'y': 720, 'w': 820, 'h': 560, 'size': 50, 'rot': -1}], 'photo': [{'x': 800, 'y': 1230, 'w': 380, 'h': 300, 'rot': 4}],
            'tag': {'red': [{'x': 540, 'y': 250, 'size': 52}], '*': [{'x': 300, 'y': 1180}]}},
  'recipe': {'at': 25, 'edit': 'actions', 'why': '…', 'items': [
      {'tag': 'すぐには逃げなかった', 'color': 'red', 'at': '25:すぐ'},
      {'card': {'style': 'note', 'rows': [{'text': '食べ物を食べた', 'check': True, 'at': '26:食べ物'}, {'text': 'トイレを使った', 'check': True, 'at': '26:トイレ'}]}}]}},
 'timeline': {
  'vi': 'ảnh + thẻ giờ giấc', 'sample': '2:36–2:55',
  'look': 'một ảnh ở nửa trên; thẻ giấy nhỏ ở nửa dưới với từng mốc giờ, dòng bị gạch đỏ khi lời kể sửa lại; nhãn đỏ ở góc dưới',
  'use': 'MỐC THỜI GIAN: câu có hai mốc giờ hoặc ngày trở lên (01:18, khoảng 10:00), trình tự trước – sau, điều chưa chắc',
  'needs': {'photo': 1, 'card': 1}, 'most': {'photo': 1},
  'slots': {'photo': [{'x': 540, 'y': 560, 'w': 760, 'h': 600, 'rot': 0.8}], 'card': [{'x': 540, 'y': 1150, 'w': 760, 'h': 300, 'size': 48}],
            'tag': {'red': [{'x': 760, 'y': 1390}], '*': [{'x': 800, 'y': 230}]}},
  'recipe': {'at': 27, 'edit': 'timeline', 'why': '…', 'items': [
      {'photo': 'crt'}, {'card': {'rows': [{'text': '01:18', 'right': 'ネット接続', 'at': '27:1時'},
                                           {'text': '10:00ごろ', 'right': '再び接続', 'at': '27:朝10時', 'strike': '28:意図'}]}},
      {'tag': '意図しない接続?', 'color': 'red', 'at': '28:意図'}]}},
 'span': {
  'vi': 'thẻ nhỏ khoảng thời gian', 'sample': '3:28–3:31, 3:42–3:45',
  'look': 'tiêu đề ở trên, một thẻ giấy nhỏ ở giữa với một hai dòng (dòng quan trọng màu đỏ); nhãn vàng ghi chú bên dưới',
  'use': 'KHOẢNG THỜI GIAN / TUỔI / ƯỚC TÍNH: câu nói bao nhiêu năm đã qua, tuổi lúc đó và bây giờ, một ước tính',
  'needs': {'card': 1}, 'most': {'photo': 0, 'stamp': 0},
  'slots': {'header': [{'x': 540, 'y': 230, 'size': 60}], 'card': [{'x': 540, 'y': 720, 'w': 820, 'h': 360, 'size': 54, 'rot': 0.8}],
            'tag': {'*': [{'x': 760, 'y': 1010}]}},
  'recipe': {'at': 29, 'edit': 'span', 'why': '…', 'items': [
      {'header': '新しいDNA分析', 'kicker': '2025'},
      {'card': {'rows': [{'text': '犯行当時', 'right': '30歳前後?', 'at': '30:30歳'}, {'text': '現在', 'right': '50〜60代?', 'color': 'red', 'at': '31:50代'}]}},
      {'tag': '報道による推定', 'at': '31:推定'}]}},
 'board': {
  'vi': 'bàn chứng cứ nối dây đỏ', 'sample': '2:56–3:03',
  'look': '3–6 ảnh nhỏ xếp hai cột, hiện từng cái khi được nhắc, nối nhau bằng dây đỏ; nhãn nhỏ dưới mỗi ảnh',
  'use': 'TỔNG HỢP CHỨNG CỨ: câu điểm lại nhiều thứ cảnh sát đang có (máu, DNA, vân tay, quần áo) — thường trước câu "nhưng không có tên"',
  'needs': {'photo': 3}, 'most': {'photo': 6},
  'slots': {'photo': BOARD, 'tag': {'white': [{'x': 540, 'y': 1440, 'size': 54}],
                                    '*': [{'x': b['x'], 'y': b['y'] + 168, 'size': 38} for b in BOARD]}},
  'recipe': {'at': 32, 'edit': 'board', 'why': '…', 'items': [
      {'photo': 'blood'}, {'photo': 'finger', 'at': '32:指紋'}, {'photo': 'soles', 'at': '33:靴'},
      {'tag': '血', 'at': '32:血'}, {'tag': '指紋', 'at': '32:指紋'}, {'tag': '靴の跡', 'at': '33:靴'},
      {'line': [0, 1], 'at': '32:指紋'}, {'line': [1, 2], 'at': '33:靴'}]}},
 'question': {
  'vi': 'ảnh + câu hỏi / điều ngược lại', 'sample': '3:58–4:05',
  'look': 'một ảnh lớn; nhãn trắng câu hỏi dưới ảnh, rồi nhãn đỏ câu trả lời bên dưới',
  'use': 'CÂU HỎI MỞ / ĐIỀU NGƯỢC LẠI: câu đặt câu hỏi cho người xem, hoặc lật lại điều vừa nói (không để lại gì? — ngược lại)',
  'needs': {'photo': 1, 'tag': 1}, 'most': {'photo': 1},
  'slots': {'photo': [{'x': 540, 'y': 680, 'w': 780, 'h': 760, 'rot': -1}],
            'tag': {'white': [{'x': 540, 'y': 1200, 'size': 58}], 'red': [{'x': 540, 'y': 1310, 'size': 56}], '*': [{'x': 300, 'y': 230}]}},
  'recipe': {'at': 34, 'edit': 'question', 'why': '…', 'items': [
      {'photo': 'house'}, {'tag': '何も残さなかった?', 'color': 'white', 'at': '34:何も'}, {'tag': 'すべてを残した', 'color': 'red', 'at': '35:すべて'}]}},
 'ending': {
  'vi': 'kết: chữ lớn trắng + đỏ', 'sample': '3:16–3:17',
  'look': 'nền đen, hai dòng chữ lớn gõ ra: dòng đầu trắng, dòng cuối đỏ',
  'use': 'KẾT: câu cuối — có gần như mọi thứ, trừ cái tên; câu hỏi còn bỏ ngỏ',
  'needs': {'text': 1}, 'most': {'photo': 0, 'card': 0}, 'scene': {'bg': 'black'},
  'slots': {'text': [{'x': 540, 'y': 860, 'size': 110}]},
  'recipe': {'at': 36, 'edit': 'ending', 'why': '…', 'items': [{'text': ['自分の名前を', {'text': '除いて。', 'color': 'red'}]}]}},
}


# ---------------------------------------------------------------------------------------------------------------
# The mechanism (the same in both crime repos; the catalogue above is each repo's own)
# ---------------------------------------------------------------------------------------------------------------
def names():
    return list(EDITS)


def kind_of(it):
    return next((k for k in KINDS if k in it), None)


def _count(items, what):
    """How many items are `what`: a kind ("photo"), "pic" (any picture kind) or "kind:style" ("card:lined")."""
    kind, _, style = what.partition(':')
    n = 0
    for it in items:
        k = kind_of(it)
        if kind == 'pic' and k in PICS: n += 1
        elif k == kind and (not style or style_of(it) == style): n += 1
    return n


def _label(what):
    kind, _, style = what.partition(':')
    return (LABEL.get(kind, kind) + (f' "{style}"' if style else ''))


def recipe(name):
    return json.dumps(EDITS[name]['recipe'], ensure_ascii=False)


def apply(sc, n, fail):
    """Scene `sc` (number n) of picks.json with "edit": a copy in which every item has the template's defaults for
    what Claude left out (position, tilt, size, colour), after checking that the name exists and that the scene has
    the items the template is made of. A scene without "edit" is returned untouched."""
    if 'edit' not in sc:
        return sc
    name = sc['edit']
    if not isinstance(name, str) or name not in EDITS:
        fail(f'cảnh {n}: không có kiểu edit {json.dumps(name, ensure_ascii=False)}. Các kiểu: {", ".join(EDITS)}')
    if not isinstance(sc.get('why', ''), str):
        fail(f'cảnh {n}: "why" phải là một câu ngắn (chữ)')
    ed = EDITS[name]
    sc = copy.deepcopy(sc)
    for k, v in (ed.get('scene') or {}).items(): sc.setdefault(k, copy.deepcopy(v))
    items = sc.get('items') or []
    for k, it in enumerate(items):
        if kind_of(it) is None: fail(f'cảnh {n}, mục {k + 1}: thiếu loại ({", ".join(KINDS)})')
    for what, least in (ed.get('needs') or {}).items():
        have = _count(items, what)
        if have < least:
            fail(f'cảnh {n}: kiểu edit "{name}" cần ít nhất {least} {_label(what)} (đang có {have}). Mẫu: {recipe(name)}')
    for what, most in (ed.get('most') or {}).items():
        have = _count(items, what)
        if have > most:
            fail(f'cảnh {n}: kiểu edit "{name}" chỉ dùng tối đa {most} {_label(what)} (đang có {have}). Mẫu: {recipe(name)}')
    err = ed['check'](sc) if ed.get('check') else None
    if err: fail(f'cảnh {n}: kiểu edit "{name}": {err}. Mẫu: {recipe(name)}')

    slots, seen = ed.get('slots') or {}, {}
    pic_index = [k for k, it in enumerate(items) if kind_of(it) in PICS]
    for k, it in enumerate(items):
        kind = kind_of(it)
        table = slots.get(kind, slots.get('pic') if kind in PICS else None)
        key = 'pic' if kind not in slots and kind in PICS else kind
        dflt = {}
        if isinstance(table, dict):                 # by colour: {'white': […], 'red': […], '*': […]}
            col = it.get('color', COLOR0)
            col = col if col in table else '*'
            table, key = table.get(col), f'{key}/{col}'
        if table:
            i = seen.get(key, 0); seen[key] = i + 1
            if i < len(table) or CYCLE:
                dflt = dict(table[i % len(table)])
            elif any(p not in it for p in PLACE):
                fail(f'cảnh {n}, mục {k + 1}: kiểu edit "{name}" chỉ có sẵn {len(table)} chỗ cho {LABEL.get(kind, kind)}'
                     f'{" màu này" if "/" in key else ""}; mục thừa phải tự ghi {", ".join(PLACE)}')
        dflt.update((ed.get('all') or {}).get(kind) or {})
        for mine, drop in GROUPS.get(kind, {}).items():   # Claude placed it himself: the template's place is not mixed in
            if mine in it:
                for g in drop: dflt.pop(g, None)
        for g, v in dflt.items():
            if isinstance(v, list) and len(v) == 2 and v[0] == 'pic':   # "on the 2nd picture of this scene" → item index
                if v[1] >= len(pic_index): continue
                v = pic_index[v[1]]
            it.setdefault(g, v)
    return finish(sc, n, fail) if finish else sc


def first_line(sc, default=1):
    """The script line a scene starts with (its "at": 3, 3.5, "3/Wort" or "3:言葉")."""
    m = re.match(r'\s*(\d+)', str(sc.get('at', default)))
    return int(m.group(1)) if m else default


def listing(scenes_in, text, bounds=None):
    """edits.md: one row per scene — number, time, first line, edit, why — for the closing comment, so the owner can
    answer "cảnh 5 đổi sang kiểu …". text = {line number: line}; bounds = scene start times (+ the end) or None."""
    rows, prev = [], None
    for j, sc in enumerate(scenes_in):
        name = sc.get('edit')
        line = (text.get(first_line(sc)) or '').replace('|', '/')
        if len(line) > 46: line = line[:45].rstrip() + '…'
        when = f'{bounds[j]:.0f}–{bounds[j + 1]:.0f} s' if bounds else ''
        kind = f'`{name}` — {EDITS[name]["vi"]}' if name in EDITS else '—'
        why = str(sc.get('why') or '').replace('|', '/').replace('\n', ' ')
        if name and name == prev: why = (why + ' ' if why else '') + '⚠️ trùng kiểu với cảnh trước'
        rows.append(f'| {j + 1} | {when} | {line} | {kind} | {why} |')
        prev = name
    return ('| Cảnh | Lúc | Câu đầu | Kiểu edit | Vì sao |\n|---|---|---|---|---|\n' + '\n'.join(rows) + '\n\n'
            'Muốn đổi kiểu của một cảnh: viết bình luận, ví dụ "cảnh 5 đổi sang kiểu `number`". Các kiểu: '
            + ', '.join(f'`{k}` ({v["vi"]})' for k, v in EDITS.items()) + '.\n')


def repeats(scenes_in):
    """Scene numbers that use the same edit as the scene before (the board should change shape every scene)."""
    return [j + 2 for j, (a, b) in enumerate(zip(scenes_in, scenes_in[1:])) if b.get('edit') and b.get('edit') == a.get('edit')]


def table_md():
    """The catalogue as the table of AGENT_CRIME.md (python3 scripts/crime/edits.py prints it)."""
    out = ['| `edit` | Trông thế nào (mẫu, phút:giây) | Dùng KHI các câu của cảnh nói về… | Công thức (chép rồi thay nội dung) |', '|---|---|---|---|']
    for k, v in EDITS.items():
        out.append(f'| `{k}`<br>{v["vi"]} | {v["look"]} ({v["sample"]}) | {v["use"]} | `{recipe(k).replace("|", "¦")}` |')
    return '\n'.join(out)


if __name__ == '__main__':
    print(table_md())
