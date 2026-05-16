import { Skeleton } from '../Skeleton';

export function ChartSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <Skeleton width="100%" height={420} radius={8} />
      {/* mirror .brush-wrap: margin-top 14 + border-top 1 + padding-top 12 + SVG 60 */}
      <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line-soft)' }}>
        <Skeleton width="100%" height={60} radius={4} />
      </div>
    </div>
  );
}
