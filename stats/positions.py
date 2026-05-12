from __future__ import annotations

from dataclasses import dataclass


POSITION_CODE_MAP = {
    "1": "P",
    "2": "C",
    "3": "1B",
    "4": "2B",
    "5": "3B",
    "6": "SS",
    "7": "LF",
    "8": "CF",
    "9": "RF",
    "D": "DH",
    "DH": "DH",
    "H": "H",
}

DEFENSIVE_POSITIONS = {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"}
PRIMARY_TIEBREAK = ["C", "SS", "2B", "3B", "CF", "RF", "LF", "1B", "DH", "OF", "P"]


@dataclass(frozen=True)
class ParsedPositionToken:
    position: str
    rank: int
    is_primary_marker: bool = False
    is_minor_marker: bool = False
    is_career_major_marker: bool = False
    is_career_minor_marker: bool = False
    reported_games: int | None = None


def parse_bref_positions(raw: str | None) -> list[ParsedPositionToken]:
    """
    Decode Baseball Reference's compact Positions Played string.

    BRef uses 1-9 for defensive positions, D/DH for designated hitter,
    and H for pinch-hitter or pinch-runner. Markers attach to the next
    token: * primary season position, / under ten games after this point,
    + career >300 games, - career <30 games.
    """
    if not raw:
        return []

    text = raw.strip()
    tokens: list[ParsedPositionToken] = []
    pending_primary = False
    pending_minor = False
    pending_career_major = False
    pending_career_minor = False
    i = 0

    while i < len(text):
        ch = text[i]
        if ch in {",", " ", "\t"}:
            i += 1
            continue
        if ch == "*":
            pending_primary = True
            i += 1
            continue
        if ch == "/":
            pending_minor = True
            i += 1
            continue
        if ch == "+":
            pending_career_major = True
            i += 1
            continue
        if ch == "-":
            pending_career_minor = True
            i += 1
            continue

        code: str | None = None
        if text[i : i + 2].upper() == "DH":
            code = "DH"
            i += 2
        elif ch.upper() in {"D", "H"}:
            code = ch.upper()
            i += 1
        elif ch in POSITION_CODE_MAP:
            code = ch
            i += 1
        else:
            i += 1
            continue

        tokens.append(
            ParsedPositionToken(
                position=POSITION_CODE_MAP[code],
                rank=len(tokens) + 1,
                is_primary_marker=pending_primary,
                is_minor_marker=pending_minor,
                is_career_major_marker=pending_career_major,
                is_career_minor_marker=pending_career_minor,
                reported_games=None,
            )
        )
        pending_primary = False
        pending_career_major = False
        pending_career_minor = False

    return tokens


def choose_primary_position(position_games: dict[str, int]) -> str | None:
    eligible = {pos: games for pos, games in position_games.items() if pos != "H"}
    if not eligible:
        return None
    order = {pos: idx for idx, pos in enumerate(PRIMARY_TIEBREAK)}
    return max(
        eligible,
        key=lambda pos: (eligible[pos], -order.get(pos, len(order)), pos),
    )
