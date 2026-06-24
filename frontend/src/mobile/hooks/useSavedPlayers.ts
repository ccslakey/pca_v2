import { useCallback, useEffect, useState } from 'react';

const KEY = 'pca:saved';

export interface SavedPlayer {
  bbref_id: string;
  name: string;
  pos: string;
}

function read(): SavedPlayer[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(list: SavedPlayer[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // storage full / unavailable — ignore
  }
}

/**
 * "Saved"/"Follow" list backed by localStorage. We store name + pos at save
 * time so the Saved tab can render without re-fetching each player.
 * Multiple mounted consumers stay in sync via the `storage` event + a custom
 * in-tab event.
 */
export function useSavedPlayers() {
  const [saved, setSaved] = useState<SavedPlayer[]>(read);

  useEffect(() => {
    const sync = () => setSaved(read());
    window.addEventListener('storage', sync);
    window.addEventListener('pca:saved-changed', sync);
    return () => {
      window.removeEventListener('storage', sync);
      window.removeEventListener('pca:saved-changed', sync);
    };
  }, []);

  const persist = useCallback((next: SavedPlayer[]) => {
    write(next);
    setSaved(next);
    window.dispatchEvent(new Event('pca:saved-changed'));
  }, []);

  const isSaved = useCallback(
    (bbrefId: string) => saved.some(p => p.bbref_id === bbrefId),
    [saved],
  );

  const toggle = useCallback(
    (player: SavedPlayer) => {
      const exists = read().some(p => p.bbref_id === player.bbref_id);
      const next = exists
        ? read().filter(p => p.bbref_id !== player.bbref_id)
        : [...read(), player];
      persist(next);
    },
    [persist],
  );

  const remove = useCallback(
    (bbrefId: string) => persist(read().filter(p => p.bbref_id !== bbrefId)),
    [persist],
  );

  return { saved, isSaved, toggle, remove };
}
