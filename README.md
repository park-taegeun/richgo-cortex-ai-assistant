# 🏙️ Richgo-Cortex AI Assistant — Strategic Command Center

> **Snowflake Hackathon 2026** · Model C+ · Plan Freeze 2026-04-01

Richgo 46만 행 부동산 시계열 데이터 × Snowflake Cortex AI를 결합한  
**부동산 상급지 이동(Moving Up) 타이밍 추천 엔진** + 하이엔드 관제탑 대시보드.

---

## 🚀 대시보드 실행 가이드

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 실제 Snowflake 자격증명 입력
```

### 2. 의존성 설치

```bash
pip install snowflake-connector-python pandas python-dotenv streamlit plotly slack_sdk numpy
```

### 3. 연결 테스트 (선택)

```bash
python scripts/test_connection.py
```

### 4. 관제탑 가동

```bash
streamlit run app.py
```

> Snowflake 연결 없이도 **Demo 모드**로 대시보드가 자동 실행됩니다.

---

## 🗂 모듈 구조도

```
snowflake-hackathon/
│
├── app.py                          # 🏙️ 관제탑 대시보드 (Streamlit)
│
├── src/
│   ├── core/
│   │   ├── engine.py               # 🧠 RichgoCortexEngine (오케스트레이터)
│   │   └── sentiment.py            # 💬 SentimentAnalyzer (Cortex AI 감성)
│   │
│   ├── analytics/
│   │   ├── temporal.py             # ⏱  PIRBandAnalyzer (60개월 시계열)
│   │   └── spatial.py              # 🗺  SupplySpilloverAnalyzer (인접구 간섭)
│   │
│   ├── utils/
│   │   └── snowflake_client.py     # 🔌 SnowflakeClient (공통 쿼리 유틸)
│   │
│   ├── mapping.json                # 📋 스키마 메타데이터 & 보정 상수
│   └── __init__.py
│
├── scripts/
│   ├── test_connection.py          # Snowflake 연결 검증
│   └── test_mission33.py           # 엔진 라이브 테스트
│
├── .env.example                    # 환경 변수 템플릿
├── .gitignore
└── CLAUDE.md                       # AI 실행 프로토콜
```

---

## 🧠 Model C+ 알고리즘 요약

### 핵심 공식

```
S_alpha = W_supply×S_supply + W_pir×S_pir + W_jeonse×S_jeonse
        + W_news×S_news + W_commute×S_commute
        + PIR_Band_Adjustment (±15pt / -10pt)
```

| 가중치     | 값   | 모듈                    |
|-----------|------|------------------------|
| W_supply  | 0.30 | `spatial.py`           |
| W_pir     | 0.25 | `engine.py`            |
| W_jeonse  | 0.20 | `engine.py`            |
| W_news    | 0.15 | `sentiment.py`         |
| W_commute | 0.10 | `engine.py`            |

### Alpha-Trigger 발동 조건

```python
if (target_score - current_score) >= 20 and target_score >= 80:
    # st.balloons() + 골든타임 선포
```

### 적응형 안전 바닥 (Adaptive Safety Floor)

| 지역          | 전세가율 바닥 | 근거                              |
|--------------|------------|----------------------------------|
| 강남/용산/성동  | **35%**   | avg=0.39, P20=0.26 (460k행 실측) |
| 서초구         | **38%**   | avg=0.43, P20=0.31               |
| 송파구         | **41%**   | avg=0.44, P20=0.36               |
| 마포/종로      | **48%**   | avg=0.51~0.59                    |
| 서울 기타      | **55%**   | 서울 전체 avg=0.58                |
| 경기 / 기본값  | **65%**   | —                                |

### PIR Band (시공간 지능)

```
PIR 상대 지수 = 현재 PIR / 60개월 평균 PIR

Index < 0.85  → 역대급 저평가  → +15pt
Index > 1.15  → 고점 경고     → −10pt
그 외          → 적정 구간    →  ±0pt
```

### Supply Spillover

```
최종 공급점수 = 본구 점수 × 0.70 + 인접구 평균 × 0.30

강남↔서초/송파 | 송파↔강동 | 마포↔용산 | 성동↔광진 등 13쌍
```

---

## 📊 활용 데이터베이스 (RICHGO_KR.HACKATHON_2026)

| 테이블명                                        | 행 수    | 용도                      |
|------------------------------------------------|---------|--------------------------|
| `DANJI_APT_INFO`                               | 3,331   | 단지 메타데이터            |
| `DANJI_APT_RICHGO_MARKET_PRICE_M_H`            | 466,555 | 단지별 월간 시세           |
| `REGION_APT_RICHGO_MARKET_PRICE_M_H`           | 36,225  | 지역별 시세 & 공급 지표    |
| `REGION_POPULATION_MOVEMENT`                   | 150,705 | 순이동 인구                |
| `APT_DANJI_AND_TRANSPORTATION_TRAIN_DISTANCE`  | 182,500 | 지하철 거리               |

---

## 🧪 Cortex AI 확정 패턴

```sql
-- ✅ CORRECT (테스트 완료 2026-04-02)
SELECT SNOWFLAKE.CORTEX.SENTIMENT('금리 인하 호재') AS s;
-- 결과: 0.09375 (raw) → × 5.0 in Python

-- ❌ AVOID: TRY_CAST + AI_SENTIMENT → __round__ 에러 발생
```

---

## 🎯 성공 지표

| 지표                   | 목표값    |
|-----------------------|---------|
| Richgo AI MAPE        | ≤ 20.2% |
| E2E 응답 시간          | ≤ 3초   |
| Groundedness Score    | ≥ 0.9   |

---

## 🔐 보안

- `.env` 파일은 `.gitignore`에 등록되어 **절대 커밋되지 않습니다.**
- 모든 자격증명은 환경 변수로만 관리합니다.
- `.env.example`을 복사하여 사용하세요.

---

*Richgo-Cortex AI · Model C+ · Snowflake Hackathon 2026*
