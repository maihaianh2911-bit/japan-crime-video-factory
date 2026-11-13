import React, { useEffect, useState } from 'react';
import { AbsoluteFill, Audio, Img, Sequence, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

// Vertical (1080×1920) true-crime short, laid out as the owner's sample (00-video-mau/MAU-VU-AN.mp4): black frame,
// one old photograph almost the full width with a slow push-in, hard cuts every few seconds, short yellow captions
// (2–3 words) in the lower part of the photograph, timed to the voice. The owner added (13/11/2026) the case title
// on top for the whole video, with a small per-shot label under it. AI illustrations carry a tag on the picture.
// Positions come from scripts/crime/layout.py via build.py.
type View = [number, number, number, number];
export type Pic = { src: string; w: number; h: number; box: [number, number, number, number]; view: View;
  zoom?: { to: View; s: number; e: number }; drift?: number };
export type Mark = { s: number; box: View; shape: 'ellipse' | 'rect' };
export type Shot = { s: number; e: number; shot: number; label: string; credit: string; ai: boolean; pic: Pic; marks: Mark[] };
export type Cap = { s: number; e: number; text: string; line: number };
type FontChunk = { family: string; file: string; range: string };
export type PlanC = { duration: number; lang: 'ja' | 'de'; title: string; titleSize: number; aiTag: string; shots: Shot[];
  caps: Cap[]; voice: { s: number; src: string }[]; music: string | null; musicVolume: number; fonts: FontChunk[] };

// layout.py
const SIDE = 24, TITLE_Y = 66, LABEL_Y = 196, CAP_Y = 1310, CAP_W = 1000, CREDIT_Y = 1676;
const CAP = { ja: 78, de: 86 };
const YELLOW = '#ffc81e', RED = '#d92a1c';
const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
const ease = (x: number) => { const p = clamp01(x); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
const fontsOf = (lang: 'ja' | 'de') => lang === 'ja'
  ? { head: '"Noto Sans JP", sans-serif', cap: '"Noto Sans JP", sans-serif', small: '"Noto Sans JP", sans-serif', capWeight: 900, headWeight: 900 }
  : { head: '"Anton", "Source Sans 3", sans-serif', cap: '"Anton", "Source Sans 3", sans-serif', small: '"Source Sans 3", sans-serif', capWeight: 400, headWeight: 400 };

let fontsLoading: Promise<void> | null = null;
const useFonts = (fonts: FontChunk[], text: string, lang: 'ja' | 'de') => {
  const [h] = useState(() => delayRender('fonts'));
  useEffect(() => {
    const f = fontsOf(lang);
    (fontsLoading ??= (async () => {
      for (const c of fonts)
        document.fonts.add(new FontFace(c.family, `url(${staticFile(c.file)}) format('woff2')`, { weight: '100 900', unicodeRange: c.range }));
      await Promise.all([900, 600, 400].flatMap((wt) => [f.head, f.small].map((fam) => document.fonts.load(`${wt} 60px ${fam}`, text))));
    })()).then(() => continueRender(h)).catch((e) => cancelRender(e));
  }, [h, fonts, text, lang]);
};

// region of the picture shown at time t: a zoom when asked for, else a slow push-in (by `drift` over the shot)
export const viewAt = (p: Pic, t: number, s: number, e: number): View => {
  if (p.zoom) {
    const k = ease((t - p.zoom.s) / Math.max(0.1, p.zoom.e - p.zoom.s));
    return p.view.map((v, i) => v + (p.zoom!.to[i] - v) * k) as View;
  }
  if (!p.drift) return p.view;
  const k = clamp01((t - s) / Math.max(0.5, e - s)) * p.drift / 2;
  const [a, b, c, d] = p.view, w = c - a, h = d - b;
  return [a + w * k, b + h * k, c - w * k, d - h * k];
};

const Photo: React.FC<{ sh: Shot; t: number; tag: string; small: string }> = ({ sh, t, tag, small }) => {
  const p = sh.pic;
  const [x, y, bw, bh] = p.box;
  const [v0, v1, v2, v3] = viewAt(p, t, sh.s, sh.e);
  const sx = bw / ((v2 - v0) * p.w), sy = bh / ((v3 - v1) * p.h);
  // a faint flicker of old film: brightness wanders by ±2 %
  const flicker = 1 + 0.02 * Math.sin(t * 13.1) * Math.sin(t * 3.7 + 1.3);
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: bw, height: bh, overflow: 'hidden', background: '#000',
      boxShadow: '0 0 0 2px rgba(225,210,180,.18), 0 20px 60px rgba(0,0,0,.8)', borderRadius: 3 }}>
      <Img src={staticFile(p.src)} style={{ position: 'absolute', left: -v0 * p.w * sx, top: -v1 * p.h * sy, width: p.w * sx, height: p.h * sy,
        maxWidth: 'none', filter: `brightness(${flicker.toFixed(4)})` }} />
      {/* worn edges of the print */}
      <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 70px rgba(20,12,4,.55), inset 0 0 14px rgba(240,225,195,.18)' }} />
      <svg width={bw} height={bh} style={{ position: 'absolute', left: 0, top: 0 }}>
        {sh.marks.filter((mk) => t >= mk.s).map((mk, i) => {
          const X = (f: number) => ((f - v0) / (v2 - v0)) * bw, Y = (f: number) => ((f - v1) / (v3 - v1)) * bh;
          const [a, b, c, d] = mk.box;
          const draw = easeOut((t - mk.s) / 0.5);
          const st = { fill: 'none', stroke: RED, strokeWidth: 7, strokeLinecap: 'round' as const, strokeDasharray: 1, strokeDashoffset: 1 - draw,
            filter: 'drop-shadow(0 0 5px rgba(0,0,0,.7))' };
          return mk.shape === 'rect'
            ? <rect key={i} pathLength={1} x={X(a)} y={Y(b)} width={X(c) - X(a)} height={Y(d) - Y(b)} rx={6} style={st} />
            // turned by -90° so the ring starts drawing at the top: its radii are swapped to keep the box's shape
            : <ellipse key={i} pathLength={1} cx={(X(a) + X(c)) / 2} cy={(Y(b) + Y(d)) / 2} rx={(Y(d) - Y(b)) / 2} ry={(X(c) - X(a)) / 2}
                transform={`rotate(-90 ${(X(a) + X(c)) / 2} ${(Y(b) + Y(d)) / 2})`} style={st} />;
        })}
      </svg>
      {sh.ai ? (
        <div style={{ position: 'absolute', right: 18, top: 18, padding: '6px 14px', borderRadius: 6, background: 'rgba(0,0,0,.55)',
          color: 'rgba(255,255,255,.9)', fontFamily: small, fontWeight: 600, fontSize: 26, letterSpacing: '0.03em' }}>{tag}</div>
      ) : null}
    </div>
  );
};

export const CrimeV: React.FC<PlanC> = (plan) => {
  const lang = plan.lang || 'ja';
  const F = fontsOf(lang);
  useFonts(plan.fonts, plan.title + plan.aiTag + plan.shots.map((s) => s.label + s.credit).join('') + plan.caps.map((c) => c.text).join(''), lang);
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  if (!plan.shots.length) return <AbsoluteFill style={{ backgroundColor: '#000' }} />;
  const idx = Math.max(0, plan.shots.findIndex((s) => t >= s.s && t < s.e));
  const sh = plan.shots.find((s) => t >= s.s && t < s.e) || plan.shots[plan.shots.length - 1];
  const prev = idx > 0 ? plan.shots[idx - 1] : null;
  const cap = plan.caps.find((c) => t >= c.s && t < c.e);
  const speaking = (tt: number) => plan.caps.some((c) => tt >= c.s - 0.2 && tt < c.e + 0.2);
  const labelIn = prev && prev.label === sh.label ? 1 : easeOut((t - sh.s) / 0.4);
  const titleIn = easeOut(t / 0.6);
  const pop = cap ? easeOut((t - cap.s) / 0.12) : 1;   // each caption chunk snaps in
  const upper = lang === 'de';
  return (
    <AbsoluteFill style={{ background: 'radial-gradient(ellipse 120% 80% at 50% 50%, #111 0%, #050505 70%, #000 100%)' }}>
      {/* case title, the whole video */}
      <div style={{ position: 'absolute', left: SIDE, right: SIDE, top: TITLE_Y, textAlign: 'center', opacity: titleIn,
        fontFamily: F.head, fontWeight: F.headWeight, fontSize: plan.titleSize, lineHeight: 1.18, color: '#f5efe3',
        textTransform: upper ? 'uppercase' : 'none', letterSpacing: upper ? '0.02em' : '0.04em', whiteSpace: 'nowrap',
        textShadow: '0 3px 18px rgba(0,0,0,.9)' }}>{plan.title}</div>
      <div style={{ position: 'absolute', left: 540 - 60, width: 120, top: LABEL_Y - 18, height: 4, background: RED, opacity: titleIn }} />
      {sh.label ? (
        <div style={{ position: 'absolute', left: SIDE, right: SIDE, top: LABEL_Y + (1 - labelIn) * 8, opacity: labelIn, textAlign: 'center',
          fontFamily: F.small, fontWeight: 600, fontSize: 36, lineHeight: 1.25, color: '#bdb4a4', letterSpacing: upper ? '0.12em' : '0.06em',
          textTransform: upper ? 'uppercase' : 'none', whiteSpace: 'nowrap' }}>{sh.label}</div>
      ) : null}
      <Photo sh={sh} t={t} tag={plan.aiTag} small={F.small} />
      {cap ? (
        <div style={{ position: 'absolute', left: 540 - CAP_W / 2, width: CAP_W, top: CAP_Y, textAlign: 'center',
          transform: `scale(${0.86 + 0.14 * pop})${upper ? ' skewX(-7deg)' : ''}`, transformOrigin: '50% 40%' }}>
          <span style={{ fontFamily: F.cap, fontWeight: F.capWeight, fontSize: CAP[lang], lineHeight: 1.12, color: YELLOW,
            textTransform: upper ? 'uppercase' : 'none', letterSpacing: upper ? '0.01em' : '0.02em',
            WebkitTextStroke: `${lang === 'ja' ? 12 : 10}px #000`, paintOrder: 'stroke fill',
            textShadow: '0 6px 18px rgba(0,0,0,.85)' }}>{cap.text}</span>
        </div>
      ) : null}
      {sh.credit ? (
        <div style={{ position: 'absolute', left: SIDE + 6, right: SIDE + 6, top: CREDIT_Y, fontFamily: F.small, fontWeight: 400, fontSize: 24,
          lineHeight: 1.3, color: 'rgba(200,192,180,.7)', letterSpacing: '0.04em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sh.credit}</div>
      ) : null}
      {plan.voice.map((v, i) => <Sequence key={i} from={Math.round(v.s * fps)}><Audio src={staticFile(v.src)} /></Sequence>)}
      {plan.music ? (
        <Audio src={staticFile(plan.music)} volume={(f) => {
          const tt = f / fps;
          return plan.musicVolume * Math.max(0, Math.min(1, tt / 0.6, (durationInFrames / fps - tt) / 1.4)) * (speaking(tt) ? 0.7 : 1);
        }} />
      ) : null}
    </AbsoluteFill>
  );
};
