interface Props {
  kind: 'mvp' | 'cy' | 'gg' | 'il' | 'asg';
  color: string;
}

export function AnnotationGlyph({ kind, color }: Props) {
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
  if (kind === 'il') {
    return (
      <g>
        <rect x="-5" y="-2.5" width="10" height="5" rx="1.5" fill={color} opacity="0.25" stroke={color} strokeWidth="1.2" transform="rotate(-30)" />
        <line x1="-1.6" y1="-0.9" x2="1.6" y2="0.9" stroke={color} strokeWidth="1.2" transform="rotate(-30)" />
        <line x1="-1.6" y1="0.9" x2="1.6" y2="-0.9" stroke={color} strokeWidth="1.2" transform="rotate(-30)" />
      </g>
    );
  }
  // asg
  return (
    <g stroke={color} strokeWidth="1.4" strokeLinecap="round">
      <line x1="0" y1="-4" x2="0" y2="4" />
      <line x1="-3.5" y1="-2" x2="3.5" y2="2" />
      <line x1="-3.5" y1="2" x2="3.5" y2="-2" />
    </g>
  );
}
