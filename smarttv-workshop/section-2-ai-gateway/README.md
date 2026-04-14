# AI Gateway — AI 도구 비용 관리

> **핵심 메시지**: AI 도구(Genie Code, Claude Code 등)를 도입할 때 가장 큰 우려는 비용입니다. Databricks AI Gateway를 통해 **사용자별 Rate Limit, 비용 상한, 사용량 모니터링**을 걸 수 있어 제한적이고 안전하게 AI 도구를 도입할 수 있습니다.

---

## AI Gateway란?

Databricks AI Gateway는 모든 AI 모델 호출을 **중앙에서 관리하는 프록시 레이어**입니다.

```
사용자 (Genie Code, Claude Code, Cursor 등)
        │
        ▼
┌─────────────────────────┐
│    Databricks AI Gateway │  ← Rate Limit, 비용 추적, 감사 로그
│    (Model Serving)       │
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  Foundation Models       │
│  (Claude, GPT, Llama 등) │
└─────────────────────────┘
```

### 왜 중요한가?

| 우려 사항 | AI Gateway로 해결 |
|----------|-----------------|
| "AI 도구 비용이 폭발하면?" | **사용자별 Rate Limit** — 분당/시간당/일당 요청 수 제한 |
| "누가 얼마나 썼는지 모르겠다" | **사용량 모니터링** — System Tables에서 사용자별 토큰 사용량 추적 |
| "민감 데이터가 외부로 나가면?" | **Guardrails** — PII 마스킹, 프롬프트 필터링 |
| "특정 모델만 허용하고 싶다" | **모델 라우팅** — 허용된 모델만 접근 가능 |
| "팀별로 예산을 나누고 싶다" | **태깅 + 비용 귀속** — 팀/프로젝트별 비용 분리 |

---

## Databricks에서 제공하는 AI 도구 라이선스

Databricks AI Gateway를 통해 사용할 수 있는 AI 도구들:

| AI 도구 | 용도 | 라이선스 방식 |
|---------|------|-------------|
| **Genie Code** | Databricks 내장 AI 코딩 어시스턴트 | Databricks 워크스페이스에 포함 (추가 비용: 컴퓨트만) |
| **Claude** (Anthropic) | Foundation Model API 통해 제공 | AI Gateway 경유, DBU로 과금 |
| **GPT-4 / GPT-4o** (OpenAI) | Foundation Model API 통해 제공 | AI Gateway 경유, DBU로 과금 |
| **Llama 3** (Meta) | Foundation Model API 통해 제공 | AI Gateway 경유, DBU로 과금 |
| **DBRX** (Databricks) | Databricks 자체 모델 | AI Gateway 경유, DBU로 과금 |

> 💡 **핵심**: 외부 AI 모델을 직접 구독하지 않아도, Databricks **Foundation Model API**를 통해 AI Gateway에서 중앙 관리하면서 사용할 수 있습니다. 비용은 DBU(Databricks Unit)로 통합 과금됩니다.

---

## AI Gateway 주요 기능

### 1. 사용자별 Rate Limit

```
예시: 
- 개발자: 분당 60 요청, 일 10,000 토큰
- 관리자: 제한 없음
- 인턴/실습생: 분당 10 요청, 일 1,000 토큰
```

> 📸 **[스크린샷]**: Model Serving → Endpoint → Rate Limits 설정 화면

### 2. 사용량 모니터링 (System Tables)

```sql
-- 사용자별 AI 모델 사용량 조회
SELECT
  user_identity.email,
  DATE(request_time) AS date,
  COUNT(*) AS request_count,
  SUM(usage.total_tokens) AS total_tokens,
  ROUND(SUM(usage.total_tokens) * 0.00001, 2) AS estimated_cost_usd
FROM system.serving.served_entities_usage
WHERE served_entity_name = 'databricks-claude-sonnet-4'
  AND request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY user_identity.email, DATE(request_time)
ORDER BY total_tokens DESC
```

> 📸 **[스크린샷]**: System Tables 쿼리 결과 — 사용자별 토큰 사용량

### 3. Guardrails (안전 장치)

| Guardrail | 설명 |
|-----------|------|
| **PII 마스킹** | 프롬프트/응답에서 개인정보 자동 마스킹 |
| **Topic 필터** | 비업무 관련 질문 차단 |
| **Safety Filter** | 유해/부적절 콘텐츠 필터링 |
| **Input/Output Validation** | 입출력 길이 제한, 포맷 검증 |

### 4. 비용 귀속 (Cost Attribution)

```
팀A (데이터 엔지니어링) → 월 $500 상한
팀B (데이터 분석)       → 월 $300 상한
팀C (ML/AI)            → 월 $1,000 상한
```

System Tables + 태깅으로 팀별 비용을 분리하고 대시보드로 모니터링할 수 있습니다.

---

## 도입 시나리오: LGE MS사업본부

### Phase 1: 파일럿 (1개월)

| 항목 | 설정 |
|------|------|
| 대상 | 데이터팀 10명 |
| AI 도구 | Genie Code + Foundation Model API (Claude) |
| Rate Limit | 사용자당 분당 30 요청 |
| 월 예산 | 팀 전체 $2,000 |
| 모니터링 | 주간 사용량 리포트 |

### Phase 2: 확대 (3개월)

| 항목 | 설정 |
|------|------|
| 대상 | MS사업본부 전체 50명 |
| AI 도구 | Genie Code + AI Dev Kit + Foundation Model API |
| Rate Limit | 역할별 차등 (개발자 60/분, 분석가 30/분) |
| 월 예산 | 팀별 예산 분리 |
| 모니터링 | 일간 대시보드 + 월간 비용 리포트 |

---

## AI Gateway 설정 방법 (Genie Code 프롬프트)

### Foundation Model API 엔드포인트 생성

```
Foundation Model API로 Claude Sonnet 엔드포인트를 만들어줘.

설정:
- 엔드포인트 이름: lge-ms-claude-sonnet
- 모델: claude-sonnet-4
- Rate Limit: 분당 60 요청
- Scale to Zero: 활성화 (비사용 시 비용 0)
```

### 사용량 모니터링 대시보드

```
system.serving.served_entities_usage 테이블을 활용하여
"AI 사용량 모니터링" 대시보드를 만들어줘.

위젯:
1. 일별 총 요청 수 추이 (꺾은선)
2. 사용자별 토큰 사용량 Top 10 (막대)
3. 모델별 비용 비중 (도넛)
4. 시간대별 요청 패턴 (히트맵)

필터: 날짜 범위, 사용자, 모델
```

---

## 주요 문서 링크

| 주제 | URL |
|------|-----|
| AI Gateway 개요 | [docs.databricks.com/ai-gateway](https://docs.databricks.com/en/ai-gateway/index.html) |
| Foundation Model API | [docs.databricks.com/foundation-models](https://docs.databricks.com/en/machine-learning/foundation-models/index.html) |
| Model Serving Rate Limits | [docs.databricks.com/model-serving/rate-limits](https://docs.databricks.com/en/machine-learning/model-serving/rate-limits.html) |
| Serving Usage System Table | [docs.databricks.com/system-tables/serving](https://docs.databricks.com/en/administration-guide/system-tables/serving.html) |
| Guardrails | [docs.databricks.com/ai-gateway/guardrails](https://docs.databricks.com/en/ai-gateway/guardrails.html) |

---

## 핵심 정리

> AI 도구 도입의 가장 큰 장벽은 **"비용 통제 불가"** 우려입니다.
> 
> Databricks AI Gateway는:
> 1. **사용자별 Rate Limit**으로 과사용 방지
> 2. **System Tables**로 사용량/비용 실시간 모니터링
> 3. **Guardrails**로 데이터 보안 확보
> 4. **DBU 통합 과금**으로 별도 AI 구독 불필요
>
> → **제한적이고 안전하게** AI 도구를 도입할 수 있습니다.
