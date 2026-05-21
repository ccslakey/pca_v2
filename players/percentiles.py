"""Position-based career WAR percentile rankings via SQL window functions."""
from django.db import connection


def war_percentile(bbref_id: str, primary_position: str | None) -> dict | None:
    """
    Return {"top_pct": float, "position": str, "rank": int, "n": int} or None.

    top_pct is the share of same-position players this player beats by career WAR;
    top_pct=3.2 means this player is in the top 3.2% at their position.
    """
    if not primary_position:
        return None

    sql = """
        WITH career_war AS (
            SELECT
                p.bbref_id,
                p.primary_position,
                COALESCE(b.war, 0) + COALESCE(pi.war, 0) AS war
            FROM players_player p
            LEFT JOIN (
                SELECT player_id, SUM(war) AS war
                FROM stats_battingseason
                GROUP BY player_id
            ) b  ON b.player_id  = p.bbref_id
            LEFT JOIN (
                SELECT player_id, SUM(war) AS war
                FROM stats_pitchingseason
                GROUP BY player_id
            ) pi ON pi.player_id = p.bbref_id
            WHERE p.primary_position IS NOT NULL
        ),
        ranked AS (
            SELECT
                bbref_id,
                ROW_NUMBER() OVER (PARTITION BY primary_position ORDER BY war)      AS rn,
                RANK()       OVER (PARTITION BY primary_position ORDER BY war DESC)  AS rnk,
                COUNT(*)     OVER (PARTITION BY primary_position)                    AS n
            FROM career_war
        )
        SELECT
            ROUND(CAST((1.0 - (rn - 1.0) / n) * 100 AS NUMERIC), 1) AS top_pct,
            rnk,
            n
        FROM ranked
        WHERE bbref_id = %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [bbref_id])
        row = cursor.fetchone()

    if row is None:
        return None

    top_pct, rank, n = row
    return {
        "top_pct": float(top_pct),
        "position": primary_position,
        "rank": int(rank),
        "n": int(n),
    }
