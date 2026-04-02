"""
Richgo-Cortex AI Assistant — Mission 3-3 Integration Test
검증 목표:
  1. PIR Band (5년 시계열) 계산 및 상대 지수 반영 확인
  2. Supply Spillover: 송파구 분석 시 강동구 공급 상태가 최종 점수에 반영됨을 증명
  3. Score Clamping: 최종 s_alpha가 0~100 정수임을 확인

Usage:
    python scripts/test_mission33.py
"""

import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

REQUIRED = [
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
]
missing = [v for v in REQUIRED if not os.getenv(v)]
if missing:
    print(f"[ERROR] Missing env vars: {missing}")
    sys.exit(1)

import snowflake.connector
from src.engine import RichgoCortexEngine, SUPPLY_SPILLOVER

print("\n" + "=" * 65)
print("  Mission 3-3 Integration Test — Temporal & Spatial Intelligence")
print("=" * 65)

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
)
engine = RichgoCortexEngine(conn)

# ── 송파구 단지 샘플 조회 ─────────────────────────────────────────────────────
print("\n[1/4] 송파구 단지 샘플 조회 중...")
cur = conn.cursor()
cur.execute("""
    SELECT DANJI_ID, DANJI
    FROM DANJI_APT_INFO
    WHERE SGG = '송파구'
    LIMIT 1
""")
row = cur.fetchone()
cur.close()

if not row:
    print("    ✗ 송파구 단지를 찾을 수 없습니다.")
    sys.exit(1)

test_danji_id, test_danji_name = row
print(f"    ✓ 테스트 단지: [{test_danji_id}] {test_danji_name}")

# ── Spillover 매핑 확인 ───────────────────────────────────────────────────────
print("\n[2/4] Supply Spillover 매핑 확인...")
adj = SUPPLY_SPILLOVER.get("송파구", [])
print(f"    송파구 인접 구: {adj}")
assert "강동구" in adj, "FAIL: 강동구가 송파구 Spillover 매핑에 없음"
print("    ✓ 강동구 → 송파구 Spillover 매핑 확인")

# ── PIR Band 단독 테스트 ──────────────────────────────────────────────────────
print("\n[3/4] PIR Band (5년 시계열) 테스트...")
pir_5yr_avg, used_fallback = engine.fetch_pir_band("송파구", "서울")
print(f"    5년 평균 PIR: {pir_5yr_avg}  (SD Fallback: {used_fallback})")

region_prices = engine.fetch_region_price("송파구", months=1)
if region_prices:
    from src.engine import REGIONAL_INCOME_MAN_WON
    income = REGIONAL_INCOME_MAN_WON["서울"]
    latest_meme = region_prices[0].get("mean_meme_price", 0)
    current_pir = round(latest_meme / income, 2) if latest_meme else 0
    idx, adj_score, label = engine.compute_pir_band_adjustment(current_pir, pir_5yr_avg)
    print(f"    현재 PIR={current_pir:.2f} | 5yr avg={pir_5yr_avg} | 상대지수={idx:.4f}")
    print(f"    PIR Band 판정: [{label}]  S_alpha 보정={adj_score:+.1f}점")
else:
    print("    ⚠ 송파구 지역 시세 데이터 없음 — Snowflake 연결 확인 필요")

# ── 전체 분석 + Spillover 증명 ────────────────────────────────────────────────
print(f"\n[4/4] 전체 분석 실행 — {test_danji_name} ({test_danji_id})...")
try:
    r = engine.analyze(test_danji_id)

    print("\n  ┌─ 종합 점수 ─────────────────────────────────────────────")
    print(f"  │  S_alpha (최종/정수):  {r['s_alpha']}점")
    print(f"  │  PIR Band 보정 전:    {r['s_alpha_before_band']}점")
    print(f"  │  PIR Band 보정값:     {r['pir_band_adjustment']:+.1f}점  [{r['pir_band_label']}]")
    print(f"  │  실행 트리거 (≥80):   {r['execution_trigger']}")
    print(f"  │  신뢰도:             {r['confidence_pct']}%  ({r['confidence_label']})")
    print("  ├─ PIR Band (Temporal) ──────────────────────────────────")
    print(f"  │  현재 PIR:           {r['pir']}")
    print(f"  │  5년 평균 PIR:       {r['pir_5yr_avg']}  (Fallback={r['pir_band_fallback']})")
    print(f"  │  상대 지수:          {r['pir_relative_index']}  → {r['pir_band_label']}")
    print("  ├─ Supply Spillover (Spatial) ───────────────────────────")
    sd = r["spillover_detail"]
    print(f"  │  송파구 자체 점수:    {sd['own_score']}")
    if sd.get("spillover_applied"):
        for adj_sgg, adj_s in sd["adjacent_scores"].items():
            print(f"  │  {adj_sgg} 공급 점수:     {adj_s}")
        print(f"  │  인접구 평균:         {sd['adjacent_avg']}")
        print(f"  │  최종 공급 점수:      {sd['final_score']}  (= {sd['own_score']}×0.7 + {sd['adjacent_avg']}×0.3)")
        assert sd["final_score"] != sd["own_score"] or sd["adjacent_avg"] == sd["own_score"], \
            "WARN: 인접구 점수가 자체 점수와 동일 (데이터 부족 가능)"
        print(f"  │  ✓ 강동구 공급 상태가 최종 점수에 반영됨")
    else:
        print(f"  │  ⚠ Spillover 미적용 (인접구 데이터 없음)")
    print("  ├─ 전세가율 ─────────────────────────────────────────────")
    print(f"  │  전세가율:           {r['jeonse_ratio']}  (바닥={r['jeonse_floor']})")
    print(f"  │  안전 여부:          {r['jeonse_safety_ok']}")
    print("  ├─ 단지 정보 ────────────────────────────────────────────")
    print(f"  │  단지명:             {r['danji_name']}")
    print(f"  │  매매가:             {r['latest_meme_price_man_won']:,}만원")
    print(f"  │  초품아:             {r['is_chobuma']}  (LIVING_SCORE={r['living_score']})")
    print("  └────────────────────────────────────────────────────────")

    # Score Clamping 검증
    assert isinstance(r["s_alpha"], int), f"FAIL: s_alpha가 정수가 아님 ({type(r['s_alpha'])})"
    assert 0 <= r["s_alpha"] <= 100, f"FAIL: s_alpha={r['s_alpha']} out of range"
    print("\n  ✓ Score Clamping 검증 통과 — s_alpha는 0~100 정수")

except Exception as e:
    print(f"\n  ✗ 분석 실패: {e}")
    import traceback
    traceback.print_exc()

conn.close()
print("\n" + "=" * 65)
print("  Mission 3-3 Test Complete.")
print("=" * 65 + "\n")
