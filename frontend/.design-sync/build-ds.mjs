#!/usr/bin/env node
// Builds the design-sync library from .design-sync/ds-entry.tsx into ds-dist/
// (gitignored) with the app's own toolchain: Vite library mode compiles the
// TSX + SCSS, tsc emits the .d.ts tree. Run from frontend/:
//   node .design-sync/build-ds.mjs
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'vite';
import react from '@vitejs/plugin-react';

const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(FRONTEND, 'ds-dist');
const ENTRY = join(FRONTEND, '.design-sync', 'ds-entry.tsx');
const pkg = JSON.parse(readFileSync(join(FRONTEND, 'package.json'), 'utf8'));
const deps = Object.keys(pkg.dependencies ?? {});
const isDep = (id) => deps.some((d) => id === d || id.startsWith(d + '/'));

rmSync(DIST, { recursive: true, force: true });
mkdirSync(DIST, { recursive: true });

// 1. JS + CSS. Dependencies stay external (a library build); the converter
// bundles them from node_modules. No env vars are exposed, so nothing from
// .env.local can be inlined into the uploaded bundle.
await build({
  configFile: false,
  root: FRONTEND,
  envPrefix: '__DS_SYNC_NO_ENV__',
  plugins: [react()],
  logLevel: 'warn',
  build: {
    outDir: DIST,
    emptyOutDir: false,
    minify: false,
    cssCodeSplit: false,
    lib: { entry: ENTRY, formats: ['es'], fileName: () => 'index.js', cssFileName: 'style' },
    rollupOptions: {
      external: isDep,
      // Drop bare side-effect imports of unused externals (e.g. Sentry via
      // observability.ts) so they aren't pulled into the bundle.
      treeshake: { moduleSideEffects: (_id, external) => !external },
    },
  },
});

// 2. Types. rootDir is frontend/, so the entry's declarations land under a
// dot-dir; move them to types/ds/ (relative ../src imports still resolve).
const tsc = join(FRONTEND, 'node_modules', '.bin', 'tsc');
try {
  execFileSync(tsc, ['-p', join(FRONTEND, '.design-sync', 'tsconfig.ds.json')], { cwd: FRONTEND, stdio: 'inherit' });
} catch {
  // Type errors still emit declarations (noEmitOnError is off); the app's own
  // `npm run build` is the type gate, not this script.
  console.error('build-ds: tsc reported errors (declarations were still emitted)');
}
const dotDir = join(DIST, 'types', '.design-sync');
if (!existsSync(join(dotDir, 'ds-entry.d.ts'))) {
  console.error('build-ds: tsc did not emit ds-entry.d.ts');
  process.exit(1);
}
renameSync(dotDir, join(DIST, 'types', 'ds'));
writeFileSync(join(DIST, 'index.d.ts'), "export * from './types/ds/ds-entry';\n");

// 3. A package.json so the converter treats ds-dist/ as the package. No
// "type": "module" - that switches esbuild to Node interop, where a default
// import of a CJS module (@visx/brush/lib/Brush) ignores __esModule and
// yields the whole exports object ("Element type is invalid").
writeFileSync(join(DIST, 'package.json'), JSON.stringify({
  name: 'pca-design-system',
  version: pkg.version,
  module: 'index.js',
  types: 'index.d.ts',
  style: 'style.css',
}, null, 2) + '\n');

for (const f of ['index.js', 'style.css', 'index.d.ts']) {
  if (!existsSync(join(DIST, f))) { console.error(`build-ds: missing ${f}`); process.exit(1); }
}
console.error(`build-ds: wrote ${DIST}`);
