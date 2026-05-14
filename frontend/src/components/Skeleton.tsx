import './Skeleton.scss';
import type { CSSProperties } from 'react';

interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  radius?: number | string;
  variant?: 'rect' | 'text' | 'circle';
  className?: string;
  style?: CSSProperties;
}

export function Skeleton({
  width,
  height,
  radius,
  variant = 'rect',
  className = '',
  style,
}: SkeletonProps) {
  const variantClass = variant === 'text' ? 'skeleton--text' : variant === 'circle' ? 'skeleton--circle' : '';
  return (
    <div
      className={`skeleton ${variantClass} ${className}`.trim()}
      style={{ width, height, borderRadius: radius, ...style }}
      aria-hidden="true"
    />
  );
}
