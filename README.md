# Richgo-Cortex AI Assistant

> 리치고 데이터 × Snowflake Cortex AI — 부동산 상급지 이동 전략 비서

## Overview

모델 C+ 기반의 5대 지표(전세가율, PIR, 공급점수, 뉴스감성, 출퇴근)를 Snowflake Cortex AI로 분석하여
단지별 상급지 이동 전략 점수(S_alpha)를 산출하는 AI 비서 시스템입니다.

## Quick Start

```bash
cp .env.example .env  # fill in Snowflake credentials
pip install snowflake-connector-python pandas python-dotenv streamlit
python scripts/test_connection.py
```

## Model C+ Key Constants

| Parameter | Value |
|---|---|
| 전세가율 안전 바닥 | 70% |
| PIR 저평가 임계값 | 10년 평균 × 85% |
| 공급 기회선 | R < 0.8 (100점) |
| 공급 위험선 | R > 1.4 (지수감점) |
| 즉시 실행 임계 | 80점 |
| 뉴스 TTL | 168시간 |

## Schema (RICHGO_KR.HACKATHON_2026)

| Table | Rows | Key Columns |
|---|---|---|
| DANJI_APT_INFO | 3,331 | DANJI_ID, LIVING_SCORE, CONSTRUCTOR_RANK |
| DANJI_APT_RICHGO_MARKET_PRICE_M_H | 466,555 | MEAN_MEME_PRICE, MEAN_JEONSE_PRICE |
| REGION_APT_RICHGO_MARKET_PRICE_M_H | 36,225 | TOTAL_HOUSEHOLDS (공급지표) |
| REGION_POPULATION_MOVEMENT | 150,705 | POPULATION (순이동) |

## Cortex AI Pattern (Confirmed)

```sql
-- CORRECT
SELECT SNOWFLAKE.CORTEX.SENTIMENT('뉴스 텍스트') AS s;

-- AVOID: TRY_CAST + AI_SENTIMENT → __round__ error risk
```

## Security

- `.env` is gitignored — never committed
- All credentials via environment variables only
