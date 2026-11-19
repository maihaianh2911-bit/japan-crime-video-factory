# japan-crime-video-factory — notes for Claude

## Iron rules (owner, 16/11/2026) — they come before everything else in this file
1. **The video is in the channel's language: Japanese (tiếng Nhật).** The voice is the Japanese voice of `prompts/channel.json`, and the script lines, subtitles and
   on-screen text are in Japanese (tiếng Nhật). A script that arrives in another language is translated faithfully into Japanese (tiếng Nhật)
   first. Never a voice or text of another language: check the language of `lines` and the voice before the voice
   step, and again on the finished video. A video in the wrong language is not delivered: fix it and render again.
2. **No video under 60 seconds.** Before the voice step, estimate the length from the script (use the seconds per
   line of this channel's earlier videos); after the voice step, read the real length of the speech (the machine
   comment gives it). If the video would be under 60 seconds, **write the script longer** (more true facts and
   detail on the same subject, in the owner's tone, nothing invented) until it passes 60 seconds, tell the owner on
   the issue what was added, and only then go on. This is the one exception to "never change the owner's script".
   Never render or deliver a video under 60 seconds. Only exception: a trial or sample video — the owner says so,
   or the issue title or notes say `thử`, `mẫu`, `test` or `demo`.
3. **Every video is vertical (1080×1920); on this channel (kênh 5, Vụ án) 61–160 seconds long** (owner, 18/11/2026:
   "tất cả các kênh đều làm dạng dọc, 80-160s thôi", then for this channel: "kênh 5 rút xuống ít nhất 61s là đc").
   Write the script for that length: under 61 s add true scenes and details of the same story (never padding), over
   160 s cut repetition. Trial or sample videos are the exception, as in rule 2.

Read `docs/HANDOVER.md` first (the owner, their standing decisions, the current state), then `AGENT_CRIME.md` (how
a video is made). The owner is Vietnamese and not technical: answer in short, simple Vietnamese, no jargon.

This repo makes one thing: vertical true-crime shorts with a **tiếng Nhật** voice and small white subtitles timed
to it, laid out as the owner's sample `00-video-mau/MAU-VU-AN.mp4` (new sample of 14/11/2026: a case file on a dark
desk — black-and-white photos with white borders, yellow hand-written tags, typed paper cards, torn-paper titles, red
stamps — each laid down as the voice names it). Real pictures first; where none exists, AI illustrations, always tagged `イメージ（AI生成）` and never
showing a real person's face. One issue `[Vụ án] …` = one video; the machine steps run on GitHub Actions
(`crime.yml`), Claude's steps are in `AGENT_CRIME.md`. Its twin `maihaianh2911-bit/germany-crime-video-factory` makes true-crime videos in tiếng Đức. Each repo got **its own case-file style on
14/11/2026** (from different sessions): the style code differs (`build.py`, `layout.py`, `prep.py`, `captions.py`, fonts,
`preview.py`, `CrimeV.tsx`) and so does the `picks.json` format; the pipeline code (`run.py`, `vn11.py`, `tts_lines.py`,
`find_images.py`, `wake_claude.sh`, the workflows) is the same. The owner has **not decided** whether the two
styles become one: never port style code between them, and ask before unifying.

## When you were started by GitHub (a Claude task, nobody in the chat)
Follow `AGENT_NIGHTLY.md` of this repo (its first check lists the `crime-*` issues waiting), then `AGENT_CRIME.md`.
Nobody answers questions, so do not ask; comments go on the issues (🤖, Vietnamese).

## When the owner pastes a script in a chat
1. Create one issue in `maihaianh2911-bit/japan-crime-video-factory`: title `[Vụ án] <case title in tiếng Nhật> — <main idea in Vietnamese>`, body with
   the sections of `docs/CHATGPT.md` (Vụ án / Kịch bản = the script exactly as pasted / Giọng đọc / Ghi chú =
   wishes from the chat). No labels: the workflow adds them, and its start job wakes the Claude task at once.
2. Right after creating the issue, add `crime-busy` (so that task leaves it to you; keep it while you work and wait
   here: the claim counts for 2 hours from when the label was
   added, so on a longer chat remove and add it again; remove it when you stop), then do Claude's steps of `AGENT_CRIME.md` for that issue right away:
   `script.json` → wait for the voice and pictures (~15–25 min; first video, 36 lines: 17 min) → `picks.json`, with the
   framing preview → wait for the render (~15–20 min for 2 minutes of video) → check the scene sheet → closing comment. While a machine step runs, say so in one line
   and wait; if the owner does not want to wait, stop after any step: the Claude task continues from the labels
   when GitHub calls it.
3. Give the owner the links to the video (view + download), the subtitles, the posting caption (`caption.txt`, owner
   16/11/2026: every video comes with it) and the picture credits.

Quality first: look at every picture yourself, read each scene's lines and choose its scene edit by their meaning
(the catalogue in `AGENT_CRIME.md` §2.4, `"edit"` + `"why"` in `picks.json`), preview before rendering, **review every picture against the words spoken while it is on screen**
(`scripts/crime/review.py`, `AGENT_CRIME.md` §2.7b, owner 18/11/2026) and paste `edits.md` in the closing comment.

## A video the owner sends (owner, 19/11/2026, for every repo)
"nếu repo nào đc dựng bằng cách remix video hoặc tao có gửi video, có thể sử dụng hình ảnh/video trong video tao gửi":
when a video of this repo is made from a video the owner sent (a remix, or a video sent in the chat), **the pictures
and the footage of that video may be used** in ours, beside the pictures of our own search. Still the rule: never its
voice or its music; a frame with the source's caption, logo or watermark over the picture is cropped clean or left;
credited 元動画; told in our own words (YouTube penalises reused content: the more of the source a video shows, the
higher that risk, told to the owner). The shared note is in `maihaianh2911-bit/japan-video-factory` →
`docs/KENH-NHAT.md`; `tools/video_frames.py` of `japan-news-video-factory` lays out the shots of a video to choose
from (this repo has no such tool yet: cut the frames with ffmpeg and save them in `crime/<N>/own/`, the
`own/<file>` pictures of `AGENT_CRIME.md`).

## Changing the pipeline
Before pushing to `main`: `python3 tests/crime_units.py`, `python3 tests/crime_smoke.py --still` (with
`FONTSOURCE` set and `bash scripts/crime/get_fonts.sh "$FONTSOURCE"`), `python3 -m compileall -q scripts tests`,
`npm run check`. Until the owner decides on one style, code changes are made **in each repo separately** (a pipeline fix: the same
change in both, by hand; style code: only in its own repo). Never touch secrets. Comments posted on GitHub
start with 🤖 (they come from the owner's account). No pull requests unless asked. The session cannot delete
branches or tags.
