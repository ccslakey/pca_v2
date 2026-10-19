import { SimilarPlayersPanel } from 'pca-design-system';
import { trout, similarToTrout } from './_players';

export const Batter = () => (
  <div style={{ width: 360 }}>
    <SimilarPlayersPanel fromId={trout.id} similar={similarToTrout} />
  </div>
);
