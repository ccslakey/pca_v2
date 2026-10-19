import { useEffect, useRef } from 'react';
import { ThemePicker } from 'pca-design-system';

export const Closed = () => (
  <div style={{ display: 'flex', justifyContent: 'flex-end', width: 280 }}>
    <ThemePicker />
  </div>
);

// The menu opens on click; open it once on mount so the card shows the list.
export const Open = () => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelector<HTMLButtonElement>('.tp-trigger')?.click();
  }, []);
  return (
    <div ref={ref} style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'flex-start', width: 280, height: 520 }}>
      <ThemePicker />
    </div>
  );
};
