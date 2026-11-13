# japan-crime-video-factory — notes for Claude

Read `docs/HANDOVER.md` first (the owner, their standing decisions, the current state), then `AGENT_CRIME.md` (how
a video is made). The owner is Vietnamese and not technical: answer in short, simple Vietnamese, no jargon.

This repo makes one thing: vertical true-crime shorts with a **tiếng Nhật** voice and short yellow captions timed
to it, laid out as the owner's sample `00-video-mau/MAU-VU-AN.mp4` (old photographs, a new picture every 3–4 s, the
case title on top). Real pictures first; where none exists, AI illustrations, always tagged `イメージ（AI生成）` and never
showing a real person's face. One issue `[Vụ án] …` = one video; the machine steps run on GitHub Actions
(`crime.yml`), Claude's steps are in `AGENT_CRIME.md`. Its twin `maihaianh2911-bit/germany-crime-video-factory` makes the same videos in tiếng Đức; the
code is the same, only `prompts/channel.json` (language, voice, AI tag) and `prompts/readings.json` differ.

## When you were started by GitHub (a Claude task, nobody in the chat)
Follow `AGENT_NIGHTLY.md` of this repo (its first check lists the `crime-*` issues waiting), then `AGENT_CRIME.md`.
Nobody answers questions, so do not ask; comments go on the issues (🤖, Vietnamese).

## When the owner pastes a script in a chat
1. Create one issue in `maihaianh2911-bit/japan-crime-video-factory`: title `[Vụ án] <case title in tiếng Nhật> — <main idea in Vietnamese>`, body with
   the sections of `docs/CHATGPT.md` (Vụ án / Kịch bản = the script exactly as pasted / Giọng đọc / Ghi chú =
   wishes from the chat). No labels: the workflow adds them.
2. Do Claude's steps of `AGENT_CRIME.md` for that issue right away (claim with `crime-busy` as written there):
   `script.json` → wait for the voice and pictures (~15–25 min) → `picks.json`, with the framing preview → wait for
   the render (~15–25 min) → check the shot sheet → closing comment. While a machine step runs, say so in one line
   and wait; if the owner does not want to wait, stop after any step: the Claude task continues from the labels
   when GitHub calls it.
3. Give the owner the links to the video (view + download), the subtitles and the picture credits.

Quality first: look at every picture yourself, preview before rendering.

## Changing the pipeline
Before pushing to `main`: `python3 tests/crime_units.py`, `python3 tests/crime_smoke.py --still` (with
`FONTSOURCE` set and `bash scripts/crime/get_fonts.sh "$FONTSOURCE"`), `python3 -m compileall -q scripts tests`,
`npm run check`. Code changes go to both crime repos (same files). Never touch secrets. Comments posted on GitHub
start with 🤖 (they come from the owner's account). No pull requests unless asked. The session cannot delete
branches or tags.
