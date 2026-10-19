import { AnnotationGlyph } from 'pca-design-system';

const KINDS = [
  ['mvp', 'MVP'], ['cy', 'Cy Young'], ['roty', 'Rookie of the Year'], ['gg', 'Gold Glove'],
  ['ss', 'Silver Slugger'], ['tc_b', 'Triple Crown (Bat)'], ['tc_p', 'Triple Crown (Pit)'],
  ['hof', 'Hall of Fame'], ['postmvp', 'Postseason MVP'], ['bat_title', 'Batting Title'],
  ['era_title', 'ERA Title'], ['all_mlb', 'All-MLB'], ['ws', 'World Series'], ['asg', 'All-Star'],
] as const;

export const AllAwardKinds = () => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 180px)', gap: '10px 16px' }}>
    {KINDS.map(([kind, label]) => (
      <div key={kind} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-1)' }}>
        <AnnotationGlyph kind={kind} color="var(--accent)" size={20} />
        {label}
      </div>
    ))}
  </div>
);

export const Sizes = () => (
  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
    {[12, 16, 20, 28].map((size) => (
      <AnnotationGlyph key={size} kind="cy" color="var(--chart-6)" size={size} />
    ))}
  </div>
);
