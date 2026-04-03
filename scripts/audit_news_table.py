"""
scripts/audit_news_table.py
뉴스 테이블 실제 위치 전수 조사 (Metadata Audit)

Usage:
    python scripts/audit_news_table.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import snowflake.connector

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    database=os.getenv("SNOWFLAKE_DATABASE", "RICHGO_KR"),
    schema=os.getenv("SNOWFLAKE_SCHEMA", "HACKATHON_2026"),
)
cur = conn.cursor()

print("=" * 65)
print("  Metadata Audit — 뉴스 테이블 위치 전수 조사")
print("=" * 65)

# ── Step 1: RICHGO_KR 내 전체 스키마 목록 ─────────────────────────────────────
print("\n[1/4] RICHGO_KR 내 전체 스키마 목록...")
try:
    cur.execute("SHOW SCHEMAS IN DATABASE RICHGO_KR")
    schemas = [r[1] for r in cur.fetchall()]
    for s in schemas:
        print(f"  • {s}")
except Exception as e:
    print(f"  ✗ {e}")
    schemas = []

# ── Step 2: 각 스키마에서 뉴스/RSS/NEWS/SENTIMENT 관련 테이블 탐색 ─────────────
print("\n[2/4] 각 스키마에서 뉴스 관련 테이블 탐색...")
news_candidates = []
for schema in schemas:
    try:
        cur.execute(f"""
            SELECT table_schema, table_name, row_count
            FROM RICHGO_KR.information_schema.tables
            WHERE table_schema = '{schema}'
              AND (
                LOWER(table_name) LIKE '%news%'
                OR LOWER(table_name) LIKE '%rss%'
                OR LOWER(table_name) LIKE '%sentiment%'
                OR LOWER(table_name) LIKE '%feed%'
                OR LOWER(table_name) LIKE '%article%'
                OR LOWER(table_name) LIKE '%cortex%'
              )
            ORDER BY table_name
        """)
        rows = cur.fetchall()
        for schema_name, table_name, row_count in rows:
            full_name = f"RICHGO_KR.{schema_name}.{table_name}"
            print(f"  ✅ FOUND: {full_name}  (rows: {row_count})")
            news_candidates.append((schema_name, table_name, row_count))
    except Exception as e:
        print(f"  ⚠ {schema}: {e}")

if not news_candidates:
    print("  ❌ 뉴스 관련 테이블 없음. 모든 테이블 목록으로 확장 조사...")

# ── Step 3: STAGING 스키마 전체 테이블 목록 (있는 경우) ─────────────────────────
print("\n[3/4] STAGING 스키마 전체 테이블 목록...")
try:
    cur.execute("""
        SELECT table_schema, table_name, row_count
        FROM RICHGO_KR.information_schema.tables
        WHERE table_schema = 'STAGING'
        ORDER BY table_name
    """)
    rows = cur.fetchall()
    if rows:
        for schema_name, table_name, row_count in rows:
            print(f"  • RICHGO_KR.{schema_name}.{table_name}  (rows: {row_count})")
    else:
        print("  ⚠ STAGING 스키마 없거나 테이블 없음")
except Exception as e:
    print(f"  ✗ {e}")

# ── Step 4: HACKATHON_2026 전체 테이블 목록 ───────────────────────────────────
print("\n[4/4] HACKATHON_2026 전체 테이블 목록...")
try:
    cur.execute("""
        SELECT table_name, row_count
        FROM RICHGO_KR.information_schema.tables
        WHERE table_schema = 'HACKATHON_2026'
        ORDER BY table_name
    """)
    rows = cur.fetchall()
    if rows:
        for table_name, row_count in rows:
            marker = " ← 🔍 뉴스 후보" if any(k in table_name.lower() for k in ["news","rss","sentiment","feed","cortex","article"]) else ""
            print(f"  • {table_name:<55} rows: {row_count}{marker}")
    else:
        print("  ⚠ 테이블 없음")
except Exception as e:
    print(f"  ✗ {e}")

cur.close()
conn.close()
print("\n" + "=" * 65)
if news_candidates:
    print(f"  ✅ 뉴스 테이블 발견: {len(news_candidates)}개")
    for s, t, r in news_candidates:
        print(f"     → RICHGO_KR.{s}.{t}  ({r} rows)")
else:
    print("  ❌ 뉴스/RSS 테이블 미발견 — CORTEX_ANALYTICS 우회로 필요")
print("=" * 65 + "\n")
