# Richgo-Cortex AI Assistant — Project Instructions (Frozen: 2026-04-01)

## 모델 C+ 확정 상수 (Frozen Constants)

이 파일은 사령관(Gemini 3)이 승인한 모델 C+ 설계 명세서의 핵심 상수 기준점입니다.
코드 구현 시 반드시 아래 값을 사용하고, 변경 시 사령관 승인 필요.

### Supply Score 임계값
| 파라미터 | 값 | 변수명 |
|---|---|---|
| 적정 수요 비율 | 0.005 (0.5%) | `DEMAND_RATIO` |
| 공급 기회선 (만점) | R < 0.8 | `SUPPLY_SAFE_UPPER` |
| 공급 선형감점 구간 | 0.8 ≤ R ≤ 1.2 | — |
| 공급 급격감점 구간 | 1.2 < R ≤ 1.4 | — |
| 공급 위험선 (지수감점) | R > 1.4 | `SUPPLY_DANGER` |

### 저평가 기준값
| 파라미터 | 값 | 변수명 |
|---|---|---|
| 전세가율 안전 바닥 | 70% (0.70) | `JEONSE_SAFETY_FLOOR` |
| PIR 저평가 임계값 | 10년 평균 × 0.85 | `PIR_UNDERVALUE_RATIO` |

### 하이브리드 점수 기준
| 파라미터 | 값 | 변수명 |
|---|---|---|
| 즉시 실행 임계 | 80점 | `MIGRATION_SCORE_EXECUTE` |
| 초품아 가중치 | ×1.5 | `EDUCATION_WEIGHT` |

### 뉴스 감성 분석
| 파라미터 | 값 | 변수명 |
|---|---|---|
| 감성 점수 스케일 | −5 ~ +5 | — |
| 뉴스 TTL | 168시간 (7일) | `NEWS_TTL_HOURS` |
| 최소 표본 수 | 3건 | `NEWS_MIN_SAMPLE` |
| 일관성 임계값 | 0.7 | `SENTIMENT_AGREEMENT_THRESHOLD` |

### 카테고리 가중치 (W_cat)
| 범주 | 기본 점수 | W_cat |
|---|---|---|
| 통화 정책 (Monetary) | +3 | 1.5 |
| 대출 규제 (Regulation) | −4 | 1.5 |
| 인프라 호재 (Infrastructure) | +5 | 1.2 |
| 세제 정책 (Taxation) | +2 | 1.0 |
| 공급 시장 (Supply) | −5 | 1.0 |
| 임대차 시장 (Rental) | +1 | 0.8 |

### 신뢰도 점수 감점 체계 (Confidence Score Deductions)
| 조건 | 감점 |
|---|---|
| `use(sigungu_avg_pir)` | −20% |
| `use(dong_avg_jeonse_ratio)` | −15% |
| `news_count < 3` | −15% |
| `supply_data_radius > 5km` | −10% |
| `sentiment_agreement_ratio < 0.7` | −10% |

신뢰도 구간: High ≥ 85% / Medium 60~84% / Low < 60%

### 성공 지표 (Success Metrics)
| 지표 | 목표 |
|---|---|
| MAPE (AI 가격 예측 오차) | ≤ 20.2% |
| End-to-End 응답 시간 | ≤ 3초 |
| Groundedness Score | ≥ 0.9 / 1.0 |

## 데이터 갱신 정책
- AI 시세·전세가율: **매주 목요일**
- PIR·입주 물량: **매월 15일**
- 인구 이동: **분기별**
- 뉴스 감성 TTL: **7일**

## Fallback 계층 전략
1. `complex_pir` 없음 → `sigungu_avg_pir` 사용 (−20% 신뢰도)
2. `complex_jeonse_ratio` 없음 → `dong_avg_jeonse_ratio` 사용 (−15% 신뢰도)
3. 공급 데이터 없음 → 인접 5km 가중 합산 (−10% 신뢰도)

## 핵심 테이블 위치
- 메인 데이터: `RICHGO_KR.HACKATHON_2026.*`
- 뉴스 피드: `STAGING.REAL_ESTATE_RSS_FEEDS`
- 감성 분석 결과: `NEWS_SENTIMENT_ANALYSIS` (생성 예정)

## Notion 마스터 기획서
- URL: https://www.notion.so/335d8df03cab81939ccfddd57f0570cb
- 상태: Plan Freeze 완료 (2026-04-01)
