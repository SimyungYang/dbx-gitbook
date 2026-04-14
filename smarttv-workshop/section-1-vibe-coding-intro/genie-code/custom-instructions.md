# Custom Instructions — 팀 규칙을 Genie Code에 심기

> 매번 "Delta로 저장해", "한국어로 해줘"를 반복하지 마세요. **한 번 설정하면 자동 적용됩니다.**

---

## Custom Instructions란?

Genie Code에게 **"항상 이 규칙을 따라줘"**라고 미리 알려주는 설정 파일입니다.

| 레벨 | 파일 위치 | 적용 범위 | 설정 주체 |
|------|----------|----------|----------|
| **개인** | `/Users/{username}/.assistant_instructions.md` | 나만 | 본인 |
| **워크스페이스** | `Workspace/.assistant_workspace_instructions.md` | 팀 전체 | 관리자 |

- 워크스페이스 Instructions가 개인보다 우선
- 최대 **20,000자** (초과분은 무시됨)
- Agent Mode, Chat Mode, 인라인 제안, /fix에 모두 적용
- Quick Fix, Autocomplete에는 적용 안 됨

---

## 설정 방법

### 방법 1: Genie Code Settings에서 직접 편집

1. Genie Code 사이드 패널 열기
2. 하단 ⚙️ 아이콘 (Settings) 클릭
3. "Custom Instructions" 섹션에서 편집

> 📸 **[스크린샷]**: Settings → Custom Instructions 편집 화면

### 방법 2: 파일 직접 생성

Genie Code에게 만들어달라고 하면 됩니다:

```
내 Custom Instructions 파일을 만들어줘.
경로: /Users/{내 username}/.assistant_instructions.md
```

---

## 워크샵용 권장 Custom Instructions

아래 내용을 그대로 복사해서 Custom Instructions에 넣으세요:

```markdown
## 기본 규칙
- 한국어로 답변하되, 기술 용어는 영문 병기 (예: 파이프라인(Pipeline))
- 코드 주석은 한국어로 작성
- PySpark를 기본으로 사용 (pandas 대신)
- SQL은 Databricks SQL 문법 사용

## 네이밍 규칙
- 카탈로그: lge_smart_tv
- 스키마: bronze(원본), silver(정제), gold(집계)
- 테이블명: snake_case (예: daily_viewing_summary)
- 컬럼명: snake_case (예: total_viewing_min)

## 안전 규칙 (중요!)
- 기존 테이블을 DROP/DELETE/UPDATE 하지 말 것
- 결과는 CREATE OR REPLACE TABLE로 저장
- Delta 형식으로 저장
- 테스트 시 SELECT에 LIMIT 1000 적용
- 모든 테이블에 COMMENT 추가

## 코딩 스타일
- SQL 키워드 대문자 (SELECT, FROM, WHERE)
- 복잡한 쿼리는 CTE(WITH) 사용
- 날짜 파티셔닝 기본 적용 (event_date)
```

---

## 팀(워크스페이스) Instructions 예시

관리자가 팀 전체에 적용할 규칙:

```markdown
## 워크스페이스 공통 규칙

### 데이터 거버넌스
- production 카탈로그에 직접 쓰기 금지
- dev, staging 카탈로그에서 개발 후 프로모션
- 민감 데이터(PII) 컬럼은 마스킹 적용

### 코딩 표준
- MLflow 실험 로깅 필수 (모든 ML 작업)
- Delta Lake 포맷만 사용
- OPTIMIZE + ZORDER 정기 실행

### 비용 관리
- 개발 시 LIMIT 1000 적용
- 불필요한 FULL SCAN 지양
- 서버리스 컴퓨트 우선 사용
```

---

## 꿀팁

### Instructions에 넣지 말아야 할 것

| 넣으면 안 되는 것 | 이유 |
|-----------------|------|
| 너무 많은 규칙 (50개+) | 우선순위 혼란, 성능 저하 |
| 모순되는 규칙 | Genie Code가 어느 것을 따를지 모름 |
| 매우 구체적인 작업 지시 | Instructions는 "항상" 적용됨 — 작업별 지시는 프롬프트에 |
| 외부 URL 참조 | Genie Code는 Instructions 기반으로 외부 정보를 가져오지 않음 |

### 효과적인 Instructions 작성 규칙

1. **10~15개 규칙이 최적** (너무 많으면 우선순위 혼란)
2. **구체적인 예시 포함** (예: "snake_case 사용" + 예시 `daily_viewing_summary`)
3. **"하지 마" 규칙 반드시 포함** (DROP 금지 등)
4. **정기적으로 업데이트** (프로젝트 단계에 따라 변경)
