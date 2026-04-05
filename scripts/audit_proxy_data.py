"""
scripts/audit_proxy_data.py
Proxy Sentiment 데이터 파이프라인 전수 조사 (Schema + Data Audit)

목적:
  - REGION_POPULATION_MOVEMENT 컬럼 구조 및 실제 값 범위 확인
  - DANJI_APT_RICHGO_MARKET_PRICE_M_H 모멘텀 쿼리 결과 확인
  - 프록시 점수 고착 (+0.5pt) 원인 규명

Usage:
    python scripts/audit_proxy_data.py
    python scripts/audit_proxy_data.py --danji-ids a7qzYub bXkMnPq
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import snowflake.connector

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE", "RICHGO_KR"),
    schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    role=os.getenv("SNOWFLAKE_ROLE"),
)
cur = conn.cursor()

SEP = "─" * 60

# ── 1. REGION_POPULATION_MOVEMENT 테이블 실존 + 컬럼 전수 조사 ────────────────
print(f"\n{SEP}")
print("【1】 REGION_POPULATION_MOVEMENT 컬럼 목록")
print(SEP)
try:
    cur.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'REGION_POPULATION_MOVEMENT'
        ORDER BY ORDINAL_POSITION
    """)
    cols = cur.fetchall()
    if cols:
        for c in cols:
            print(f"  {c[0]:35s} {c[1]:20s} nullable={c[2]}")
    else:
        print("  ⚠️  테이블을 찾을 수 없습니다. 유사 테이블을 검색합니다...")
        cur.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME ILIKE '%POPULATION%'
               OR TABLE_NAME ILIKE '%MIGRATION%'
               OR TABLE_NAME ILIKE '%MOVEMENT%'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        for r in cur.fetchall():
            print(f"  → {r[0]}.{r[1]}")
except Exception as e:
    print(f"  ❌ 오류: {e}")

# ── 2. REGION_POPULATION_MOVEMENT 실제 데이터 샘플 (순이동 기준) ──────────────
print(f"\n{SEP}")
print("【2】 REGION_POPULATION_MOVEMENT 샘플 데이터 (순이동, 최근 6개월)")
print(SEP)
TEST_SGGG = ["도봉구", "강남구", "노원구", "송파구"]
for sgg in TEST_SGGG:
    try:
        cur.execute("""
            SELECT YYYYMMDD, POPULATION, MOVEMENT_TYPE, REGION_LEVEL
            FROM REGION_POPULATION_MOVEMENT
            WHERE SGG = %s AND MOVEMENT_TYPE = '순이동' AND REGION_LEVEL = 'sgg'
            ORDER BY YYYYMMDD DESC
            LIMIT 6
        """, (sgg,))
        rows = cur.fetchall()
        if rows:
            vals = [r[1] for r in rows if r[1] is not None]
            print(f"  {sgg}: {[f'{v:+.0f}' for v in vals]}")
            print(f"    → avg={sum(vals)/len(vals):+.1f} | min={min(vals):+.0f} | max={max(vals):+.0f}")
            print(f"    → 구간 판정: {'> 50 → pop_adj=+0.5 ⚠️ 고착 의심' if sum(vals)/len(vals) > 50 else '정상 범위'}")
        else:
            print(f"  {sgg}: 데이터 없음 (0.0 반환)")
    except Exception as e:
        print(f"  {sgg}: ❌ {e}")

# ── 3. MOVEMENT_TYPE 종류 전수 조사 ──────────────────────────────────────────
print(f"\n{SEP}")
print("【3】 MOVEMENT_TYPE 고유값 목록")
print(SEP)
try:
    cur.execute("""
        SELECT DISTINCT MOVEMENT_TYPE, COUNT(*) AS cnt
        FROM REGION_POPULATION_MOVEMENT
        GROUP BY MOVEMENT_TYPE
        ORDER BY cnt DESC
    """)
    for r in cur.fetchall():
        print(f"  '{r[0]}' : {r[1]:,}건")
except Exception as e:
    print(f"  ❌ {e}")

# ── 4. POPULATION 컬럼 전체 값 범위 (순이동 기준) ─────────────────────────────
print(f"\n{SEP}")
print("【4】 POPULATION 컬럼 전체 통계 (MOVEMENT_TYPE='순이동')")
print(SEP)
try:
    cur.execute("""
        SELECT
            COUNT(*)            AS row_count,
            MIN(POPULATION)     AS min_val,
            MAX(POPULATION)     AS max_val,
            AVG(POPULATION)     AS avg_val,
            STDDEV(POPULATION)  AS std_val
        FROM REGION_POPULATION_MOVEMENT
        WHERE MOVEMENT_TYPE = '순이동' AND REGION_LEVEL = 'sgg'
    """)
    row = cur.fetchone()
    if row:
        print(f"  건수: {row[0]:,}")
        print(f"  MIN : {row[1]:+.1f}")
        print(f"  MAX : {row[2]:+.1f}")
        print(f"  AVG : {row[3]:+.1f}")
        print(f"  STD : {row[4]:.1f}")
        if row[2] > 10000:
            print("  ⚠️  MAX > 10,000 → 절대 인구수 가능성 (단위: 명)")
        elif row[2] > 500:
            print("  ⚠️  MAX > 500 → 정규화 기준 검토 필요 (50명 임계값이 너무 낮음)")
        else:
            print("  ✅  값 범위 정상 (순이동 건수로 추정)")
except Exception as e:
    print(f"  ❌ {e}")

# ── 5. 가격 모멘텀 실측 (다중 단지) ─────────────────────────────────────────
print(f"\n{SEP}")
print("【5】 가격 모멘텀 실측 (fetch_price_momentum 재현)")
print(SEP)
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--danji-ids", nargs="*", default=[])
args, _ = parser.parse_known_args()
test_ids = args.danji_ids or []

if test_ids:
    for did in test_ids:
        try:
            cur.execute("""
                SELECT
                    AVG(CASE WHEN idx <= 3 THEN MEAN_MEME_PRICE END) AS recent_avg,
                    AVG(CASE WHEN idx > 3 AND idx <= 6 THEN MEAN_MEME_PRICE END) AS prior_avg
                FROM (
                    SELECT MEAN_MEME_PRICE,
                           ROW_NUMBER() OVER (ORDER BY YYYYMMDD DESC) AS idx
                    FROM DANJI_APT_RICHGO_MARKET_PRICE_M_H
                    WHERE DANJI_ID = %s AND MEAN_MEME_PRICE IS NOT NULL
                )
            """, (did,))
            row = cur.fetchone()
            if row and row[0] and row[1]:
                pct = (row[0] - row[1]) / row[1] * 100
                print(f"  {did}: recent={row[0]:.0f} | prior={row[1]:.0f} | momentum={pct:+.2f}%")
                if abs(pct) < 2.0:
                    print(f"    → ±2% 이내 → base=0.0 (중립 구간)")
            else:
                print(f"  {did}: 데이터 없음 → momentum=0.0")
        except Exception as e:
            print(f"  {did}: ❌ {e}")
else:
    print("  (--danji-ids 인수를 전달하면 단지별 모멘텀을 확인할 수 있습니다)")
    print("  예: python scripts/audit_proxy_data.py --danji-ids a7qzYub bXkMnPq")

# ── 6. 진단 요약 ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("【진단 요약】 +0.5pt 고착 가설")
print(SEP)
print("  가설 A: population_net > 50 (절대 인구수/누적 유입이 임계값 초과)")
print("           → base=0.0 (momentum ±2% 이내) + pop_adj=+0.5 = 고착")
print("  가설 B: fetch_population_net 쿼리 실패 → 0.0 반환")
print("           → base=0.0 + pop_adj=0.0 = 0.0 (이 경우 +0.5 아님, 제외)")
print("  → 위 【2】【4】 데이터로 가설 A 검증 필요")
print()
print("  처방: compute_proxy_score 산식을 연속형으로 교체")
print("  Score = (momentum_pct * 0.5 * 0.7) + (pop_net / POP_SCALE * 1.5 * 0.3)")

cur.close()
conn.close()
print(f"\n{SEP}")
print("감사 완료.")
