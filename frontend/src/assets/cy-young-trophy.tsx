const CyYoung = ({ color, size = 20 }: { color: string; size?: number }) => {
  return (
    <svg
      viewBox="0 0 200 225"
      width={size}
      height={size}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
    >
      {/* Far-left spike */}
      <polygon points="6,14 32,138 54,146" fill={color} opacity={0.75} />
      {/* Near-left spike (lighter face) */}
      <polygon points="38,16 56,138 74,144" fill={color} />
      {/* Near-right spike */}
      <polygon points="162,16 126,144 144,138" fill={color} />
      {/* Far-right spike */}
      <polygon points="194,14 146,146 168,138" fill={color} opacity={0.75} />

      {/* Spike shadow overlaps for depth */}
      <polygon points="38,16 56,138 54,146 32,138" fill="black" opacity={0.2} />
      <polygon
        points="162,16 144,138 146,146 168,138"
        fill="black"
        opacity={0.2}
      />

      {/* Base: top diamond platform */}
      <polygon points="100,138 126,152 100,166 74,152" fill="#b4b4b4" />
      <polygon
        points="100,138 126,152 100,144 74,152"
        fill="#ccc"
        opacity={0.5}
      />
      <polygon
        points="100,166 126,152 100,162 74,152"
        fill="#888"
        opacity={0.4}
      />

      {/* Arm collar ring (sits on diamond) */}
      <ellipse cx="100" cy="138" rx="20" ry="7" fill="#a0a0a0" />
      <ellipse cx="100" cy="137" rx="18" ry="5" fill="#bcbcbc" />

      {/* Upper base tier */}
      <polygon points="58,152 142,152 152,168 48,168" fill="#ababab" />
      <polygon points="100,152 142,152 152,168 100,168" fill="#989898" />

      {/* Base tier step */}
      <polygon points="48,168 152,168 156,174 44,174" fill="#888" />
      <polygon
        points="48,168 152,168 100,170 48,170"
        fill="#bbb"
        opacity={0.3}
      />

      {/* Lower base body */}
      <rect x="40" y="174" width="120" height="32" fill="#a8a8a8" />
      {/* Lower base highlight */}
      <rect
        x="48"
        y="177"
        width="104"
        height="10"
        fill="#ccc"
        opacity={0.35}
        rx="1"
      />
      {/* Lower base shadow */}
      <rect x="40" y="195" width="120" height="11" fill="#888" opacity={0.5} />

      {/* Base bottom trim */}
      <polygon points="40,206 160,206 154,218 46,218" fill="#8a8a8a" />
      <polygon
        points="40,206 160,206 100,208 40,208"
        fill="#ccc"
        opacity={0.2}
      />

      {/* Forearm */}
      <path
        d="M83,110 C82,128 82,144 100,148 C118,144 118,128 117,110 Z"
        fill="#bcbcbc"
      />
      {/* Forearm highlight (left face) */}
      <path
        d="M83,110 C82,128 82,144 100,148 C100,140 96,124 88,112 Z"
        fill="#d4d4d4"
      />
      {/* Forearm shadow (right face) */}
      <path
        d="M117,110 C118,128 118,144 100,148 C100,140 104,124 112,112 Z"
        fill="#a4a4a4"
      />

      {/* Wrist band */}
      <ellipse cx="100" cy="112" rx="17" ry="6" fill="#a8a8a8" />
      <ellipse cx="100" cy="111" rx="15" ry="4" fill="#c4c4c4" />

      {/* Fist main mass */}
      <path
        d="M78,92 C77,74 80,60 100,58 C120,60 123,74 122,92 C122,107 113,120 100,122 C87,120 78,107 78,92 Z"
        fill="#c4c4c4"
      />
      {/* Fist shadow right */}
      <path
        d="M100,58 C120,60 123,74 122,92 C122,107 113,120 100,122 C112,118 116,106 116,92 C116,78 112,64 100,62 Z"
        fill="#aaa"
      />
      {/* Fist highlight left */}
      <path
        d="M100,58 C80,60 77,74 78,92 C78,107 87,120 100,122 C88,118 84,106 84,92 C84,78 88,64 100,62 Z"
        fill="#d8d8d8"
      />

      {/* Knuckle bumps across top */}
      <ellipse cx="87" cy="70" rx="8" ry="5.5" fill="#b4b4b4" />
      <ellipse cx="100" cy="66" rx="8" ry="5.5" fill="#b4b4b4" />
      <ellipse cx="113" cy="70" rx="8" ry="5.5" fill="#b4b4b4" />
      {/* Knuckle highlights */}
      <ellipse cx="86" cy="68" rx="5" ry="3" fill="#ccc" opacity={0.6} />
      <ellipse cx="99" cy="64" rx="5" ry="3" fill="#ccc" opacity={0.6} />
      <ellipse cx="112" cy="68" rx="5" ry="3" fill="#ccc" opacity={0.6} />

      {/* Thumb (left side) */}
      <path
        d="M78,96 C74,90 75,82 79,79 C84,77 88,82 86,90 C84,96 81,99 78,96 Z"
        fill="#c0c0c0"
      />
      <path d="M78,96 C74,90 75,82 79,79 C80,82 79,88 80,93 Z" fill="#d0d0d0" />

      {/* Pinky (right side hint) */}
      <path
        d="M122,90 C125,86 126,80 122,77 C119,76 117,80 118,86 Z"
        fill="#b8b8b8"
      />

      {/* Baseball */}
      <circle cx="100" cy="44" r="27" fill="#ebebeb" />
      {/* Ball shadow (right-bottom) */}
      <path
        d="M108,20 A27,27 0 0 1 127,58 A27,27 0 0 0 108,20 Z"
        fill="#c8c8c8"
        opacity={0.6}
      />
      {/* Ball highlight (left-top) */}
      <circle cx="91" cy="35" r="9" fill="white" opacity={0.4} />

      {/* Stitching: left S-curve */}
      <path
        d="M88,30 C82,37 82,51 88,58"
        fill="none"
        stroke="#a0a0a0"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* Stitching: right S-curve */}
      <path
        d="M112,30 C118,37 118,51 112,58"
        fill="none"
        stroke="#a0a0a0"
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      {/* Left stitch ticks */}
      <line
        x1="85"
        y1="33"
        x2="90"
        y2="35"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="83"
        y1="40"
        x2="88"
        y2="42"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="83"
        y1="47"
        x2="88"
        y2="45"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="85"
        y1="54"
        x2="90"
        y2="52"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />

      {/* Right stitch ticks */}
      <line
        x1="110"
        y1="33"
        x2="115"
        y2="35"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="112"
        y1="40"
        x2="117"
        y2="42"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="112"
        y1="47"
        x2="117"
        y2="45"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <line
        x1="110"
        y1="54"
        x2="115"
        y2="52"
        stroke="#a0a0a0"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
};

export default CyYoung;
