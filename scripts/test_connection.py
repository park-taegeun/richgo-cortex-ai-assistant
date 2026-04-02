"""
Richgo-Cortex AI Assistant — Snowflake Connection Test Script
Mission 1: 연동 테스트 및 RICHGO_KR.HACKATHON_2026 스키마 검증

Usage:
    1. cp .env.example .env  (and fill in your credentials)
    2. python scripts/test_connection.py
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# ── 1. 환경변수 검증 ──────────────────────────────────────────────────────────
REQUIRED_ENV_VARS = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
]

missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
if missing:
    print(f"[ERROR] Missing environment variables: {missing}")
    print("  → Copy .env.example to .env and fill in your Snowflake credentials.")
    sys.exit(1)

try:
    import snowflake.connector
except ImportError:
    print("[ERROR] snowflake-connector-python not installed.")
    print("  → Run: pip install snowflake-connector-python")
    sys.exit(1)


# ── 2. 연결 ──────────────────────────────────────────────────────────────────
print("\n[1/4] Connecting to Snowflake...")
start = time.time()

try:
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )
    elapsed = time.time() - start
    print(f"    ✓ Connected in {elapsed:.2f}s")
except Exception as e:
    print(f"    ✗ Connection failed: {e}")
    sys.exit(1)

cur = conn.cursor()


# ── 3. HACKATHON_2026 스키마 테이블 목록 조회 ─────────────────────────────────
print("\n[2/4] Listing tables in RICHGO_KR.HACKATHON_2026...")
try:
    cur.execute("""
        SELECT table_name, row_count, bytes
        FROM information_schema.tables
        WHERE table_schema = 'HACKATHON_2026'
        ORDER BY table_name
    """)
    rows = cur.fetchall()
    if rows:
        print(f"\n    {'TABLE NAME':<50} {'ROWS':>12} {'SIZE(MB)':>10}")
        print("    " + "-" * 74)
        for name, row_count, size_bytes in rows:
            mb = round((size_bytes or 0) / 1024 / 1024, 2)
            print(f"    {name:<50} {str(row_count or 0):>12} {mb:>10.2f}")
    else:
        print("    ⚠ No tables found. Verify schema name and permissions.")
except Exception as e:
    print(f"    ✗ Query failed: {e}")


# ── 4. 모델 C+ 핵심 컬럼 존재 여부 검증 ──────────────────────────────────────
print("\n[3/4] Validating Model C+ required columns...")

# 명세서에서 요구하는 핵심 컬럼 목록 (테이블명은 실제 스키마 확인 후 수정)
REQUIRED_COLUMNS = {
    # table_name (예상): [required columns]
    # 실제 테이블명은 위 조회 결과로 확인 후 채워야 함
    # 아래는 명세서 기반 예상 매핑
    "APARTMENT": ["complex_id", "complex_name", "sigungu_code", "latitude", "longitude"],
    "PRICE": ["complex_id", "trade_price", "jeonse_ratio", "ai_forecast_price", "pir"],
    "SUPPLY": ["sigungu_code", "supply_qty_3yr", "population"],
}

try:
    cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'HACKATHON_2026'
        ORDER BY table_name, ordinal_position
    """)
    all_cols = cur.fetchall()

    actual = {}
    for table, col in all_cols:
        actual.setdefault(table, []).append(col.lower())

    for expected_table, expected_cols in REQUIRED_COLUMNS.items():
        # 유사한 실제 테이블명 찾기 (부분 매칭)
        matched_tables = [t for t in actual if expected_table.lower() in t.lower()]
        if matched_tables:
            real_table = matched_tables[0]
            missing_cols = [c for c in expected_cols if c.lower() not in actual[real_table]]
            if missing_cols:
                print(f"    ⚠ [{real_table}] missing columns: {missing_cols}")
                print(f"      → Fallback logic will be required for Model C+")
            else:
                print(f"    ✓ [{real_table}] all required columns present")
        else:
            print(f"    ⚠ No table matching '{expected_table}' found — manual mapping needed")

except Exception as e:
    print(f"    ✗ Column validation failed: {e}")


# ── 5. Cortex AI 함수 가용성 확인 ─────────────────────────────────────────────
print("\n[4/4] Checking Snowflake Cortex AI availability...")
try:
    cur.execute("""
        SELECT SNOWFLAKE.CORTEX.AI_SENTIMENT('금리 인하로 부동산 시장이 활성화될 전망입니다.')
        AS sentiment_test
    """)
    result = cur.fetchone()
    score = result[0]
    scaled = round(score * 5, 2)
    print(f"    ✓ AI_SENTIMENT available")
    print(f"      Test sentence sentiment: raw={score:.4f}, scaled(×5)={scaled}")

    if scaled > 0:
        print(f"      → Positive sentiment detected ✓ (expected for '금리 인하' news)")
    else:
        print(f"      → ⚠ Unexpected negative score — Korean NLP may need ensemble fallback")

except Exception as e:
    print(f"    ✗ Cortex AI_SENTIMENT unavailable: {e}")
    print("      → Rule-based keyword scoring fallback REQUIRED")


# ── 완료 ─────────────────────────────────────────────────────────────────────
cur.close()
conn.close()

print("\n" + "=" * 60)
print("  Connection test complete.")
print("  Next step: Review table names above and update")
print("  src/config.py with actual table mapping.")
print("=" * 60 + "\n")
