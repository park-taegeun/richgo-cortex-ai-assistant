"""
modules/data_loader.py
Richgo-Cortex AI — Data Layer

Responsibilities:
  - Snowflake connection (RichgoCortexEngine factory)
  - 단지 목록 로드: 유령 단지 소탕 INNER JOIN 쿼리
  - st.cache_* 데코레이터는 여기서만 선언

Public API:
  get_engine()                       → RichgoCortexEngine | None
  get_all_danji_list(engine)         → List[Dict]
"""
from typing import Dict, List, Optional

import os
import streamlit as st


# ── Engine Factory ─────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_engine():
    """
    실제 Snowflake 연결 시도.
    실패 시 None 반환 → 호출부에서 Demo 모드로 전환.
    """
    try:
        import snowflake.connector
        from src.core.engine import RichgoCortexEngine

        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "RICHGO_KR"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "HACKATHON_2026"),
        )
        return RichgoCortexEngine(conn)
    except Exception:
        return None


# ── Danji List Loader ──────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_danji_list(_engine) -> List[Dict]:
    """
    Snowflake DB 전 지역 단지 실시간 동기화.

    핵심 로직 — 유령 단지 소탕 (Ghost Danji Elimination):
      INNER JOIN으로 DANJI_APT_RICHGO_MARKET_PRICE_M_H 테이블과 교차하여
      시세 데이터(MEAN_MEME_PRICE, MEAN_JEONSE_PRICE)가 실제로 존재하는
      단지만 추출합니다. (2,928개 정예 단지)

    Returns:
        list of {"DANJI_ID", "SD", "SGG", "DANJI_NAME"}
        엔진 없음 → []
    """
    if not _engine:
        return []
    try:
        query = """
        SELECT DISTINCT
            a.DANJI_ID,
            a.SD,
            a.SGG,
            a.DANJI
        FROM RICHGO_KR.HACKATHON_2026.DANJI_APT_INFO          a
        INNER JOIN RICHGO_KR.HACKATHON_2026.DANJI_APT_RICHGO_MARKET_PRICE_M_H b
            ON a.DANJI_ID = b.DANJI_ID
        WHERE b.MEAN_MEME_PRICE   IS NOT NULL
          AND b.MEAN_JEONSE_PRICE IS NOT NULL
        ORDER BY a.SD ASC, a.SGG ASC, a.DANJI ASC
        """
        cur = _engine._client.conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        return [
            {"DANJI_ID": r[0], "SD": r[1], "SGG": r[2], "DANJI_NAME": r[3]}
            for r in rows
        ]
    except Exception as e:
        st.error(f"단지 목록 동기화 실패: {e}")
        return []


# ── Cascading Selector Helper ──────────────────────────────────────────────────

def render_cascading_selector(danji_list: List[Dict], prefix: str) -> Optional[Dict]:
    """
    시/도 → 시/군/구 → 단지명 3단 연동 셀렉터.

    Args:
        danji_list: get_all_danji_list() 반환값
        prefix:     session_state 키 충돌 방지용 접두어 ("cur" | "tgt")

    Returns:
        선택된 단지 dict {"DANJI_ID", "SD", "SGG", "DANJI_NAME"} | None
    """
    sd_list = sorted({d["SD"] for d in danji_list if d.get("SD")})
    if not sd_list:
        return None

    sd_key    = f"{prefix}_sd"
    sgg_key   = f"{prefix}_sgg"
    danji_key = f"{prefix}_danji"

    if sd_key not in st.session_state:
        st.session_state[sd_key] = sd_list[0]

    selected_sd = st.selectbox(
        "시/도", sd_list, key=sd_key,
        help="분석을 원하는 시/도 지역을 선택하세요.",
    )

    sgg_list = sorted({
        d["SGG"] for d in danji_list
        if d.get("SD") == selected_sd and d.get("SGG")
    })
    if not sgg_list:
        return None

    if sgg_key not in st.session_state or st.session_state[sgg_key] not in sgg_list:
        st.session_state[sgg_key] = sgg_list[0]

    selected_sgg = st.selectbox(
        "시/군/구", sgg_list, key=sgg_key,
        help="선택한 시/도의 세부 구역을 선택하세요.",
    )

    filtered = sorted(
        [d for d in danji_list if d.get("SD") == selected_sd and d.get("SGG") == selected_sgg],
        key=lambda x: x.get("DANJI_NAME", ""),
    )
    if not filtered:
        return None

    return st.selectbox(
        "단지명", filtered,
        format_func=lambda x: x.get("DANJI_NAME", ""),
        key=danji_key,
        help="비교 분석할 최종 단지를 선택하세요.",
    )
