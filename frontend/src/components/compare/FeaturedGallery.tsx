import './FeaturedGallery.scss';
import { useFeatured } from '../../hooks';
import { playerColor } from '../../utils/color';
import type { FeaturedTrio } from '../../types';

interface Props {
  onSelect: (playerIds: string[]) => void;
}

function initials(first: string, last: string): string {
  return `${first[0] ?? ''}${last[0] ?? ''}`.toUpperCase();
}

function TrioCard({ trio, onSelect }: { trio: FeaturedTrio; onSelect: () => void }) {
  return (
    <button className="featured-card" onClick={onSelect} type="button">
      <div className="featured-card-label">{trio.label}</div>
      <div className="featured-card-avatars">
        {trio.players.map(p => (
          <span
            key={p.bbref_id}
            className="featured-avatar"
            style={{ background: playerColor(p.bbref_id) }}
            title={`${p.first_name} ${p.last_name}`}
          >
            {initials(p.first_name, p.last_name)}
          </span>
        ))}
      </div>
      <div className="featured-card-names">
        {trio.players.map(p => p.last_name).join(' · ')}
      </div>
    </button>
  );
}

export function FeaturedGallery({ onSelect }: Props) {
  const { data } = useFeatured();
  if (!data?.trios.length) return null;

  return (
    <div className="featured-gallery">
      <div className="featured-gallery-header">
        <h2 className="featured-gallery-title">
          Featured matchups
          <span className="muted">{data.trios.length} curated comparisons</span>
        </h2>
        <span className="featured-gallery-hint">scroll →</span>
      </div>
      <div className="featured-scroll-wrap">
        <div className="featured-scroll">
          {data.trios.map(t => (
            <TrioCard
              key={t.slug}
              trio={t}
              onSelect={() => onSelect(t.players.map(p => p.bbref_id))}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
