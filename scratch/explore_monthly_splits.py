"""
Exploration: Monthly batting splits via pybaseball.get_splits
=============================================================

STATUS: Shelved — scraping cost is too high for full ingest.

FINDINGS
--------
pybaseball.get_splits(bbref_id, year=YYYY) hits the BRef batting splits
page and returns a MultiIndex DataFrame.  Monthly rows live under the
'Months' level:

    from pybaseball import get_splits
    df = get_splits('troutmi01', year=2023)
    monthly = df.loc['Months']
    # index: ['April/March', 'May', 'June', 'July', 'August']
    # columns include: PA, BA, OBP, SLG, OPS, HR, RBI, BB, SO, BAbip, tOPS+, sOPS+

Sample output for Trout 2023:
    Month          PA    BA    OBP   SLG   OPS
    April/March   124  .308  .395  .589  .984
    May           112  .245  .339  .449  .788
    June          109  .227  .367  .420  .787
    July           13  .273  .385  .545  .930
    August          4  .250  .250  .250  .500

'September/October' only appears when the player had PAs in that month;
same for months where they were on the IL the whole month.

SCRAPING COST
-------------
One BRef request per (player, year).  At 10 req/min (BRef rate limit):

    500 batters × 6 years  = 3,000 requests  ≈  5 hours
    1,000 batters × 10 yrs = 10,000 requests ≈  17 hours

Full coverage is not practical.  Feasible subsets:
  - Players with career WAR > 30: ~150 players × 6 seasons = 900 req (~1.5 hrs)
  - On-demand fetch-and-cache on first profile view: adds 2–5 s latency
    per uncached player; acceptable for demo but not clean in a sync view

PROPOSED DATA MODEL (if implemented)
-------------------------------------
class BattingMonthly(models.Model):
    player       = models.ForeignKey(Player, on_delete=models.CASCADE,
                                     related_name='batting_monthly')
    year         = models.SmallIntegerField()
    month        = models.SmallIntegerField()  # 4=Apr 5=May 6=Jun 7=Jul 8=Aug 9=Sep
    pa           = models.SmallIntegerField(null=True)
    batting_avg  = models.FloatField(null=True)
    on_base_pct  = models.FloatField(null=True)
    slugging_pct = models.FloatField(null=True)
    ops          = models.FloatField(null=True)

    class Meta:
        unique_together = ('player', 'year', 'month')

MONTH NORMALISATION
-------------------
BRef labels the first month 'April/March' (spring training games bleed in).
Map to integer month with:

    MONTH_MAP = {
        'March/April': 4, 'April/March': 4, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 9, 'September/October': 9,
    }

USAGE EXAMPLE
-------------
    from pybaseball import get_splits

    def fetch_monthly(bbref_id: str, year: int):
        df = get_splits(bbref_id, year=year)
        try:
            monthly = df.loc['Months']
        except KeyError:
            return []  # no monthly split data for this player/year

        MONTH_MAP = {
            'March/April': 4, 'April/March': 4, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 9, 'September/October': 9,
        }
        rows = []
        for label, row in monthly.iterrows():
            month = MONTH_MAP.get(label)
            if month is None:
                continue
            rows.append({
                'month': month,
                'pa': int(row['PA']) if row['PA'] else None,
                'batting_avg': float(row['BA']) if row['BA'] else None,
                'on_base_pct': float(row['OBP']) if row['OBP'] else None,
                'slugging_pct': float(row['SLG']) if row['SLG'] else None,
                'ops': float(row['OPS']) if row['OPS'] else None,
            })
        return rows
"""
