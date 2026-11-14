// Frames of a crime video rendered by Remotion exactly as the video (the framing preview and the smoke test).
// Usage: node scripts/crime/stills.mjs <plan.json> <public_dir> <out_prefix> <t1> [t2 ...]   (seconds; half size)
// Writes <out_prefix>_<t>.jpg for each time.
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const [planFile, publicDir, prefix, ...ts] = process.argv.slice(2);
const inputProps = JSON.parse(fs.readFileSync(planFile, 'utf8'));
const serveUrl = await bundle({ entryPoint: path.join(ROOT, 'src/crime/index.ts'), publicDir: path.resolve(publicDir) });
const chromiumOptions = { gl: 'swiftshader' };
const composition = await selectComposition({ serveUrl, id: 'CrimeV', inputProps, chromiumOptions });
for (const t of ts) {
  const frame = Math.min(composition.durationInFrames - 1, Math.round(Number(t) * composition.fps));
  await renderStill({ serveUrl, composition, inputProps, frame, output: `${prefix}_${t}.jpg`, imageFormat: 'jpeg', jpegQuality: 88,
    chromiumOptions, scale: 0.5 });
  console.log(`${prefix}_${t}.jpg`);
}
