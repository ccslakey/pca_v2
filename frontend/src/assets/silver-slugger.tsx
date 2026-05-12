const SilverSlugger = ({ color, size = 20 }: { color: string; size?: number }) => {
  // Starburst at (115, 72), outer r=42, inner r=16, 8 spikes
  const starPoints =
    "115,30 121,57 145,42 130,66 157,72 130,78 145,102 121,87 115,114 109,87 85,102 100,78 73,72 100,66 85,42 109,57";

  // Bat: barrel at (106,75) → handle at (195,42)
  // Perpendicular (0.348, 0.938), hw=17 at barrel, hw=5 at handle
  const batBody = "M 100,59 L 112,91 L 197,47 L 193,37 Z";

  return (
    <svg viewBox="0 0 210 140" width={size} height={size} xmlns="http://www.w3.org/2000/svg">

      {/* === MOTION LINES (behind ball) === */}
      <path d="M 4,63 L 21,67" stroke="#1a1a1a" strokeWidth="3.5" strokeLinecap="round" />
      <path d="M 1,75 L 19,76" stroke="#1a1a1a" strokeWidth="4"   strokeLinecap="round" />
      <path d="M 4,87 L 21,83" stroke="#1a1a1a" strokeWidth="3.5" strokeLinecap="round" />

      {/* === BASEBALL — fill only, outline drawn after starburst === */}
      <circle cx="55" cy="75" r="36" fill="#f0f0f0" />

      {/* === STARBURST (on top of ball fill, behind bat) === */}
      <polygon points={starPoints} fill={color} />
      <polygon points={starPoints} fill="none" stroke="#1a1a1a" strokeWidth="1.5" strokeLinejoin="round" />
      {/* White flash at contact center */}
      <circle cx="115" cy="72" r="13" fill="white" opacity={0.65} />

      {/* === BASEBALL — stitching and outline on top of starburst === */}
      {/* Left stitch curve */}
      <path d="M 40,54 C 33,63 33,78 40,90" fill="none" stroke="#888" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="37" y1="57" x2="41" y2="59" stroke="#888" strokeWidth="0.9" />
      <line x1="35" y1="64" x2="39" y2="65" stroke="#888" strokeWidth="0.9" />
      <line x1="35" y1="72" x2="39" y2="71" stroke="#888" strokeWidth="0.9" />
      <line x1="36" y1="79" x2="40" y2="78" stroke="#888" strokeWidth="0.9" />
      <line x1="38" y1="86" x2="42" y2="85" stroke="#888" strokeWidth="0.9" />
      {/* Right stitch curve */}
      <path d="M 68,54 C 75,63 75,78 68,90" fill="none" stroke="#888" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="67" y1="57" x2="71" y2="59" stroke="#888" strokeWidth="0.9" />
      <line x1="69" y1="64" x2="73" y2="65" stroke="#888" strokeWidth="0.9" />
      <line x1="69" y1="72" x2="73" y2="71" stroke="#888" strokeWidth="0.9" />
      <line x1="68" y1="79" x2="72" y2="78" stroke="#888" strokeWidth="0.9" />
      <line x1="67" y1="86" x2="71" y2="85" stroke="#888" strokeWidth="0.9" />
      {/* Ball outline */}
      <circle cx="55" cy="75" r="36" fill="none" stroke="#1a1a1a" strokeWidth="2.5" />

      {/* === BASEBALL BAT === */}
      {/* Shadow face (bottom/dark) */}
      <path d={batBody} fill={color} opacity={0.72} />
      {/* Highlight face (top strip) */}
      <path d="M 100,59 L 193,37 L 195,41 L 102,63 Z" fill={color} />
      {/* Barrel end cap (ellipse perpendicular to bat, ~-20°) */}
      <ellipse cx="106" cy="75" rx="17" ry="8" fill={color} opacity={0.85} transform="rotate(-20 106 75)" />
      <ellipse cx="105" cy="73" rx="11" ry="4" fill="white" opacity={0.2} transform="rotate(-20 105 73)" />
      {/* Center spine highlight */}
      <line x1="101" y1="60" x2="194" y2="38" stroke="white" strokeWidth="2" strokeLinecap="round" opacity={0.28} />
      {/* Bat outline */}
      <path d={batBody} fill="none" stroke="#1a1a1a" strokeWidth="1.8" strokeLinejoin="round" />
      <ellipse cx="106" cy="75" rx="17" ry="8" fill="none" stroke="#1a1a1a" strokeWidth="1.8" transform="rotate(-20 106 75)" />

      {/* Knob (handle-end cap) */}
      <ellipse cx="196" cy="42" rx="9" ry="5" fill={color} opacity={0.85} transform="rotate(-20 196 42)" />
      <ellipse cx="195" cy="41" rx="6" ry="3" fill={color} transform="rotate(-20 195 41)" />
      <ellipse cx="196" cy="42" rx="9" ry="5" fill="none" stroke="#1a1a1a" strokeWidth="1.5" transform="rotate(-20 196 42)" />

    </svg>
  );
};

export default SilverSlugger;
