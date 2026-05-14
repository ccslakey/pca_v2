import { Link } from 'react-router-dom';
import { Skeleton } from '../Skeleton';

/**
 * Full-page skeleton matching ProfilePage layout. Renders the topbar + panel
 * chrome immediately while data is loading; only the inner content is greyed.
 */
export function ProfilePageSkeleton() {
  return (
    <div className="profile">
      <div className="topbar">
        <Link to="/" className="profile-back">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 6 9 12 15 18" />
          </svg>
          Comparison
        </Link>
        <div className="brand" style={{ marginLeft: 8 }}>
          <div className="brand-mark" />
          <span className="brand-name">Career Arc Visualizer</span>
        </div>
        <div style={{ flex: 1 }} />
      </div>

      <div className="profile-main">
        {/* Hero */}
        <div className="hero">
          <div className="hero-left">
            <Skeleton width={220} height={220} radius={24} />
          </div>
          <div className="hero-mid">
            <Skeleton width={140} height={22} radius={999} style={{ marginBottom: 12 }} />
            <Skeleton width={340} height={48} style={{ marginBottom: 12 }} />
            <div style={{ display: 'flex', gap: 14 }}>
              <Skeleton width={90} height={13} />
              <Skeleton width={110} height={13} />
              <Skeleton width={100} height={13} />
              <Skeleton width={130} height={13} />
            </div>
          </div>
          <div className="hero-right">
            <Skeleton width={92} height={32} radius={8} />
          </div>
        </div>

        {/* Stat grid */}
        <div className="stat-grid">
          <div className="stat-block is-headline">
            <Skeleton width={80} height={10} />
            <Skeleton width={120} height={36} style={{ marginTop: 8 }} />
            <Skeleton width={140} height={11} style={{ marginTop: 6 }} />
          </div>
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="stat-block">
              <Skeleton width={60} height={10} />
              <Skeleton width={70} height={28} style={{ marginTop: 8 }} />
              <Skeleton width={80} height={11} style={{ marginTop: 6 }} />
            </div>
          ))}
        </div>

        <div className="col-2">
          {/* LEFT column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Career arc */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Career arc</div>
              </div>
              <Skeleton width="100%" height={32} radius={8} />
              <Skeleton width="100%" height={360} radius={8} style={{ marginTop: 12 }} />
            </div>

            {/* Sparklines */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Sparklines</div>
              </div>
              <div className="spark-grid">
                {[0, 1, 2, 3].map(i => (
                  <div key={i} className="spark">
                    <div className="spark-head">
                      <Skeleton width={50} height={10} />
                      <Skeleton width={30} height={14} />
                    </div>
                    <Skeleton width="100%" height={36} />
                  </div>
                ))}
              </div>
            </div>

            {/* Season log */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Season log</div>
              </div>
              <table className="season-table">
                <thead>
                  <tr>
                    {[40, 60, 60, 60, 60].map((w, i) => (
                      <th key={i}><Skeleton width={w} height={10} /></th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: 10 }).map((_, i) => (
                    <tr key={i}>
                      {[40, 60, 60, 60, 60].map((w, j) => (
                        <td key={j}><Skeleton width={w} height={13} /></td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* RIGHT column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Similar players */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Similar players</div>
              </div>
              <Skeleton width={80} height={10} style={{ marginBottom: 10 }} />
              {[0, 1, 2, 3].map(i => (
                <div key={i} className="comp-row" style={{ pointerEvents: 'none' }}>
                  <Skeleton variant="circle" width={32} height={32} />
                  <div style={{ flex: 1 }}>
                    <Skeleton width="60%" height={14} />
                    <Skeleton width="40%" height={11} style={{ marginTop: 4 }} />
                  </div>
                  <Skeleton width={36} height={20} radius={999} />
                </div>
              ))}
            </div>

            {/* Pitch zone */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Pitch zone</div>
              </div>
              <Skeleton width="100%" height={280} radius={8} />
            </div>

            {/* James scores */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Hall of Fame Metrics</div>
              </div>
              <div className="james-grid">
                {[0, 1, 2].map(i => (
                  <div key={i} className="james-block">
                    <Skeleton width={60} height={10} />
                    <Skeleton width={40} height={22} style={{ marginTop: 4 }} />
                  </div>
                ))}
              </div>
            </div>

            {/* Awards */}
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Awards</div>
              </div>
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0' }}>
                  <Skeleton width={32} height={12} />
                  <Skeleton variant="circle" width={18} height={18} />
                  <Skeleton width="50%" height={13} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
