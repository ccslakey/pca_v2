import { Link } from 'react-router-dom';
import { playerColor } from '../../utils/color';
import { initials } from '../../utils/format';
import type { SimilarPlayersResponse } from '../../types';

interface Props {
  similar: SimilarPlayersResponse;
}

export function SimilarPlayersPanel({ similar }: Props) {
  const isTwoWay = similar.batters.length > 0 && similar.pitchers.length > 0;
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          Similar players
          <span className="muted">by WAR &amp; profile</span>
        </div>
      </div>
      {[
        { list: similar.batters,  label: 'As a batter'  },
        { list: similar.pitchers, label: 'As a pitcher' },
      ].map(({ list, label }) => {
        if (!list.length) return null;
        return (
          <div key={label}>
            {isTwoWay && <div className="similar-role-label">{label}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {list.map(p => {
                const c = playerColor(p.bbref_id);
                return (
                  <Link key={p.bbref_id} to={`/player/${p.bbref_id}`} className="comp-row">
                    <div className="comp-shot" style={{ background: c }}>
                      {initials(`${p.first_name} ${p.last_name}`)}
                    </div>
                    <div className="comp-info">
                      <div className="comp-name">{p.first_name} {p.last_name}</div>
                      <div className="comp-meta">
                        {p.is_pitcher ? 'P' : 'B'} · {p.career_war.toFixed(1)} WAR
                        {p.mlb_played_first && ` · ${p.mlb_played_first}–${p.mlb_played_last ?? 'pres'}`}
                      </div>
                    </div>
                    <div className="comp-score">{p.similarity}% sim</div>
                  </Link>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
