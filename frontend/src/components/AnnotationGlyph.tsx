import {
  BaseballCapIcon,
  BaseballHelmetIcon,
  BaseballIcon,
  CrownIcon,
  FlagBannerIcon,
  MedalIcon,
  AxeIcon,
  StarIcon,
  TrophyIcon,
  ShieldChevronIcon,
} from "@phosphor-icons/react";
import type { AwardKind } from "../types";
import CyYoung from "../assets/cy-young-trophy";
import SilverSlugger from "../assets/silver-slugger";
import GoldGlove from "../assets/gold-glove";

interface Props {
  kind: AwardKind;
  color: string;
  size?: number;
}

export function AnnotationGlyph({ kind, color, size = 20 }: Props) {
  if (kind === "mvp")
    return <MedalIcon size={size} color={color} weight="fill" />;
  if (kind === "asg")
    return <StarIcon size={size} color={color} weight="fill" />;
  if (kind === "ws")
    return <TrophyIcon size={size} color={color} weight="fill" />;
  if (kind === "roty")
    return <BaseballHelmetIcon size={size} color={color} weight="fill" />;
  if (kind === "tc_p" || kind === "tc_b")
    return <CrownIcon size={size} color={color} weight="fill" />;
  if (kind === "cy") return <CyYoung color={color} size={size} />;
  if (kind === "ss") return <SilverSlugger color={color} size={24} />;
  if (kind === "gg") return <GoldGlove color={color} size={size} />;
  if (kind === "hof")
    return <BaseballIcon size={size} color={color} weight="fill" />;
  if (kind === "postmvp")
    return <BaseballCapIcon size={size} color={color} weight="fill" />;
  if (kind === "bat_title") return <AxeIcon color={color} size={size} />;
  if (kind === "era_title") return <FlagBannerIcon color={color} size={size} />;
  if (kind === "all_mlb")
    return <ShieldChevronIcon color={color} size={size} />;
}
