# 01. 환경 설정

| 항목 | 내용 |
|------|------|
| **소요 시간** | ~5분 |
| **핵심** | 워크스페이스 접속 → 카탈로그/스키마 생성 → Genie Code + MCP 준비 |

### 이 모듈에서 사용하는 Databricks 기능

| 기능 | 설명 | 공식 문서 |
|------|------|----------|
| **Unity Catalog** | Databricks의 통합 데이터 거버넌스 플랫폼. 카탈로그 > 스키마 > 테이블 3단계로 데이터를 관리하고, 권한·리니지·태그를 중앙에서 통제합니다. | [docs](https://docs.databricks.com/en/data-governance/unity-catalog/index.html) |
| **Genie Code Agent Mode** | Genie Code의 자율 실행 모드. 계획 → 코드 생성 → 실행 → 검증 → 에러 수정을 자동으로 반복합니다. 실행 전 사용자 승인을 요청합니다. | [docs](https://docs.databricks.com/en/genie-code/index.html) |
| **Serverless Compute** | Databricks가 관리하는 서버리스 컴퓨트. 클러스터를 직접 만들 필요 없이 코드를 바로 실행합니다. Python과 SQL만 지원합니다. | [docs](https://docs.databricks.com/en/compute/serverless.html) |
| **Custom Instructions** | Genie Code에게 "항상 이 규칙을 따라줘"라고 미리 알려주는 설정 파일. 네이밍 규칙, 안전 규칙 등을 한 번 설정하면 자동 적용됩니다. | [docs](https://docs.databricks.com/en/genie-code/instructions.html) |

---

## Step 1: Databricks 워크스페이스 접속

1. 제공받은 워크스페이스 URL에 접속
2. 로그인 (SSO 또는 제공된 계정)

> 📸 **[스크린샷]**: Databricks 워크스페이스 랜딩 페이지

---

## Step 2: 노트북 생성

1. 왼쪽 사이드바에서 **New** → **Notebook** 클릭
2. 노트북 이름을 클릭하여 `00_Smart_TV_Workshop`으로 변경
3. 기본 언어: **Python** (상단에 표시)
4. **컴퓨트 연결**: 노트북 우측 상단의 컴퓨트 선택 버튼 클릭 → **Serverless** 선택
   - 초록색 불이 들어오면 사용 가능한 상태입니다
   - 처음 연결 시 10~20초 정도 소요될 수 있습니다

![Serverless 드롭다운](../section-1-vibe-coding-intro/genie-code/images/serverless-dropdown.png) → ![Serverless 연결 완료](../section-1-vibe-coding-intro/genie-code/images/serverless-connected.png)
*Serverless를 선택하면(왼쪽) 잠시 후 초록불이 켜집니다(오른쪽)*

> 💡 **컴퓨트란?** 코드를 실행하는 컴퓨터입니다. Serverless를 선택하면 Databricks가 관리하는 컴퓨터를 바로 사용할 수 있어, 클러스터를 직접 만들 필요가 없습니다.

---

## Step 3: Genie Code Agent Mode 확인

1. Databricks 화면 우측 상단의 **Genie Code 아이콘**(✨)을 클릭합니다 (노트북이 아닌 어느 페이지에서든 가능)
2. 화면 우측에 **Genie Code 사이드 패널**이 열립니다
3. 패널 하단에서 드롭다운을 클릭 → **Agent** 선택
4. 하단 입력창에 프롬프트를 입력할 수 있는 상태가 됩니다

![Genie Code 패널 + Agent Mode](../section-1-vibe-coding-intro/genie-code/images/genie-code-panel.png)
*Genie Code 사이드 패널이 열리면 하단에서 Agent 모드를 선택합니다*

> ⚠️ **Stop 버튼 확인**: Genie Code가 작업 중일 때는 입력창 우측에 **빨간색 Stop 버튼**이 표시됩니다. 이 버튼이 보이는 동안은 AI가 아직 코드를 실행하고 있으므로, 다음 프롬프트를 입력하지 마세요. 기존 작업을 중단하려면 Stop 버튼을 클릭합니다.

### Agent Mode 동작 확인

```
안녕, Agent Mode가 정상적으로 켜져 있는지 확인해줘.
현재 연결된 컴퓨트 종류와 접근 가능한 카탈로그도 알려줘.
```

> Plan이 표시되고 "Allow" 버튼이 나타나면 Agent Mode가 정상입니다.

---

## Step 4: 카탈로그 / 스키마 / 볼륨 생성

Genie Code에 아래 프롬프트를 입력합니다:

```
Unity Catalog에 다음 환경을 설정해줘:
- 카탈로그: smart_tv (이미 있으면 스킵)
- 스키마: bronze, silver, gold, quarantine (이미 있으면 스킵)
- 볼륨: bronze 스키마에 raw_files 볼륨 생성

각 스키마에 COMMENT도 추가해줘:
- bronze: 'Raw 텔레메트리 로그 데이터'
- silver: '정제/표준화된 데이터'  
- gold: '비즈니스 집계 테이블'
- quarantine: '데이터 품질 위반 레코드'

기존 오브젝트가 있으면 DROP하지 말고 스킵해줘.
```

> 📸 **[스크린샷]**: Genie Code가 카탈로그/스키마 생성 코드를 실행하는 화면

### 생성 결과 확인

```
smart_tv 카탈로그의 모든 스키마를 보여줘
```

기대 결과:

| 스키마 | 설명 |
|--------|------|
| `bronze` | Raw 텔레메트리 로그 데이터 |
| `silver` | 정제/표준화된 데이터 |
| `gold` | 비즈니스 집계 테이블 |
| `quarantine` | 데이터 품질 위반 레코드 |

---

## Step 5: Custom Instructions 설정 (권장)

> Custom Instructions가 무엇인지, 왜 필요한지는 [Section 1: Custom Instructions 설정](../section-1-vibe-coding-intro/genie-code/custom-instructions.md)에서 상세히 설명합니다.

Genie Code Settings(⚙️) → Custom Instructions에 아래 내용을 붙여넣기 합니다:

```markdown
## 기본 규칙
- 한국어로 답변, 기술 용어는 영문 병기
- PySpark 기본 사용 (pandas 대신)
- SQL은 Databricks SQL 문법

## 네이밍
- 카탈로그: smart_tv
- 스키마: bronze / silver / gold / quarantine
- 테이블/컬럼: snake_case

## 안전 규칙
- 기존 테이블 DROP/DELETE/UPDATE 금지
- CREATE OR REPLACE TABLE 사용
- 테스트 시 LIMIT 1000
- 모든 테이블에 COMMENT 추가
- Delta 형식, event_date 파티셔닝 기본

## MCP 도구 활용 (AI Dev Kit)
- Genie Space 생성 → manage_genie
- 대시보드 생성 → manage_dashboard
- Job 스케줄링 → manage_jobs
- KA/Supervisor Agent → manage_ka, manage_mas
- MCP 도구 호출 실패 시 재시도, 노트북 우회 제안하지 말 것
```

> 📸 **[스크린샷]**: Custom Instructions 편집 화면

> 💡 **꿀팁**: 이 설정을 해두면 이후 프롬프트에서 매번 "Delta로 저장해", "한국어로 해줘"를 반복하지 않아도 됩니다.

### Custom Instructions 적용 확인

```
Custom Instructions가 적용됐는지 테스트해줘.
@smart_tv.bronze.devices에서 region별 디바이스 수를 5건만 보여줘.
```

> **확인 포인트**: 한국어 답변, PySpark 사용, LIMIT 포함, snake_case 테이블명이면 정상 적용된 것입니다.

---

## Step 6: 환경 검증

모든 설정이 완료되면 간단한 테스트를 합니다:

```
smart_tv.bronze 스키마에 test_table이라는 이름으로 
1행짜리 Delta 테이블을 만들고, 바로 삭제해줘. 
권한과 컴퓨트가 정상인지 확인하는 용도야.
```

성공하면 환경 설정 완료!

---

## 환경 요약

> **참고**: 아래 테이블 수(17개, 15개, 10개)는 **목표값**입니다. 이 시점에서는 아직 테이블이 없으며, [02. 가상 데이터 생성](02-data-generation.md)과 [03. SDP 파이프라인](03-sdp-pipeline.md)을 완료하면 생성됩니다.

| 항목 | 값 |
|------|-----|
| 카탈로그 | `smart_tv` |
| Bronze 스키마 | `smart_tv.bronze` (17개 Raw 테이블) |
| Silver 스키마 | `smart_tv.silver` (15개 정제 테이블) |
| Gold 스키마 | `smart_tv.gold` (10개 집계 테이블) |
| Quarantine 스키마 | `smart_tv.quarantine` (품질 위반 격리) |
| 볼륨 | `smart_tv.bronze.raw_files` |
| 컴퓨트 | Serverless |
| Genie Code 모드 | Agent Mode |

---

## 다음 단계

- **[02. 가상 데이터 생성](02-data-generation.md)** — 17개 테이블, 250만건 webOS TV 로그 데이터 생성
