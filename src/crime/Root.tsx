import React from 'react';
import { Composition } from 'remotion';
import { CrimeV, PlanC } from './CrimeV';

const FPS = 30;
// The whole plan comes in as props (scripts/crime/build.py), its length included.
const EMPTY: PlanC = { duration: 1, lang: 'ja', title: '', aiTag: '', bg: '', grain: '', scenes: [], subs: [], voice: [], music: null,
  musicVolume: 0.16, fonts: [], families: {} };

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
