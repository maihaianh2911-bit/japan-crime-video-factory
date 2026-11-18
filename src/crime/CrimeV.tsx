import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Audio, Img, Sequence, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

// Vertical (1080×1920) true-crime short laid out as the owner's sample (00-video-mau/MAU-VU-AN.mp4, a case file of
// the Setagaya family murder): a dark wooden desk on which the evidence of each scene is laid down as the voice names
// it — black-and-white photographs with a white print border, yellow tape labels written by hand, paper cards with
// typed lines, torn-paper titles, red stamps, big numbers, red strings — dust and grain of old film over all, and the
// voice in a small white subtitle box at the bottom. AI illustrations carry a tag on the picture.
// The plan comes from scripts/crime/build.py (layout: scripts/crime/layout.py).
type View = [number, number, number, number];
type Base = { s: number; e?: number; x: number; y: number; rot: number };
export type Mark = { s: number; box: View; shape: 'ellipse' | 'rect'; color: 'yellow' | 'red' };
export type Photo = Base & { k: 'photo'; src: string; iw: number; ih: number; w: number; h: number; view: View;
  zoom?: { to: View; s: number; e: number }; drift: number; ai: boolean; credit: string; frame: 'white' | 'none'; marks: Mark[]; depth?: string; slides?: Slide[] };
// one of the pictures a photo frame shows in turn (build.py): its own region, start, end and move
export type Slide = { src: string; iw: number; ih: number; view: View; s: number; e: number; move: string; ai: boolean; credit: string; depth?: string };
export type Tag = Base & { k: 'tag'; text: string; color: 'yellow' | 'red' | 'white' | 'black'; size: number; font: Role };
export type Header = Base & { k: 'header'; title: string; kicker: string; size: number };
export type Row = { s: number; text: string; right: string; color: string; check: boolean; strike?: number };
export type Card = Base & { k: 'card'; style: 'paper' | 'note' | 'file'; head: string; rows: Row[]; w: number; h: number; size: number };
export type Stamp = Base & { k: 'stamp'; text: string; size: number };
export type Big = Base & { k: 'big'; num: string; text: string; size: number };
export type Text = Base & { k: 'text'; rows: { s: number; text: string; color: string }[]; size: number };
export type Line = Base & { k: 'line'; pts: [[number, number], [number, number]]; color: string };
export type Person = { name: string; sub: string; s: number; src?: string; iw?: number; ih?: number; focus?: [number, number] };
export type Roster = Base & { k: 'roster'; people: Person[]; title: string; kicker: string; pick: number; pick_s: number; note: string; rank: string; done: number[] };
export type Item = Photo | Tag | Header | Card | Stamp | Big | Text | Line | Roster;
export type Scene = { s: number; e: number; scene: number; bg: 'wood' | 'black'; push: number; items: Item[]; edit?: string };   // edit: name of the scene edit (picks.json), for the sheets only
export type Sub = { s: number; e: number; text: string; line: number };
type Role = 'sans' | 'serif' | 'mono' | 'hand';
type FontChunk = { family: string; file: string; range: string; weight: string; style: string };
export type PlanC = { duration: number; lang: 'ja' | 'de'; title: string; aiTag: string; bg: string; grain: string; scenes: Scene[];
  subs: Sub[]; voice: { s: number; src: string }[]; music: string | null; musicVolume: number; musicLoop?: boolean; fx?: { motion: boolean; depth: boolean; text: boolean }; quotes?: { s: number; e: number; text: string }[]; fonts: FontChunk[];
  families: Partial<Record<Role, string>> };

// layout.py
const SUB_Y = 1588, SUB_MAX_W = 960, BORDER = 12;
const SUB_SIZE = { ja: 40, de: 40 };
const YELLOW = '#f1c232', RED = '#c9252c', PAPER = '#e5dfd2', INK = '#1b1a18';
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const ease = (x: number) => { const p = clamp01(x); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const backOut = (x: number) => { const p = clamp01(x), c = 1.6; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
// a fixed pseudo-random number in [0, 1) for a seed (the same in every frame and every render)
const rnd = (n: number) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const hash = (s: string) => { let h = 7; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 100003; return h; };
const DEFAULT_FAM: Record<'ja' | 'de', Record<Role, string>> = {
  ja: { sans: 'Noto Sans JP', serif: 'Noto Serif JP', mono: 'M PLUS 1 Code', hand: 'Yusei Magic' },
  de: { sans: 'Source Sans 3', serif: 'Roboto Slab', mono: 'Space Mono', hand: 'Kalam' },
};

let fontsLoading: Promise<void> | null = null;
const useFonts = (plan: PlanC, fam: Record<Role, string>) => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const text = JSON.stringify(plan.scenes) + plan.subs.map((c) => c.text).join('') + plan.aiTag + '0123456789';
    (fontsLoading ??= (async () => {
      for (const c of plan.fonts)
        document.fonts.add(new FontFace(c.family, `url(${staticFile(c.file)}) format('woff2')`, { weight: c.weight, style: c.style, unicodeRange: c.range }));
      await Promise.all([900, 700, 500, 400].flatMap((wt) => Object.values(fam).map((f) => document.fonts.load(`${wt} 60px "${f}"`, text))));
    })()).then(() => continueRender(h)).catch((e) => cancelRender(e));
  }, [h, plan, fam]);
};

// text typed out from time s: characters shown at time t
const typed = (text: string, t: number, s: number, cps = 22) => {
  const n = [...text].length;
  const k = Math.floor((t - s) * Math.max(cps, n / 0.9));
  return k >= n ? text : [...text].slice(0, Math.max(0, k)).join('');
};

// torn paper edges: a polygon with jagged left and right sides (fixed per text)
const torn = (seed: number, jag = 1.6) => {
  const pts: string[] = [];
  for (let i = 0; i <= 6; i++) pts.push(`${(rnd(seed + i) * jag).toFixed(2)}% ${(i * 100 / 6).toFixed(1)}%`);
  for (let i = 6; i >= 0; i--) pts.push(`${(100 - rnd(seed + 50 + i) * jag).toFixed(2)}% ${(i * 100 / 6).toFixed(1)}%`);
  return `polygon(${pts.join(',')})`;
};

// region of the picture shown at time t: a zoom when asked for, else a slow push-in (by `drift` over the scene)
// picture effects of the plan (owner 18/11/2026, from japan-news): set once per frame by CrimeV
let FX = { motion: false, depth: false, text: false };
// motion: the camera moves quickly at first and then settles, instead of one even speed
const pace = (x: number) => (FX.motion ? 1 - Math.pow(1 - clamp01(x), 2.2) : clamp01(x));

const viewAt = (p: Photo, t: number, e: number): View => {
  if (p.zoom) {
    const k = ease((t - p.zoom.s) / Math.max(0.1, p.zoom.e - p.zoom.s));
    return p.view.map((v, i) => v + (p.zoom!.to[i] - v) * k) as View;
  }
  if (!p.drift) return p.view;
  const k = pace((t - p.s) / Math.max(0.5, e - p.s)) * p.drift / 2;
  const [a, b, c, d] = p.view, w = c - a, h = d - b;
  return [a + w * k, b + h * k, c - w * k, d - h * k];
};

// an item enters: fades in and settles from a little larger / turned (photos drop onto the desk, tags slap on)
const enter = (t: number, s: number, kind: Item['k']) => {
  const d = kind === 'tag' || kind === 'stamp' ? 0.16 : kind === 'photo' || kind === 'card' ? 0.32 : 0.26;
  const p = (t - s) / d;
  const from = kind === 'stamp' ? 1.7 : kind === 'tag' ? 1.3 : kind === 'photo' || kind === 'card' ? 1.08 : 1.12;
  const sc = kind === 'stamp' ? 1 + (from - 1) * (1 - easeOut(p)) : 1 + (from - 1) * (1 - backOut(p));
  return { opacity: clamp01(p * 1.6), scale: sc, turn: (1 - easeOut(p)) * (kind === 'photo' ? 2.5 : kind === 'tag' ? -3 : 0) };
};

// the region of a slide at time t, by its move (owner 18/11/2026: the pictures must move visibly): push in or pull back
// by a fifth, or travel across / up / down the picture at 1.2× — quick at first, then settling (motion)
const slideView = (sl: Slide, t: number): View => {
  const [a, b, c, d] = sl.view, W = c - a, H = d - b, k = pace((t - sl.s) / Math.max(0.8, sl.e - sl.s + 0.45));
  const box = (cx: number, cy: number, z: number): View => [cx - W * z / 2, cy - H * z / 2, cx + W * z / 2, cy + H * z / 2];
  const cx = (a + c) / 2, cy = (b + d) / 2, Z = 0.82, m = (1 - Z) / 2;
  switch (sl.move) {
    case 'push-in': return box(cx, cy, 1 - 0.2 * k);
    case 'pull-back': return box(cx, cy, 0.8 + 0.2 * k);
    case 'pan-right': return box(cx + W * m * (2 * k - 1), cy, Z);
    case 'pan-left': return box(cx - W * m * (2 * k - 1), cy, Z);
    case 'rise': return box(cx, cy - H * m * (2 * k - 1), Z);
    case 'fall': return box(cx, cy + H * m * (2 * k - 1), Z);
    default: return box(cx, cy, 1 - 0.04 * k);
  }
};

// one picture drawn in the frame through a region (flat, or with its depth map)
const Layer: React.FC<{ src: string; iw: number; ih: number; w: number; h: number; v: View; depth?: string; k: number; opacity?: number }> = ({ src, iw, ih, w, h, v, depth, k, opacity = 1 }) => {
  const [v0, v1, v2, v3] = v;
  const sx = w / ((v2 - v0) * iw), sy = h / ((v3 - v1) * ih), W = iw * sx, H = ih * sy;
  if (depth && FX.depth) {
    // depth: near things move outwards a little more than far things (2.5D, a map by prep.py)
    const id = `dm${hash(src)}`;
    return (
      <svg width={W} height={H} style={{ position: 'absolute', left: -v0 * W, top: -v1 * H, overflow: 'hidden', opacity }}>
        <filter id={id} x="0" y="0" width={W} height={H} filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feImage href={staticFile(depth)} x="0" y="0" width={W} height={H} preserveAspectRatio="none" result="map" />
          <feDisplacementMap in="SourceGraphic" in2="map" scale={0.1 * Math.max(W, H) * k} xChannelSelector="R" yChannelSelector="G" />
        </filter>
        <image href={staticFile(src)} x="0" y="0" width={W} height={H} preserveAspectRatio="none" filter={`url(#${id})`} />
      </svg>
    );
  }
  return <Img src={staticFile(src)} style={{ position: 'absolute', left: -v0 * W, top: -v1 * H, width: W, height: H, maxWidth: 'none', opacity }} />;
};

const PhotoV: React.FC<{ p: Photo; t: number; e: number; tag: string; sans: string; mono: string }> = ({ p, t, e, tag, sans, mono }) => {
  const slides: Slide[] = p.slides && p.slides.length ? p.slides
    : [{ src: p.src, iw: p.iw, ih: p.ih, view: p.view, s: p.s, e, move: p.drift ? 'push-in' : 'hold', ai: p.ai, credit: p.credit, depth: p.depth }];
  let i = 0;
  slides.forEach((sl, k) => { if (t >= sl.s) i = k; });
  const cur = slides[i], prev = i > 0 && t - cur.s < 0.45 ? slides[i - 1] : null;
  const fade = clamp01((t - cur.s) / 0.45);
  const viewOf = (sl: Slide, k: number): View => (k === 0 && p.zoom ? viewAt(p, t, e) : slideView(sl, t));
  const [v0, v1, v2, v3] = viewOf(cur, i);
  const depthK = (sl: Slide) => pace((t - sl.s) / Math.max(0.8, sl.e - sl.s + 0.45));
  const b = p.frame === 'white' ? BORDER : 0;
  return (
    <div style={{ position: 'relative', width: p.w + 2 * b, height: p.h + 2 * b, background: '#e8e5de', padding: b, boxSizing: 'border-box',
      boxShadow: '0 18px 40px rgba(0,0,0,.65), 0 3px 8px rgba(0,0,0,.5)' }}>
      <div style={{ position: 'relative', width: p.w, height: p.h, overflow: 'hidden', background: '#000' }}>
        {prev ? <Layer src={prev.src} iw={prev.iw} ih={prev.ih} w={p.w} h={p.h} v={viewOf(prev, i - 1)} depth={prev.depth} k={depthK(prev)} /> : null}
        <Layer src={cur.src} iw={cur.iw} ih={cur.ih} w={p.w} h={p.h} v={[v0, v1, v2, v3]} depth={cur.depth} k={depthK(cur)} opacity={prev ? fade : 1} />
        <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 50px rgba(0,0,0,.45)' }} />
        <svg width={p.w} height={p.h} style={{ position: 'absolute', left: 0, top: 0 }}>
          {(i === 0 ? p.marks : []).filter((mk) => t >= mk.s).map((mk, mi) => {
            const X = (f: number) => ((f - v0) / (v2 - v0)) * p.w, Y = (f: number) => ((f - v1) / (v3 - v1)) * p.h;
            const [a, bb, c, d] = mk.box;
            const draw = easeOut((t - mk.s) / 0.5);
            const st = { fill: 'none', stroke: mk.color === 'red' ? RED : YELLOW, strokeWidth: 6, strokeLinecap: 'round' as const,
              strokeDasharray: 1, strokeDashoffset: 1 - draw, filter: 'drop-shadow(0 0 4px rgba(0,0,0,.7))' };
            return mk.shape === 'rect'
              ? <rect key={mi} pathLength={1} x={X(a)} y={Y(bb)} width={X(c) - X(a)} height={Y(d) - Y(bb)} rx={6} style={st} />
              // turned by -90° so the ring starts drawing at the top: its radii are swapped to keep the box's shape
              : <ellipse key={mi} pathLength={1} cx={(X(a) + X(c)) / 2} cy={(Y(bb) + Y(d)) / 2} rx={(Y(d) - Y(bb)) / 2} ry={(X(c) - X(a)) / 2}
                  transform={`rotate(-90 ${(X(a) + X(c)) / 2} ${(Y(bb) + Y(d)) / 2})`} style={st} />;
          })}
        </svg>
        {cur.ai ? (
          <div style={{ position: 'absolute', right: 10, bottom: 10, padding: '3px 10px', background: 'rgba(0,0,0,.6)', color: 'rgba(255,255,255,.92)',
            fontFamily: `"${sans}"`, fontWeight: 500, fontSize: 21, letterSpacing: '0.02em', borderRadius: 3 }}>{tag}</div>
        ) : null}
      </div>
      {cur.credit ? (
        <div style={{ position: 'absolute', left: b, right: b, top: p.h + 2 * b + 6, fontFamily: `"${mono}", "${sans}"`, fontWeight: 400, fontSize: 17,
          color: 'rgba(225,218,205,.5)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cur.credit}</div>
      ) : null}
    </div>
  );
};

const TagV: React.FC<{ g: Tag; F: Record<Role, string>; lang: 'ja' | 'de' }> = ({ g, F, lang }) => {
  const look = {
    yellow: { bg: YELLOW, fg: INK, weight: 400 }, red: { bg: RED, fg: '#fff', weight: 700 },
    white: { bg: '#eeebe4', fg: INK, weight: 800 }, black: { bg: '#141312', fg: '#f2efe8', weight: 700 },
  }[g.color];
  const italic = g.font === 'serif' && lang === 'de';
  return (
    <div style={{ background: look.bg, color: look.fg, padding: `${g.size * 0.08}px ${g.size * 0.34}px`, whiteSpace: 'pre', textAlign: 'center',
      fontFamily: `"${F[g.font]}", "${F.sans}"`, fontWeight: g.font === 'hand' ? (lang === 'de' ? 700 : 400) : look.weight, fontStyle: italic ? 'italic' : 'normal',
      fontSize: g.size, lineHeight: 1.22, clipPath: torn(hash(g.text), 2.2), boxShadow: '0 4px 10px rgba(0,0,0,.45)',
      letterSpacing: g.font === 'mono' ? '0.04em' : '0.01em' }}>{g.text}</div>
  );
};

const HeaderV: React.FC<{ h: Header; t: number; F: Record<Role, string>; lang: 'ja' | 'de' }> = ({ h, t, F, lang }) => {
  const k = typed(h.kicker, t, h.s, 16);
  const ti = easeOut((t - h.s - (h.kicker ? 0.35 : 0)) / 0.3);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: h.size * 0.12 }}>
      {h.kicker ? (
        <div style={{ background: '#121110', color: '#f1eee7', padding: `${h.size * 0.06}px ${h.size * 0.3}px`, fontFamily: `"${F.mono}", "${F.sans}"`, fontWeight: 700,
          fontSize: h.size * 0.62, letterSpacing: '0.08em', textTransform: 'uppercase', whiteSpace: 'pre', minHeight: h.size * 0.75,
          minWidth: h.size * 0.62 * [...h.kicker].length * (lang === 'ja' ? 1.0 : 0.66) }}>{k}</div>
      ) : null}
      <div style={{ opacity: ti, transform: `translateX(${(1 - ti) * -40}px)`, background: '#ece9e2', color: INK, whiteSpace: 'pre',
        padding: `${h.size * 0.06}px ${h.size * 0.32}px`, fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 800, fontStyle: lang === 'de' ? 'italic' : 'normal',
        fontSize: h.size, lineHeight: 1.25, clipPath: torn(hash(h.title) + 3, 1.6), boxShadow: '0 5px 12px rgba(0,0,0,.5)' }}>{h.title}</div>
    </div>
  );
};

const CardV: React.FC<{ c: Card; t: number; F: Record<Role, string> }> = ({ c, t, F }) => {
  const note = c.style === 'note', file = c.style === 'file';
  const lh = c.size * 1.6;
  const bg = note
    ? `repeating-linear-gradient(180deg, transparent 0, transparent ${lh - 2}px, rgba(90,130,200,.35) ${lh - 2}px, rgba(90,130,200,.35) ${lh}px), #f4f2ec`
    : `radial-gradient(ellipse 80% 70% at 50% 45%, ${file ? '#d8c69c' : '#ece7dc'} 0%, ${file ? '#c7b283' : PAPER} 60%, ${file ? '#a8946a' : '#c9c2b2'} 100%)`;
  const pad = c.size * 0.9;
  return (
    <div style={{ position: 'relative', width: c.w, height: c.h, background: bg, boxShadow: '0 18px 40px rgba(0,0,0,.6), 0 2px 6px rgba(0,0,0,.4)',
      padding: `${note ? lh * 0.6 : pad}px ${pad}px ${pad}px ${note ? c.size * 2.2 : pad}px`, boxSizing: 'border-box', overflow: 'hidden' }}>
      {note ? <div style={{ position: 'absolute', left: c.size * 1.6, top: 0, bottom: 0, width: 3, background: 'rgba(200,60,60,.45)' }} /> : null}
      {c.head ? (
        <div style={{ fontFamily: `"${F.mono}", "${F.sans}"`, fontWeight: 700, fontSize: c.size * 0.9, color: '#2a2724', letterSpacing: '0.05em', whiteSpace: 'pre',
          paddingBottom: c.size * 0.35, marginBottom: c.size * 0.5, borderBottom: '2px solid rgba(40,36,32,.55)', textTransform: 'uppercase' }}>{typed(c.head, t, c.s, 18)}</div>
      ) : null}
      {c.rows.filter((r) => t >= r.s).map((r, i) => {
        const st = r.strike !== undefined ? easeOut((t - r.strike) / 0.35) : 0;
        const ink = r.color === 'red' ? RED : note ? '#26398a' : '#23201d';
        return (
          <div key={i} style={{ position: 'relative', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: c.size * 0.5,
            minHeight: lh, lineHeight: `${lh}px` }}>
            <span style={{ fontFamily: `"${note ? F.hand : r.right ? F.serif : F.mono}", "${F.sans}"`, fontWeight: note ? 400 : 700, fontSize: c.size, color: ink, whiteSpace: 'pre' }}>
              {r.check ? '✓ ' : ''}{typed(r.text, t, r.s)}</span>
            {r.right ? <span style={{ fontFamily: `"${F.mono}", "${F.sans}"`, fontWeight: 500, fontSize: c.size * 0.72, color: 'rgba(60,55,50,.7)', whiteSpace: 'pre' }}>
              {typed(r.right, t, r.s + 0.25)}</span> : null}
            {st > 0 ? <div style={{ position: 'absolute', left: 0, top: lh * 0.52, height: 4, width: `${st * 100}%`, background: RED }} /> : null}
          </div>
        );
      })}
    </div>
  );
};

const StampV: React.FC<{ g: Stamp; F: Record<Role, string> }> = ({ g, F }) => (
  <div style={{ border: `${g.size * 0.1}px solid ${RED}`, color: RED, padding: `${g.size * 0.12}px ${g.size * 0.4}px`, fontFamily: `"${F.mono}", "${F.sans}"`,
    fontWeight: 700, fontSize: g.size, lineHeight: 1.15, textAlign: 'center', whiteSpace: 'pre', letterSpacing: '0.06em', textTransform: 'uppercase',
    opacity: 0.9, mixBlendMode: 'multiply', background: 'rgba(240,235,225,.06)' }}>{g.text}</div>
);

const BigV: React.FC<{ g: Big; t: number; F: Record<Role, string> }> = ({ g, t, F }) => {
  // the number counts up from 0 when it is a plain number
  const n = Number(g.num.replace(/,/g, ''));
  const shown = Number.isFinite(n) && /^[\d,]+$/.test(g.num) ? Math.round(n * easeOut((t - g.s) / 0.7)).toLocaleString('en-US') : g.num;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: g.size * 0.12 }}>
      <span style={{ fontFamily: `"${F.sans}"`, fontWeight: 900, fontSize: g.size, lineHeight: 1, color: '#eeeae2', whiteSpace: 'nowrap', textShadow: '0 6px 18px rgba(0,0,0,.5)' }}>{shown}</span>
      {g.text ? <span style={{ fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 600, fontSize: g.size * 0.27, lineHeight: 1.3, color: '#cbc4b8', whiteSpace: 'pre',
        paddingTop: g.size * 0.25 }}>{g.text}</span> : null}
    </div>
  );
};

const TextV: React.FC<{ g: Text; t: number; F: Record<Role, string> }> = ({ g, t, F }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
    {g.rows.map((r, i) => (
      <div key={i} style={{ fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 900, fontSize: g.size, lineHeight: 1.2, whiteSpace: 'pre', minHeight: g.size * 1.2,
        color: r.color === 'red' ? '#d8333a' : '#efebe3', textShadow: '0 6px 20px rgba(0,0,0,.6)' }}>{t >= r.s ? typed(r.text, t, r.s, 14) : ''}</div>
    ))}
  </div>
);

// The opening of an episode of a "Top" series (owner, 18/11/2026: the sample of a list of killers, made finer): on
// black, the series title on torn paper, a 3×3 grid of round portraits that come in one by one with their names on
// paper tape; when the voice names this episode's person the others fade to grey, a red ring is drawn round that one
// and the camera pushes in to it. A portrait without a free picture is a dark silhouette with a red question mark.
const RCOL = [195, 540, 885], RROW = [600, 960, 1320], RD3 = 275;
const RosterV: React.FC<{ r: Roster; t: number; F: Record<Role, string>; lang: 'ja' | 'de' }> = ({ r, t, F, lang }) => {
  const n = r.people.length;
  // up to 4 people (owner 18/11/2026: a grid of 4 suits 9:16 best): a 2×2 grid of large portraits; 5–9: 3 columns
  const two = n <= 4, RD = two ? 380 : RD3, NAME = two ? 48 : 36, SUBF = two ? 30 : 24;
  const rows = two ? Math.ceil(n / 2) : Math.ceil(n / 3);
  const pos = r.people.map((_, i) => {
    if (two) {
      const row = Math.floor(i / 2), inRow = Math.min(2, n - row * 2);
      return { x: inRow === 2 ? [285, 795][i % 2] : 540, y: [700, 1220][row] + (2 - rows) * 260 };
    }
    const row = Math.floor(i / 3), inRow = Math.min(3, n - row * 3), col = i % 3;
    const x = inRow === 3 ? RCOL[col] : inRow === 2 ? [370, 710][col] : 540;
    return { x, y: RROW[row] + (3 - rows) * 180 };
  });
  const c = pos[r.pick] || pos[0];
  const k = ease((t - r.pick_s) / 1.15);
  const ring = easeOut((t - r.pick_s - 0.15) / 0.6);
  const ti = easeOut((t - r.s) / 0.5);
  return (
    <AbsoluteFill style={{ background: 'radial-gradient(ellipse 90% 60% at 50% 55%, #241614 0%, #0d0a09 60%, #050404 100%)' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 120, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14,
        opacity: ti * (1 - k), transform: `translateY(${(1 - ti) * -30 - k * 60}px)` }}>
        {r.kicker ? <div style={{ background: RED, color: '#fff', padding: '6px 26px', fontFamily: `"${F.mono}", "${F.sans}"`, fontWeight: 700, fontSize: 40,
          letterSpacing: '0.18em', clipPath: torn(hash(r.kicker), 2), boxShadow: '0 4px 12px rgba(0,0,0,.5)' }}>{r.kicker}</div> : null}
        <div style={{ background: '#ece9e2', color: INK, padding: '10px 34px', fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 900,
          fontStyle: lang === 'de' ? 'italic' : 'normal', fontSize: r.title.length > 11 ? 64 : 76, lineHeight: 1.2, whiteSpace: 'pre', textAlign: 'center',
          clipPath: torn(hash(r.title) + 5, 1.4), boxShadow: '0 8px 22px rgba(0,0,0,.6)', maxWidth: 1000 }}>{r.title}</div>
      </div>
      <AbsoluteFill style={{ transformOrigin: `${c.x}px ${c.y}px`, transform: `translate(${(540 - c.x) * k}px, ${(820 - c.y) * k}px) scale(${1 + (two ? 0.8 : 1.35) * k})` }}>
        {r.people.map((p, i) => {
          const a = easeOut((t - p.s) / 0.35), me = i === r.pick;
          const fade = me ? 1 : 1 - k;
          const gone = r.done.includes(i);   // a person this video already told: grey, struck through
          const { x, y } = pos[i];
          return (
            <div key={i} style={{ position: 'absolute', left: x - RD / 2, top: y - RD / 2, width: RD, opacity: a * fade,
              transform: `scale(${0.6 + 0.4 * backOut((t - p.s) / 0.4)}) rotate(${(rnd(i + 3) - 0.5) * 4}deg)`, filter: me ? 'none' : `grayscale(${gone ? 1 : k}) brightness(${gone ? 0.55 : 1}) blur(${1.5 * k}px)` }}>
              <div style={{ position: 'relative', width: RD, height: RD, borderRadius: '50%', overflow: 'hidden', border: '6px solid #e8e5de',
                boxShadow: '0 14px 34px rgba(0,0,0,.75)', background: 'radial-gradient(circle at 50% 35%, #3a3532 0%, #1a1715 70%)' }}>
                {p.src ? <Img src={staticFile(p.src)} style={{ width: '100%', height: '100%', objectFit: 'cover',
                    objectPosition: `${(p.focus || [0.5, 0.35])[0] * 100}% ${(p.focus || [0.5, 0.35])[1] * 100}%` }} />
                  : <svg width={RD} height={RD} viewBox="0 0 100 100" style={{ position: 'absolute', left: 0, top: 0 }}>
                      <ellipse cx="50" cy="40" rx="17" ry="20" fill="#0a0908" /><path d="M14 100 C 16 72, 30 62, 50 62 C 70 62, 84 72, 86 100 Z" fill="#0a0908" />
                      <text x="50" y="49" textAnchor="middle" fontSize="22" fontWeight="900" fill={RED} fontFamily={`"${F.serif}"`}>?</text>
                    </svg>}
                <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 40px rgba(0,0,0,.55)', borderRadius: '50%' }} />
              </div>
              {gone ? <svg width={RD} height={RD} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
                <line x1={RD * 0.12} y1={RD * 0.12} x2={RD * 0.88} y2={RD * 0.88} stroke={RED} strokeWidth={9} strokeLinecap="round" opacity={0.85} />
                <line x1={RD * 0.88} y1={RD * 0.12} x2={RD * 0.12} y2={RD * 0.88} stroke={RED} strokeWidth={9} strokeLinecap="round" opacity={0.85} /></svg> : null}
              {me && r.rank && ring > 0 ? <div style={{ position: 'absolute', left: '50%', top: -58, transform: `translateX(-50%) rotate(-4deg) scale(${0.6 + 0.4 * backOut(ring)})`,
                background: '#ece9e2', color: RED, padding: '0 18px', fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 900, fontSize: 44, whiteSpace: 'nowrap',
                clipPath: torn(hash(r.rank), 2.2), boxShadow: '0 4px 10px rgba(0,0,0,.6)' }}>{r.rank}</div> : null}
              {me && ring > 0 ? <svg width={RD + 60} height={RD + 60} style={{ position: 'absolute', left: -30, top: -30, overflow: 'visible' }}>
                <ellipse pathLength={1} cx={(RD + 60) / 2} cy={(RD + 60) / 2} rx={(RD + 34) / 2} ry={(RD + 26) / 2} fill="none" stroke={RED} strokeWidth={7}
                  strokeLinecap="round" strokeDasharray={1} strokeDashoffset={1 - ring} transform={`rotate(-80 ${(RD + 60) / 2} ${(RD + 60) / 2})`}
                  style={{ filter: 'drop-shadow(0 0 6px rgba(0,0,0,.8))' }} /></svg> : null}
              <div style={{ position: 'absolute', left: '50%', top: RD - 8, transform: 'translateX(-50%) rotate(-1.5deg)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ background: me && k > 0.05 ? RED : '#ece9e2', color: me && k > 0.05 ? '#fff' : INK, padding: '2px 16px', whiteSpace: 'nowrap',
                  fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 800, fontSize: NAME, lineHeight: 1.25, clipPath: torn(hash(p.name), 2.4),
                  boxShadow: '0 4px 10px rgba(0,0,0,.5)' }}>{p.name}</div>
                {p.sub ? <div style={{ marginTop: 4, fontFamily: `"${F.mono}", "${F.sans}"`, fontWeight: 700, fontSize: SUBF, color: YELLOW, whiteSpace: 'nowrap',
                  textShadow: '0 2px 6px rgba(0,0,0,.9)' }}>{p.sub}</div> : null}
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
      {r.note ? <div style={{ position: 'absolute', left: 60, right: 60, top: 372, textAlign: 'center', fontFamily: `"${F.sans}"`, fontWeight: 700,
        fontSize: 28, color: 'rgba(230,224,214,.7)', letterSpacing: '0.04em', opacity: ti * (1 - k) }}>{r.note}</div> : null}
    </AbsoluteFill>
  );
};

const ItemV: React.FC<{ it: Item; t: number; e: number; plan: PlanC; F: Record<Role, string> }> = ({ it, t, e, plan, F }) => {
  if (t < it.s || (it.e !== undefined && t >= it.e)) return null;
  if (it.k === 'roster') return <RosterV r={it} t={t} F={F} lang={plan.lang} />;
  if (it.k === 'line') {
    const [[x0, y0], [x1, y1]] = it.pts;
    const d = easeOut((t - it.s) / 0.45);
    return (
      <svg width={1080} height={1920} style={{ position: 'absolute', left: 0, top: 0 }}>
        <line x1={x0} y1={y0} x2={x0 + (x1 - x0) * d} y2={y0 + (y1 - y0) * d} stroke={it.color === 'yellow' ? YELLOW : RED} strokeWidth={4}
          strokeLinecap="round" style={{ filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.6))' }} />
        <circle cx={x0} cy={y0} r={7} fill={RED} />
        {d >= 1 ? <circle cx={x1} cy={y1} r={7} fill={RED} /> : null}
      </svg>
    );
  }
  const a = enter(t, it.s, it.k);
  const body = it.k === 'photo' ? <PhotoV p={it} t={t} e={e} tag={plan.aiTag} sans={F.sans} mono={F.mono} />
    : it.k === 'tag' ? <TagV g={it} F={F} lang={plan.lang} />
    : it.k === 'header' ? <HeaderV h={it} t={t} F={F} lang={plan.lang} />
    : it.k === 'card' ? <CardV c={it} t={t} F={F} />
    : it.k === 'stamp' ? <StampV g={it} F={F} />
    : it.k === 'big' ? <BigV g={it} t={t} F={F} />
    : <TextV g={it} t={t} F={F} />;
  return (
    <div style={{ position: 'absolute', left: it.x, top: it.y, width: 0, height: 0 }}>
      <div style={{ position: 'absolute', left: 0, top: 0, transform: `translate(-50%, -50%) rotate(${it.rot + a.turn}deg) scale(${a.scale})`,
        opacity: a.opacity }}>{body}</div>
    </div>
  );
};

const SceneV: React.FC<{ sc: Scene; t: number; plan: PlanC; F: Record<Role, string> }> = ({ sc, t, plan, F }) => {
  const push = 1 + sc.push * pace((t - sc.s) / Math.max(1, sc.e - sc.s));
  return (
    <AbsoluteFill style={{ background: '#0b0a09', overflow: 'hidden' }}>
      <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: '50% 45%' }}>
        {sc.bg === 'wood' ? <Img src={staticFile(plan.bg)} style={{ position: 'absolute', left: -54, top: -96, width: 1188, height: 2112 }} /> : null}
        {sc.items.map((it, i) => <ItemV key={i} it={it} t={t} e={sc.e} plan={plan} F={F} />)}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// old film over everything: grain, dust specks, now and then a hair, a faint flicker
const Film: React.FC<{ frame: number; grain: string }> = ({ frame, grain }) => {
  const specks = Array.from({ length: 7 }, (_, i) => {
    const r = (k: number) => rnd(frame * 13 + i * 7 + k);
    return r(1) < 0.55 ? { x: r(2) * 1080, y: r(3) * 1920, s: 2 + r(4) * 5, o: 0.35 + r(5) * 0.5 } : null;
  }).filter(Boolean) as { x: number; y: number; s: number; o: number }[];
  const hairOn = rnd(Math.floor(frame / 9) * 3.3) < 0.28;   // a hair stays ~9 frames, about a third of the time
  const hs = Math.floor(frame / 9);
  const hx = rnd(hs + 1) * 900 + 90, hy = rnd(hs + 2) * 1700 + 110, hr = rnd(hs + 3) * 360;
  const flick = 0.04 * rnd(frame * 0.7 + 5);
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <AbsoluteFill style={{ backgroundImage: `url(${staticFile(grain)})`, backgroundPosition: `${Math.floor(rnd(frame) * 512)}px ${Math.floor(rnd(frame + 0.5) * 512)}px`,
        mixBlendMode: 'overlay', opacity: 0.22 }} />
      <svg width={1080} height={1920} style={{ position: 'absolute', left: 0, top: 0 }}>
        {specks.map((p, i) => <ellipse key={i} cx={p.x} cy={p.y} rx={p.s} ry={p.s * 0.7} fill={`rgba(245,242,235,${p.o})`} />)}
        {hairOn ? <path d="M0 0 c 18 -22 34 -6 20 14 c -10 14 -30 22 -38 40 c -4 10 6 18 16 14" transform={`translate(${hx} ${hy}) rotate(${hr}) scale(1.5)`}
          fill="none" stroke="rgba(235,232,225,.55)" strokeWidth={1.6} /> : null}
      </svg>
      <AbsoluteFill style={{ background: '#000', opacity: flick }} />
      <AbsoluteFill style={{ boxShadow: 'inset 0 0 220px rgba(0,0,0,.75)' }} />
    </AbsoluteFill>
  );
};

export const CrimeV: React.FC<PlanC> = (plan) => {
  const lang = plan.lang || 'ja';
  FX = { motion: false, depth: false, text: false, ...(plan.fx || {}) };
  const F = { ...DEFAULT_FAM[lang], ...(plan.families || {}) } as Record<Role, string>;
  useFonts(plan, F);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  if (!plan.scenes.length) return <AbsoluteFill style={{ backgroundColor: '#000' }} />;
  const idx = Math.max(0, plan.scenes.findIndex((s) => t >= s.s && t < s.e));
  const sc = plan.scenes[idx >= 0 && t < plan.scenes[plan.scenes.length - 1].e ? idx : plan.scenes.length - 1];
  const prev = idx > 0 ? plan.scenes[idx - 1] : null;
  const fade = prev ? clamp01((t - sc.s) / 0.22) : 1;   // a short dissolve between scenes
  const sub = plan.subs.find((c) => t >= c.s && t < c.e);
  const speaking = (tt: number) => plan.subs.some((c) => tt >= c.s - 0.2 && tt < c.e + 0.2);
  return (
    <AbsoluteFill style={{ backgroundColor: '#0b0a09' }}>
      {prev && fade < 1 ? <SceneV sc={prev} t={t} plan={plan} F={F} /> : null}
      <AbsoluteFill style={{ opacity: prev ? fade : clamp01(t / 0.4) }}><SceneV sc={sc} t={t} plan={plan} F={F} /></AbsoluteFill>
      <Film frame={frame} grain={plan.grain} />
      {(plan.quotes || []).filter((q) => t >= q.s && t < q.e).map((q, i) => {
        // a key line printed big on the foot of the frame over a soft dark band while it is spoken (hook, from japan-news)
        const a = easeOut((t - q.s) / 0.35) * (1 - easeOut((t - (q.e - 0.3)) / 0.3));
        const shown = FX.text ? typed(q.text, t, q.s, Math.max(6, [...q.text].length / Math.max(0.6, (q.e - q.s) * 0.8))) : q.text;
        return (
          <AbsoluteFill key={i} style={{ pointerEvents: 'none', opacity: a }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: 1150, height: 560,
              background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.72) 38%, rgba(0,0,0,.82) 100%)' }} />
            <div style={{ position: 'absolute', left: 70, right: 70, top: 1380, transform: `translateY(${(1 - a) * 20}px)`, textAlign: 'center',
              fontFamily: `"${F.serif}", "${F.sans}"`, fontWeight: 900, fontSize: Math.min(76, Math.floor(920 / Math.max(...q.text.split('\n').map((r) => [...r].length)))), lineHeight: 1.35, color: '#f4efe6', whiteSpace: 'pre-line',
              textShadow: '0 4px 18px rgba(0,0,0,.85)' }}>{shown}</div>
          </AbsoluteFill>
        );
      })}
      {sub ? (
        <div style={{ position: 'absolute', left: 540 - SUB_MAX_W / 2, width: SUB_MAX_W, top: SUB_Y, display: 'flex', justifyContent: 'center',
          transform: 'translateY(-50%)' }}>
          <div style={{ background: '#f7f5f0', color: '#111', padding: '8px 18px', borderRadius: 3, fontFamily: `"${F.sans}"`, fontWeight: 500,
            fontSize: SUB_SIZE[lang], lineHeight: 1.3, textAlign: 'center', boxShadow: '0 3px 10px rgba(0,0,0,.35)' }}>
            {FX.text ? (() => {   // text: the whole clause is there, pale, and darkens from left to right as it is read
              const cs = [...sub.text], n = Math.round(cs.length * clamp01((t - sub.s) / Math.max(0.3, (sub.e - sub.s) * 0.92)));
              return <><span>{cs.slice(0, n).join('')}</span><span style={{ color: '#9a958c' }}>{cs.slice(n).join('')}</span></>;
            })() : sub.text}</div>
        </div>
      ) : null}
      {plan.voice.map((v, i) => <Sequence key={i} from={Math.round(v.s * fps)}><Audio src={staticFile(v.src)} /></Sequence>)}
      {plan.music ? (
        <Audio src={staticFile(plan.music)} loop={!!plan.musicLoop} volume={(f) => {
          const tt = f / fps;
          return plan.musicVolume * Math.max(0, Math.min(1, tt / 0.6, (durationInFrames / fps - tt) / 1.4)) * (speaking(tt) ? 0.7 : 1);
        }} />
      ) : null}
    </AbsoluteFill>
  );
};
