import { Skeleton } from '../Skeleton';

export function ChartSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <Skeleton width="100%" height={360} radius={8} />
      <Skeleton width="100%" height={48} radius={6} />
    </div>
  );
}
