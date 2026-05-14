"""
Curated comparison groups surfaced on the Compare page when no ?compare= URL
param is present. The frontend picks one randomly to populate the chart on
first visit; each entry is also a permanent linkable URL via its slug, which
will back the future Featured-matchups gallery (see LAUNCH.md).

To extend: append an entry. bbref_ids must exist in the Player table — verify
beforehand or the player will be silently dropped from the response.
"""

FEATURED_COMPARISONS = [
    {
        "slug":       "goat-batters",
        "label":      "The GOAT batter debate",
        "player_ids": ["ruthba01", "bondsba01", "willite01"],
    },
    {
        "slug":       "cf-eras",
        "label":      "Center fielders across eras",
        "player_ids": ["cobbty01", "dimagjo01", "mayswi01", "mantlmi01", "troutmi01"],
    },
    {
        "slug":       "goat-pitchers",
        "label":      "The greatest aces ever",
        "player_ids": ["youngcy01", "johnswa01", "maddugr01", "martipe02"],
    },
    {
        "slug":       "closer-revolution",
        "label":      "The closer revolution",
        "player_ids": ["riverma01", "hoffmtr01", "eckerde01"],
    },
    {
        "slug":       "modern-power",
        "label":      "Modern power hitters",
        "player_ids": ["pujolal01", "cabremi01", "rodrial01"],
    },
    {
        "slug":       "lefty-aces",
        "label":      "Left-handed aces",
        "player_ids": ["grovele01", "koufasa01", "johnsra05", "kershcl01"],
    },
    {
        "slug":       "shortstops",
        "label":      "Shortstops across eras",
        "player_ids": ["wagneho01", "ripkeca01", "jeterde01"],
    },
    {
        "slug":       "dead-ball-aces",
        "label":      "Dead-ball-era aces",
        "player_ids": ["youngcy01", "johnswa01", "mathech01", "alexape01"],
    },
    {
        "slug":       "hits-kings",
        "label":      "Hit collectors",
        "player_ids": ["rosepe01", "cobbty01", "suzukic01"],
    },
    {
        "slug":       "two-way-greats",
        "label":      "Two-way superstars",
        "player_ids": ["ruthba01", "ohtansh01"],
    },
    {
        "slug":       "modern-aces",
        "label":      "Modern aces",
        "player_ids": ["verlaju01", "scherma01", "kershcl01"],
    },
    {
        "slug":       "contact-masters",
        "label":      "Contact-hitting greats",
        "player_ids": ["gwynnto01", "boggswa01", "suzukic01"],
    },
    {
        "slug":       "speed-power",
        "label":      "Speed and power",
        "player_ids": ["henderi01", "bondsba01", "troutmi01"],
    },
    {
        "slug":       "1970s-icons",
        "label":      "1970s icons",
        "player_ids": ["schmimi01", "benchjo01", "seaveto01"],
    },
]
