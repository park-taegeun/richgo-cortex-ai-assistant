import os
import sys
import snowflake.connector
from dotenv import load_dotenv

from src.core.engine import RichgoCortexEngine

def main():
    load_dotenv()

    print("=== [debug_test_run] Data Pipeline Execution ===")
    target_id = "a7qzYub"  # 예제 ID
    
    try:
        print(f"Connecting to Snowflake...")
        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "RICHGO_KR"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "HACKATHON_2026"),
        )
        print("Connected! Initializing CortexEngine...")
        engine = RichgoCortexEngine(conn)
        
        print(f"Running analyze() for ID: {target_id}")
        result = engine.analyze(target_id)
        
        print("\n=== Validation Results ===")
        print(f"[1] S_alpha 종합 점수: {result.get('s_alpha')}")
        print(f"[2] PIR Band: {result.get('pir_band_label')} (adj: {result.get('pir_band_adjustment')})")
        print(f"[3] Supply Score (Final): {result.get('supply_score_final')}")
        
    except Exception as e:
        print(f"\n[Error/Exception Detected]: {e}")
        print("Checking .env mapped variables vs snowflake_client needs...")
        sys.exit(1)

if __name__ == "__main__":
    main()
