import { Skeleton } from 'pca-design-system';

export const TextLines = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 320 }}>
    <Skeleton variant="text" width="55%" />
    <Skeleton variant="text" width="100%" />
    <Skeleton variant="text" width="88%" />
  </div>
);

export const PlayerRow = () => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: 320 }}>
    <Skeleton variant="circle" width={36} height={36} />
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
      <Skeleton variant="text" width="70%" />
      <Skeleton variant="text" width="40%" />
    </div>
    <Skeleton width={36} height={18} radius={9} />
  </div>
);

export const ChartBlock = () => <Skeleton width={320} height={140} radius="var(--radius)" />;
