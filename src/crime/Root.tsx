import React from 'react';
import { Composition } from 'remotion';
import { CrimeV, PlanC } from './CrimeV';

const FPS = 30;
// The whole plan comes in as props (scripts/crime/build.py), its length included.
const EMPTY: PlanC = { duration: 1, lang: 'ja', title: '', titleSize: 78, aiTag: '', shots: [], caps: [], voice: [], music: null, musicVolume: 0.14, fonts: [] };

export const CrimeRoot: React.FC = () => (
  <Composition
    id="CrimeV"
    component={CrimeV as unknown as React.FC<Record<string, unknown>>}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={FPS}
    defaultProps={EMPTY as unknown as Record<string, unknown>}
    calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, Math.ceil((props as unknown as PlanC).duration * FPS)) })}
  />
);
