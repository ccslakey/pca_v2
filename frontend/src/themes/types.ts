export interface Theme {
  id: string;
  concept: string;
  label: string;
  mode: 'dark' | 'light';
  tagline: string;
  fonts: { sans: string; mono: string; display: string };
  radius: { sm: number; md: number; lg: number };
  shadow: string;
  chartGridStyle: string;
  colors: {
    bg0: string; bg1: string; bg2: string; bg3: string;
    line: string; lineSoft: string;
    text0: string; text1: string; text2: string; text3: string;
    accent: string; accent2: string;
    success: string; danger: string; warning: string;
    chart: [string, string, string, string, string, string, string, string, string, string];
    gridDot: string;
  };
}
