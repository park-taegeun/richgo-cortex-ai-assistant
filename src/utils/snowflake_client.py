"""
Snowflake connection utilities.
All Analyzer classes receive a SnowflakeClient instance —
no module holds a raw connection directly.
"""


class SnowflakeClient:
    """Thin wrapper around a snowflake-connector-python connection."""

    def __init__(self, conn):
        self.conn = conn

    def _cur(self):
        return self.conn.cursor()

    # ── Danji (complex) level ────────────────────────────────────────────────

    def fetch_danji_info(self, danji_id: str) -> dict:
        """DANJI_APT_INFO — single complex metadata row."""
        cur = self._cur()
        cur.execute("""
            SELECT BJD_CODE, SD, SGG, EMD, DANJI_ID, DANJI,
                   BUILDING_TYPE, AGES_YEAR, TOTAL_HOUSEHOLDS,
                   LIVING_SCORE, CONSTRUCTOR_RANK
            FROM DANJI_APT_INFO
            WHERE DANJI_ID = %s
            LIMIT 1
        """, (danji_id,))
        row = cur.fetchone()
        cur.close()
        if not row:
            raise ValueError(f"DANJI_ID '{danji_id}' not found in DANJI_APT_INFO")
        cols = ["bjd_code", "sd", "sgg", "emd", "danji_id", "danji",
                "building_type", "ages_year", "total_households",
                "living_score", "constructor_rank"]
        return dict(zip(cols, row))

    def fetch_market_price(self, danji_id: str, months: int = 12) -> list:
        """DANJI_APT_RICHGO_MARKET_PRICE_M_H — recent N months."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, MEAN_MEME_PRICE, MEAN_JEONSE_PRICE,
                   MEME_PRICE_PER_SUPPLY_PYEONG, JEONSE_PRICE_PER_SUPPLY_PYEONG,
                   MEME_CAP_PRICE
            FROM DANJI_APT_RICHGO_MARKET_PRICE_M_H
            WHERE DANJI_ID = %s
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (danji_id, months))
        rows = cur.fetchall()
        cur.close()
        cols = ["yyyymmdd", "mean_meme_price", "mean_jeonse_price",
                "meme_price_per_supply_pyeong", "jeonse_price_per_supply_pyeong",
                "meme_cap_price"]
        return [dict(zip(cols, r)) for r in rows]

    # ── Region level ─────────────────────────────────────────────────────────

    def fetch_region_price(self, sgg: str, months: int = 12) -> list:
        """REGION_APT_RICHGO_MARKET_PRICE_M_H — SGG level."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, TOTAL_HOUSEHOLDS, MEAN_MEME_PRICE, MEAN_JEONSE_PRICE
            FROM REGION_APT_RICHGO_MARKET_PRICE_M_H
            WHERE SGG = %s AND REGION_LEVEL = 'sgg'
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (sgg, months))
        rows = cur.fetchall()
        cur.close()
        cols = ["yyyymmdd", "total_households", "mean_meme_price", "mean_jeonse_price"]
        return [dict(zip(cols, r)) for r in rows]

    def fetch_region_price_sd(self, sd: str, months: int = 60) -> list:
        """REGION_APT_RICHGO_MARKET_PRICE_M_H — SD level (PIR Band fallback)."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, TOTAL_HOUSEHOLDS, MEAN_MEME_PRICE, MEAN_JEONSE_PRICE
            FROM REGION_APT_RICHGO_MARKET_PRICE_M_H
            WHERE SD = %s AND REGION_LEVEL = 'sd'
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (sd, months))
        rows = cur.fetchall()
        cur.close()
        cols = ["yyyymmdd", "total_households", "mean_meme_price", "mean_jeonse_price"]
        return [dict(zip(cols, r)) for r in rows]

    def fetch_population_movement(self, sgg: str, months: int = 36) -> list:
        """REGION_POPULATION_MOVEMENT — SGG net migration."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, POPULATION
            FROM REGION_POPULATION_MOVEMENT
            WHERE SGG = %s AND MOVEMENT_TYPE = '순이동' AND REGION_LEVEL = 'sgg'
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (sgg, months))
        rows = cur.fetchall()
        cur.close()
        return [{"yyyymmdd": r[0], "population": r[1]} for r in rows]
