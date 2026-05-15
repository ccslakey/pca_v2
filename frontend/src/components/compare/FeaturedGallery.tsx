import './FeaturedGallery.scss';
import { useFeatured } from '../../hooks';
import { playerColor } from '../../utils/color';
import { Skeleton } from '../Skeleton';
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

function TrioCardSkeleton() {
  return (
    <div className="featured-card" aria-hidden="true">
      <Skeleton width="80%" height={13} />
      <div className="featured-card-avatars">
        <Skeleton variant="circle" width={26} height={26} />
        <Skeleton variant="circle" width={26} height={26} />
        <Skeleton variant="circle" width={26} height={26} />
      </div>
      <Skeleton width="60%" height={11} />
    </div>
  );
}

export function FeaturedGallery({ onSelect }: Props) {
  const { data } = useFeatured();
  const trios = data?.trios ?? [];

  // Header chrome renders eagerly (h2 is the LCP element — paint it before the
  // API resolves). Cards render as skeletons until data arrives.
  return (
    <div className="featured-gallery">
      <div className="featured-gallery-header">
        <h2 className="featured-gallery-title">
          Featured matchups
          {trios.length > 0 && (
            <span className="muted">{trios.length} curated comparisons</span>
          )}
        </h2>
        <span className="featured-gallery-hint">scroll →</span>
      </div>
      <div className="featured-scroll-wrap">
        <div className="featured-scroll">
          {trios.length > 0
            ? trios.map(t => (
                <TrioCard
                  key={t.slug}
                  trio={t}
                  onSelect={() => onSelect(t.players.map(p => p.bbref_id))}
                />
              ))
            : Array.from({ length: 6 }).map((_, i) => <TrioCardSkeleton key={i} />)}
        </div>
      </div>
    </div>
  );
}
