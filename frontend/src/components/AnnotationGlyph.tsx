import type { AwardKind } from '../types';

interface Props {
  kind:  AwardKind;
  color: string;
}

export function AnnotationGlyph({ kind, color }: Props) {
  // Shared style props reused across multiple glyphs
  const stroke1 = { stroke: color, strokeWidth: 1.4, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };

  if (kind === 'mvp') {
    return (
      <path
        d="M0,-5 L1.4,-1.5 L5,-1.5 L2.1,0.7 L3.2,4.3 L0,2.1 L-3.2,4.3 L-2.1,0.7 L-5,-1.5 L-1.4,-1.5 Z"
        fill={color}
      />
    );
  }

  if (kind === 'cy') {
    return <text className="annot-glyph" textAnchor="middle" dy="3.4" fill={color}>CY</text>;
  }

  if (kind === 'gg') {
    return <path d="M0,-4.5 L4.5,0 L0,4.5 L-4.5,0 Z" fill="none" stroke={color} strokeWidth="1.5" />;
  }

  if (kind === 'asg') {
    return (
      <g stroke={color} strokeWidth="1.4" strokeLinecap="round">
        <line x1="0" y1="-4" x2="0" y2="4" />
        <line x1="-3.5" y1="-2" x2="3.5" y2="2" />
        <line x1="-3.5" y1="2" x2="3.5" y2="-2" />
      </g>
    );
  }

  if (kind === 'ws') {
    // Trophy: open cup, narrow stem, wide base
    return (
      <g {...stroke1}>
        <path d="M -3,-5 L -3,0 Q 0,3.5 3,0 L 3,-5" />
        <line x1="0" y1="3.5" x2="0" y2="5.5" />
        <line x1="-2.5" y1="5.5" x2="2.5" y2="5.5" />
      </g>
    );
  }

  if (kind === 'ss') {
    // Silver Slugger bat: diagonal line, knob at handle end
    return (
      <g stroke={color} strokeLinecap="round" fill="none">
        <line x1="-3.5" y1="5" x2="4" y2="-4.5" strokeWidth="2.2" />
        <circle cx="-4.5" cy="5.5" r="1.2" fill={color} strokeWidth="0" />
      </g>
    );
  }

  if (kind === 'hof') {
    // Hall of Fame: filled pentagon
    return <path d="M0,-5 L4.75,-1.55 L2.94,4.05 L-2.94,4.05 L-4.75,-1.55 Z" fill={color} />;
  }

  if (kind === 'roty') {
    // Rookie of the Year: upward arrow
    return (
      <g {...stroke1}>
        <polyline points="-3.5,4 0,-4.5 3.5,4" />
        <line x1="-2" y1="1.5" x2="2" y2="1.5" />
      </g>
    );
  }

  if (kind === 'tc_b') {
    // Triple Crown (batting): TC text
    return <text className="annot-glyph" textAnchor="middle" dy="3.4" fill={color}>TC</text>;
  }

  if (kind === 'tc_p') {
    // Triple Crown (pitching): crown silhouette, filled
    return (
      <path
        d="M -5,4 L -5,-1 L -2.5,2 L 0,-4 L 2.5,2 L 5,-1 L 5,4 Z"
        fill={color}
      />
    );
  }

  if (kind === 'postmvp') {
    // Postseason MVP: 4-point star inside a ring
    return (
      <g>
        <circle cx="0" cy="0" r="5.5" fill="none" stroke={color} strokeWidth="1.2" />
        <path d="M0,-3.5 L1.1,-1.1 L3.5,0 L1.1,1.1 L0,3.5 L-1.1,1.1 L-3.5,0 L-1.1,-1.1 Z" fill={color} />
      </g>
    );
  }

  if (kind === 'bat_title') {
    return <text className="annot-glyph" textAnchor="middle" dy="3.4" fill={color}>BT</text>;
  }

  if (kind === 'era_title') {
    return <text className="annot-glyph" textAnchor="middle" dy="3.4" fill={color}>ET</text>;
  }

  // all_mlb: shield outline
  return (
    <path
      d="M -4,-5 L 4,-5 L 4,0 Q 4,2.5 0,5.5 Q -4,2.5 -4,0 Z"
      {...stroke1}
      strokeWidth={1.4}
    />
  );
}
