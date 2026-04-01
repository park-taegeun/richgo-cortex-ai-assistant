"""
Richgo-Cortex AI Assistant — Snowflake Connection & Engine Test
Usage: python scripts/test_connection.py
"""
import os, sys, time
from dotenv import load_dotenv
load_dotenv()

REQUIRED = ["SNOWFLAKE_ACCOUNT","SNOWFLAKE_USER","SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_WAREHOUSE","SNOWFLAKE_DATABASE","SNOWFLAKE_SCHEMA"]
missing = [v for v in REQUIRED if not os.getenv(v)]
if missing:
    print(f"[ERROR] Missing env vars: {missing}")
    sys.exit(1)

import snowflake.connector

print("\n[1/3] Connecting to Snowflake...")
start = time.time()
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"), user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"), role=os.getenv("SNOWFLAKE_ROLE","ACCOUNTADMIN"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"), database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
)
print(f"    Connected in {time.time()-start:.2f}s")
cur = conn.cursor()

print("\n[2/3] Schema tables:")
cur.execute("SELECT table_name, row_count, bytes FROM information_schema.tables WHERE table_schema='HACKATHON_2026' ORDER BY table_name")
print(f"    {'TABLE':<50} {'ROWS':>10} {'MB':>8}")
for n, r, b in cur.fetchall():
    print(f"    {n:<50} {r or 0:>10,} {round((b or 0)/1024/1024,2):>8.2f}")

print("\n[3/3] RichgoCortexEngine.analyze('a7qzYub')...")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.engine import RichgoCortexEngine
engine = RichgoCortexEngine(conn)
result = engine.analyze('a7qzYub')
print(f"    {result['danji_name']} ({result['sgg']})")
print(f"    S_alpha={result['s_alpha']} | Confidence={result['confidence_pct']}% ({result['confidence_label']})")
print(f"    전세가율={result['jeonse_ratio']} (OK={result['jeonse_safety_ok']}) | PIR={result['pir']}")
print(f"    Supply={result['supply_score']} | Sentiment={result['sentiment_score']}")
print(f"    Execution Trigger: {result['execution_trigger']}")

cur.close(); conn.close()
print("\n" + "="*60 + "\n  Complete.\n" + "="*60)
