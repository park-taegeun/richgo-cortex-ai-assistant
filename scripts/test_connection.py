"""
Richgo-Cortex AI Assistant — Snowflake Connection & Engine Integration Test

Usage:
    1. cp .env.example .env  # fill in credentials
    2. python scripts/test_connection.py
"""
import os, sys, time
from dotenv import load_dotenv
load_dotenv()

REQUIRED = [
    "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA",
]
missing = [v for v in REQUIRED if not os.getenv(v)]
if missing:
    print(f"[ERROR] Missing env vars: {missing}")
    print("  -> Copy .env.example to .env and fill in Snowflake credentials.")
    sys.exit(1)

try:
    import snowflake.connector
except ImportError:
    print("[ERROR] snowflake-connector-python not installed.")
    print("  -> Run: pip install snowflake-connector-python")
    sys.exit(1)

print("\n[1/4] Connecting to Snowflake...")
start = time.time()
try:
    conn = snowflake.connector.connect(
        account   = os.getenv("SNOWFLAKE_ACCOUNT"),
        user      = os.getenv("SNOWFLAKE_USER"),
        password  = os.getenv("SNOWFLAKE_PASSWORD"),
        role      = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE"),
        database  = os.getenv("SNOWFLAKE_DATABASE"),
        schema    = os.getenv("SNOWFLAKE_SCHEMA"),
    )
    print(f"    Connected in {time.time()-start:.2f}s")
except Exception as e:
    print(f"    Connection failed: {e}")
    sys.exit(1)

cur = conn.cursor()

print("\n[2/4] Schema tables (HACKATHON_2026):")
try:
    cur.execute("""
        SELECT table_name, row_count, bytes
        FROM information_schema.tables
        WHERE table_schema = 'HACKATHON_2026'
        ORDER BY table_name
    """)
    print(f"    {'TABLE':<52} {'ROWS':>10} {'MB':>8}")
    print("    " + "-" * 72)
    for name, row_count, size_bytes in cur.fetchall():
        mb = round((size_bytes or 0) / 1024 / 1024, 2)
        print(f"    {name:<52} {(row_count or 0):>10,} {mb:>8.2f}")
except Exception as e:
    print(f"    Query failed: {e}")

print("\n[3/4] Cortex AI availability:")
try:
    cur.execute("""
        SELECT SNOWFLAKE.CORTEX.SENTIMENT('금리 인하로 부동산 시장이 활성화될 전망입니다.') AS s
    """)
    raw = float(cur.fetchone()[0])
    print(f"    CORTEX.SENTIMENT: raw={raw:.4f}, scaled(x5)={round(raw*5, 4)}")
except Exception as e:
    print(f"    Cortex unavailable: {e}")

print("\n[4/4] RichgoCortexEngine quick test (a7qzYub):")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from src.engine import RichgoCortexEngine
    engine = RichgoCortexEngine(conn)
    r = engine.analyze('a7qzYub')
    print(f"    {r['danji_name']} ({r['sgg']})")
    print(f"    S_alpha={r['s_alpha']} | {r['confidence_pct']}% ({r['confidence_label']})")
    print(f"    전세가율={r['jeonse_ratio']} | 지역바닥={r['jeonse_floor']} | OK={r['jeonse_safety_ok']}")
    print(f"    PIR={r['pir']} | Supply={r['supply_score']} | Trigger={r['execution_trigger']}")
except Exception as e:
    print(f"    Engine test failed: {e}")

cur.close()
conn.close()
print("\n" + "=" * 60 + "\n  Complete.\n" + "=" * 60 + "\n")
