// Exports real player data from a running local API into the preview
// fixtures (.design-sync/previews/_data.json), shaped exactly like the app's
// useChartPlayer() output. Regenerate with:
//   (backend) python manage.py runserver 127.0.0.1:8765
//   (frontend) npx esbuild .design-sync/fixtures/export.ts --bundle --platform=node \
//       --format=esm --outfile=<tmp>/export.mjs && node <tmp>/export.mjs
import { writeFileSync } from 'node:fs';
import { mergeSeasons, playerRoles } from '../../src/utils/seasons';
import { initials, posLabel } from '../../src/utils/format';
import type { ChartPlayer, PlayerBundle, SimilarPlayersResponse, AgingCurvePoint } from '../../src/types';

const API = process.env.PCA_API ?? 'http://127.0.0.1:8765/api';
// Run from frontend/ (the bundled script lives elsewhere, so not import.meta.url).
const OUT = '.design-sync/previews/_data.json';
// Batters, pitchers, and a two-way player - the shapes every component branches on.
const IDS = ['troutmi01', 'judgeaa01', 'griffke02', 'kershcl01', 'maddugr01', 'ohtansh01'];

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

// Same construction as useChartPlayer() in src/hooks.ts.
function toChartPlayer(b: PlayerBundle, colorIndex: number): ChartPlayer {
  const { detail: p, batting: bat, pitching: pit, awards } = b;
  const { isBatter, isPitcher } = playerRoles(p.primary_position, bat, pit);
  const debutYear = p.debut ? new Date(p.debut).getUTCFullYear() : null;
  const finalYear = p.final_game ? new Date(p.final_game).getUTCFullYear() : null;
  const wp = p.war_percentile;
  return {
    id: p.bbref_id,
    name: `${p.first_name} ${p.last_name}`,
    color: `var(--chart-${(colorIndex % 10) + 1})`,
    initials: initials(`${p.first_name} ${p.last_name}`),
    pos: posLabel(p.primary_position, p.throws, isPitcher),
    years: debutYear && finalYear ? `${debutYear}–${finalYear}` : 'Active',
    seasons: mergeSeasons(bat, pit, p.birth_date),
    isBatter,
    isPitcher,
    awards,
    birthYear: p.birth_date ? new Date(p.birth_date).getUTCFullYear() : null,
    warPercentile: wp ? { topPct: wp.top_pct, position: wp.position, rank: wp.rank, n: wp.n } : null,
  };
}

const players: Record<string, ChartPlayer> = {};
const james: Record<string, unknown> = {};
for (const [i, id] of IDS.entries()) {
  const b = await get<PlayerBundle>(`/players/${id}/bundle/`);
  players[id] = toChartPlayer(b, i);
  james[id] = b.detail.james_score;
}
const similar = await get<SimilarPlayersResponse>('/players/troutmi01/similar/');
const agingBatters = await get<AgingCurvePoint[]>('/players/aging_curve/?role=B');

writeFileSync(OUT, JSON.stringify({ players, james, similar: { troutmi01: similar }, agingBatters }, null, 1) + '\n');
console.log(`wrote ${OUT}: ${IDS.length} players`);
