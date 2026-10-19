import { useState } from 'react';
import { ChipBar } from 'pca-design-system';
import { trout, judge, kershaw, ohtani } from './_players';

export const Comparing = () => {
  const [hover, setHover] = useState<string | null>(null);
  const [players, setPlayers] = useState([trout, judge, kershaw, ohtani]);
  return (
    <div style={{ width: 720 }}>
      <ChipBar players={players} hoverPlayerId={hover} setHoverPlayerId={setHover}
        onRemove={(id) => setPlayers((ps) => ps.filter((p) => p.id !== id))} />
    </div>
  );
};

export const OnePlayerHovered = () => (
  <div style={{ width: 720 }}>
    <ChipBar players={[ohtani]} hoverPlayerId={ohtani.id} setHoverPlayerId={() => {}} onRemove={() => {}} />
  </div>
);
