# 05. 에이전트 개발 — Knowledge Assistant, Genie Agent, Supervisor

| 항목 | 내용 |
|------|------|
| **소요 시간** | ~2시간 |
| **사전 조건** | [04. 대시보드 & Genie Space](04-dashboard-genie.md) 완료 (Genie Space 3개 필요) |
| **실습 환경** | Genie Code + AI Dev Kit MCP 연결 상태 |
| **사용 MCP 도구** | `manage_ka`, `manage_mas`, `manage_vs_index`, `manage_vs_endpoint`, `manage_lakebase_database` |

> **핵심 메시지**: "대시보드는 보는 것, Genie는 묻는 것, 에이전트는 행동하는 것"

### 이 모듈에서 사용하는 Databricks 기능

| 기능 | 설명 | 공식 문서 |
|------|------|----------|
| **Agent Bricks** | Databricks에서 AI 에이전트를 **코드 없이 UI/API로 생성**하는 기능입니다. Knowledge Assistant(문서 Q&A), Genie Agent(데이터 분석), Supervisor(오케스트레이션) 세 가지 유형이 있습니다. | [docs](https://docs.databricks.com/en/generative-ai/agent-bricks/index.html) |
| **Vector Search** | 텍스트를 벡터(숫자 배열)로 변환하여 **의미적으로 유사한 문서**를 빠르게 찾는 기능입니다. Knowledge Assistant의 핵심 — FAQ 문서를 인덱싱하여 관련 답변을 검색합니다. | [docs](https://docs.databricks.com/en/generative-ai/vector-search.html) |
| **Model Serving** | AI 모델을 API 엔드포인트로 배포하여 실시간으로 호출하는 기능입니다. 에이전트의 LLM(Claude, Llama 등)과 임베딩 모델이 여기서 서빙됩니다. | [docs](https://docs.databricks.com/en/machine-learning/model-serving/index.html) |
| **Lakebase** | Databricks에 내장된 **PostgreSQL 호환 OLTP 데이터베이스**입니다. 에이전트 대화 이력, 사용자 선호도 등 트랜잭션 데이터를 저장합니다. (선택 사항) | [docs](https://docs.databricks.com/en/database/index.html) |

## 개요

이 모듈에서는 3가지 유형의 에이전트를 구축하고, 이들을 하나의 **Supervisor Agent**로 통합합니다:

| 에이전트 | 역할 | 데이터 소스 | 사용 시나리오 |
|---------|------|-----------|-------------|
| **Knowledge Assistant** | Smart TV 사용 가이드 Q&A | PDF/문서 (Vector Search) | "DolbyVision 설정 방법은?", "OLED 번인 예방법은?" |
| **Genie Agent** | 데이터 기반 분석 질의 | Gold 테이블 (Genie Space) | "이번 주 시청 시간 추이는?", "에러율이 높은 펌웨어는?" |
| **Supervisor Agent** | 위 에이전트 오케스트레이션 | 위 에이전트들 | 질문 의도에 따라 적절한 에이전트로 라우팅 |

**Supervisor Agent** → 질문의 의도를 파악하여 적절한 에이전트로 라우팅

| 사용자 질문 유형 | 라우팅 대상 | 예시 |
|---------------|-----------|------|
| 사용법/설정/트러블슈팅 | **Knowledge Assistant** (문서 기반) | "OLED 번인 예방하려면 설정에서..." |
| 데이터/통계/추이 | **Genie Agent** (데이터 기반) | "이번 주 Netflix 시청시간은 평균 45분..." |
| 복합 질문 | **KA + Genie 둘 다** 호출 | "버퍼링 현황과 해결 방법은?" |

---

## Part A: Knowledge Assistant (KA) — Smart TV 가이드 챗봇

### 개념

Knowledge Assistant는 **비정형 문서**(PDF, 매뉴얼, FAQ)를 Vector Search로 인덱싱하여, 사용자 질문에 관련 문서 조각을 찾아 답변하는 RAG 기반 에이전트입니다.

> 💡 **왜 일반 SQL 검색이 아닌 Vector Search?** SQL의 `LIKE '%번인%'` 검색은 정확히 "번인"이라는 단어가 포함된 문서만 찾습니다. 하지만 Vector Search는 "OLED 화면 잔상 방지"처럼 **의미적으로 비슷한 문서**도 찾아냅니다. 이것이 RAG(Retrieval-Augmented Generation) 기반 에이전트의 핵심입니다. RAG란 "질문과 관련된 문서를 먼저 검색(Retrieval)한 뒤, 그 문서를 LLM에 전달하여 답변을 생성(Generation)하는 방식"입니다.

### Step 1: 지식 문서 준비

#### Genie Code 프롬프트: FAQ 문서 생성

```
Smart TV webOS 사용 가이드 FAQ 문서를 생성해줘. Delta 테이블 형태로 만들어줘.

테이블: smart_tv.bronze.tv_knowledge_base

컬럼:
- doc_id: STRING (고유 문서 ID)
- category: STRING (카테고리)
- title: STRING (질문/제목)
- content: STRING (답변 내용, 500~1500자)
- tags: ARRAY<STRING> (관련 태그)
- last_updated: DATE

카테고리별 문서 (총 100개):

1. 초기 설정 (15개):
   - Wi-Fi 연결 방법, 리모컨 페어링, 채널 검색, Google/Apple 계정 연동
   - ThinQ 앱 연결, 음성 비서 설정 (ThinQ AI, Alexa, Google)
   - 화면 모드 설정 (Filmmaker, Vivid, Game, HDR Cinema)
   - HDMI CEC 설정 (Simplink), eARC 설정, 사운드바 연결

2. 화질/디스플레이 (20개):
   - OLED 번인 예방법 (픽셀 리프레셔, 화면 보호기, Logo Luminance 조정)
   - DolbyVision vs HDR10 vs HDR10Plus 차이점
   - AI 화질 조정 (AI Super Upscaling, AI 밝기 조절)
   - 게임 모드 설정 (ALLM, VRR, G-Sync Compatible, FreeSync)
   - 120Hz 설정 (HDMI 2.1, 4K@120, Instant Game Response)
   - 에너지 절약 모드별 화질 영향

3. 오디오 (15개):
   - Dolby Atmos 설정, eARC 패스스루, WiSA 스피커 연결
   - AI Sound Pro 모드 설명
   - 블루투스 오디오 연결 (지연 최소화 방법)
   - 사운드바 Q심포니 설정

4. 앱/스트리밍 (15개):
   - Netflix 4K DolbyVision 시청 조건
   - YouTube 8K/4K HDR 재생 설정
   - Disney+ DolbyAtmos 활성화
   - FAST 채널 사용법
   - 앱 캐시 삭제, 앱 재설치 방법

5. 트러블슈팅 (20개):
   - Wi-Fi 연결 안 됨 → 진단 방법 (DNS, DHCP, 5GHz 호환)
   - 화면 깜빡임 → OLED 패널 리프레시, HDMI 케이블 확인
   - 소리 안 남 → 오디오 출력 설정, eARC 핸드셰이크 초기화
   - 리모컨 반응 없음 → 배터리, 페어링 리셋, IR 센서 확인
   - 앱 크래시 → 캐시 삭제, 앱 재설치, 펌웨어 업데이트
   - HDMI 디바이스 인식 안 됨 → CEC 설정, HDMI 포트 교체
   - 인터넷 속도 느림 → DNS 변경, Wi-Fi 채널 최적화
   - 펌웨어 업데이트 실패 → USB 수동 업데이트 방법

6. 스마트홈/IoT (15개):
   - ThinQ 앱으로 가전 제어 (에어컨, 세탁기, 냉장고)
   - Matter 지원 디바이스 연결
   - TV를 IoT 허브로 사용하기
   - 루틴 설정 (귀가 시 자동 TV + 에어컨 ON)

Delta 테이블로 저장하고, 실제 webOS TV 매뉴얼 수준의 상세하고 정확한 한국어 콘텐츠로 작성해줘.
```

### Step 2: Knowledge Assistant 생성

#### 사전 준비: Vector Search 엔드포인트 생성

> ⚠️ Vector Search 엔드포인트 생성은 **5~10분** 소요됩니다. KA 생성 전에 미리 시작하세요:

```
Vector Search 엔드포인트를 만들어줘.
- 이름: vs-endpoint-smart-tv
- 타입: Managed (Databricks 관리)
상태가 Online이 되면 알려줘.
```

> 엔드포인트 상태가 "Online"이 된 후 아래 Knowledge Assistant 생성을 진행하세요.

#### Genie Code 프롬프트 (AI Dev Kit MCP 활용)

```
Knowledge Assistant를 만들어줘.

설정:
- 이름: Smart TV 가이드
- 설명: Smart TV webOS 사용 방법, 설정, 트러블슈팅에 대해 답변합니다.
- 지식 소스: smart_tv.bronze.tv_knowledge_base 테이블
  - 임베딩 대상 컬럼: content
  - 메타데이터 컬럼: category, title, tags
- Vector Search 엔드포인트: vs-endpoint-smart-tv (없으면 새로 생성)
- Vector Search 인덱스: vs-index-tv-knowledge
- 임베딩 모델: databricks-gte-large-en (Databricks Foundation Model)
- LLM 모델: databricks-claude-sonnet-4 또는 databricks-meta-llama-3.3-70b-instruct
- System Prompt:

"당신은 Smart TV webOS 전문 어시스턴트입니다.
규칙:
1. 반드시 제공된 지식 문서에 기반하여 답변하세요.
2. 문서에 없는 내용은 '해당 정보를 찾을 수 없습니다'라고 답하세요.
3. 한국어로 답변하되, 기술 용어는 영문 병기 (예: 픽셀 리프레셔(Pixel Refresher))
4. 단계별 가이드가 필요한 경우 번호 매기기를 사용하세요.
5. 관련된 추가 팁이 있으면 '💡 참고' 형태로 추가하세요.
6. 안전 관련 주의사항이 있으면 반드시 언급하세요."

Knowledge Assistant를 생성하고 테스트 질문 3개를 실행해줘:
1. "OLED 번인을 예방하려면 어떻게 해야 하나요?"
2. "PS5를 120Hz로 연결하는 방법을 알려주세요"
3. "WiFi가 자꾸 끊기는데 어떻게 해야 하나요?"
```

### KA 생성 확인

```
"Smart TV 가이드" Knowledge Assistant가 정상 생성됐는지 확인해줘.
Vector Search 엔드포인트 상태와 인덱스 문서 수도 알려줘.
```

> ⚠️ **주의**: Vector Search 인덱싱은 **5~10분** 소요됩니다. 인덱스 상태가 "PROVISIONING"이면 "ONLINE"이 될 때까지 기다린 뒤 테스트하세요. 인덱싱 완료 전에 KA에 질문하면 "관련 문서를 찾을 수 없습니다"라고 답합니다.

### Step 3: Knowledge Assistant 테스트 & 평가

#### Genie Code 프롬프트

```
방금 만든 "Smart TV 가이드" Knowledge Assistant에 다음 질문을 보내고 답변 품질을 평가해줘:

평가 기준:
- 정확성: 답변이 사실에 부합하는지 (1~5점)
- 완전성: 질문에 충분히 답했는지 (1~5점)
- 관련성: 검색된 문서가 질문과 관련있는지 (1~5점)
- 가독성: 답변이 읽기 쉬운지 (1~5점)

테스트 질문 10개:
1. "DolbyVision이 뭔가요? 어떻게 켜나요?"
2. "에어컨을 TV에서 제어할 수 있나요?"
3. "넷플릭스에서 4K로 안 나와요"
4. "리모컨 음성 인식이 안 돼요"
5. "TV 전기세를 줄이려면?"
6. "게임할 때 입력 지연을 줄이려면?"
7. "사운드바를 eARC로 연결하는 방법"
8. "OLED TV를 오래 쓰려면 어떤 설정이 좋나요?"
9. "펌웨어 업데이트가 실패했어요"
10. "Matter 디바이스를 연결하는 방법은?"

각 질문의 4가지 점수와 종합 평균을 표로 보여줘.
평균 4점 미만인 질문은 knowledge_base에 문서를 보강해야 할 후보야.
```

---

## Part B: Genie Agent — 데이터 분석 에이전트

### 개념

Genie Agent는 앞서 만든 **Genie Space**를 에이전트의 도구(tool)로 사용하여, 데이터 기반 질문에 SQL 쿼리로 답변합니다.

### Step 1: Genie Agent 생성

#### Genie Code 프롬프트 (AI Dev Kit MCP 활용)

```
다음 Genie Space들을 도구로 사용하는 Genie Agent를 만들어줘.

설정:
- 이름: Smart TV 데이터 분석가
- 설명: Smart TV 시청 데이터, 광고 성과, 디바이스 건강 상태를 분석합니다.
- 연결할 Genie Space:
  1. "Smart TV 시청 분석" (시청/콘텐츠/사용자 행동)
  2. "Ad Performance" (광고 성과)
  3. "TV 디바이스 운영 분석" (디바이스 건강/에러)
- LLM 모델: databricks-claude-sonnet-4

System Prompt:
"당신은 Smart TV 데이터 분석 전문가입니다.
규칙:
1. 시청 관련 질문 → 'Smart TV 시청 분석' Genie Space 사용
2. 광고 관련 질문 → 'Ad Performance' Genie Space 사용
3. 디바이스/에러 관련 질문 → 'TV 디바이스 운영 분석' Genie Space 사용
4. 숫자 결과는 표 형태로 정리
5. 추세/비교 분석 시 증감률(%)을 반드시 포함
6. 한국어로 답변하되 전문 용어는 영문 병기"

생성 후 테스트:
1. "이번 주 한국 지역 시청 시간 추이를 분석해줘"
2. "screensaver 광고의 CTR이 banner보다 높아?"
3. "에러율이 가장 높은 펌웨어 버전 3개를 알려줘"
```

### Genie Agent 생성 확인

```
"Smart TV 데이터 분석가" Genie Agent가 정상 생성됐는지 확인해줘.
연결된 Genie Space 3개가 모두 인식되는지도 확인해줘.
```

---

## Part C: Supervisor Agent — 멀티 에이전트 오케스트레이션

### 개념

Supervisor Agent는 사용자 질문의 **의도(intent)**를 파악하여, 적절한 하위 에이전트로 라우팅합니다. 단일 질문이 여러 에이전트의 정보를 필요로 할 수도 있습니다.

### Step 1: Supervisor Agent 생성

#### Genie Code 프롬프트 (AI Dev Kit MCP 활용)

```
Supervisor Agent를 만들어줘.

설정:
- 이름: Smart TV AI 어시스턴트
- 설명: Smart TV에 관한 모든 질문에 답변하는 통합 AI 어시스턴트입니다. 사용 가이드, 데이터 분석, 트러블슈팅을 지원합니다.
- 하위 에이전트:
  1. "Smart TV 가이드" (Knowledge Assistant) — 사용법, 설정, 트러블슈팅
  2. "Smart TV 데이터 분석가" (Genie Agent) — 시청 데이터, 광고, 디바이스 분석
- LLM 모델: databricks-claude-sonnet-4

System Prompt:
"당신은 Smart TV 통합 AI 어시스턴트입니다.

## 라우팅 규칙
사용자 질문의 의도를 파악하여 적절한 에이전트로 라우팅하세요:

### Knowledge Assistant로 보낼 질문:
- "어떻게 ~하나요?", "~하는 방법", "~설정"
- 제품 기능 설명, 트러블슈팅, 사용 가이드
- 예: 'DolbyVision 켜는 법', 'WiFi 끊김 해결', 'OLED 번인 예방'

### Genie Agent (데이터 분석)로 보낼 질문:
- "얼마나", "몇 개", "추이", "비교", "분석"
- 숫자/통계/트렌드가 포함된 질문
- 예: '이번 주 시청 시간', '가장 인기 있는 앱', '에러율 추이'

### 두 에이전트 모두 필요한 질문:
- 데이터 + 가이드가 함께 필요한 경우
- 예: 'Netflix 4K가 재생 안 되는 디바이스가 많은데, 해결 방법은?'
  → 먼저 Genie: Netflix 관련 에러 통계 조회
  → 그 다음 KA: Netflix 4K 재생 조건 및 트러블슈팅 가이드

## 답변 규칙
1. 에이전트 라우팅 결정을 사용자에게 노출하지 마세요
2. 여러 에이전트의 답변은 자연스럽게 통합하여 하나의 답변으로 제공
3. 한국어로 답변하되, 기술 용어는 영문 병기
4. 답변 끝에 '🔍 관련 질문'으로 후속 질문 2~3개 제안"

Supervisor Agent를 생성해줘.
```

### Step 2: Supervisor Agent 통합 테스트

> 💡 **테스트 전략**: 5개 시나리오를 한꺼번에 테스트하지 말고, **단순 → 복잡** 순서로 하나씩 진행하세요. 각 시나리오 사이에 결과를 확인하고, 문제가 있으면 먼저 해결한 뒤 다음으로 넘어갑니다.

**단계별 테스트 순서**:

| 순서 | 테스트 목적 | 프롬프트 | 기대 라우팅 |
|------|-----------|---------|-----------|
| 1단계 | KA 라우팅 확인 | "OLED 번인을 예방하려면?" | → KA |
| 2단계 | Genie 라우팅 확인 | "이번 주 시청 시간 추이는?" | → Genie |
| 3단계 | 하이브리드 라우팅 | "버퍼링 현황과 해결 방법" | → Genie + KA |
| 4단계 | 의사결정 지원 | "ThinQ 사용률과 연결 방법" | → Genie + KA |
| 5단계 | 복합 분석 | "펌웨어 에러 원인과 해결" | → Genie + Genie + KA |

#### Genie Code 프롬프트

```
"Smart TV AI 어시스턴트" Supervisor Agent에 다음 시나리오를 테스트해줘:

시나리오 1 — 순수 가이드 질문:
"OLED TV를 새로 샀는데, 처음 설정할 때 꼭 해야 할 것들을 알려주세요"
→ 기대: KA가 초기 설정 가이드 제공

시나리오 2 — 순수 데이터 질문:
"이번 달 한국 지역에서 가장 많이 시청된 프로그램 Top 5는?"
→ 기대: Genie가 content_popularity 테이블 조회

시나리오 3 — 하이브리드 질문:
"최근 스트리밍 버퍼링이 많이 발생하는 것 같은데, 현황과 해결 방법을 알려주세요"
→ 기대: 
  1. Genie → streaming_qoe에서 버퍼링율 추이 조회
  2. KA → 네트워크 트러블슈팅 가이드 제공

시나리오 4 — 의사결정 지원 질문:
"에어컨을 ThinQ로 TV에서 제어하고 싶은데, 현재 ThinQ 사용률은 어느 정도인가요?"
→ 기대:
  1. Genie → iot_ecosystem_stats에서 ThinQ 사용 통계
  2. KA → ThinQ 앱 연결 및 에어컨 제어 가이드

시나리오 5 — 복합 분석 + 가이드:
"펌웨어 03.33.80에서 미디어 에러가 많은 것 같은데, 원인과 해결 방법은?"
→ 기대:
  1. Genie → error_rate_by_firmware에서 해당 버전 에러 통계
  2. Genie → error_events에서 에러 유형 분석
  3. KA → 펌웨어 업데이트 방법 가이드

각 시나리오별로:
- 어떤 에이전트가 호출되었는지
- 응답 시간 (초)
- 답변 품질 (1~5점)
- 라우팅이 올바른지

결과를 표로 정리해줘.
```

---

## Part D: Lakebase 연동 — 에이전트 세션 관리 (선택)

> Lakebase 사용 가능한 환경에서만 진행합니다.

> **Lakebase 사용 불가 시**: 아래 프롬프트로 확인한 뒤, 불가하면 이 Part를 건너뛰세요. 에이전트는 Lakebase 없이도 정상 동작합니다.
> ```
> 내 환경에서 Lakebase(Databricks managed PostgreSQL)를 사용할 수 있는지 확인해줘.
> ```

### 개념

에이전트와 사용자의 대화 이력을 **Lakebase(PostgreSQL 호환 OLTP)**에 저장하면:
- 대화 컨텍스트 유지 (이전 대화 참조)
- 사용자별 선호도 학습
- 에이전트 사용 패턴 분석

### Step 1: Lakebase 데이터베이스 생성

#### Genie Code 프롬프트 (AI Dev Kit MCP 활용)

```
Lakebase 데이터베이스를 만들어줘.

설정:
- 데이터베이스 이름: smart_tv_agent_db
- 카탈로그: smart_tv

테이블:
1. chat_sessions:
   - session_id UUID PRIMARY KEY
   - device_id VARCHAR(50) -- 어떤 TV에서 질문했는지
   - user_name VARCHAR(100)
   - started_at TIMESTAMP DEFAULT NOW()
   - ended_at TIMESTAMP
   - total_messages INT DEFAULT 0
   - satisfaction_score INT -- 1~5점

2. chat_messages:
   - message_id UUID PRIMARY KEY
   - session_id UUID REFERENCES chat_sessions
   - role VARCHAR(20) -- 'user' or 'assistant'
   - content TEXT
   - agent_used VARCHAR(50) -- 'ka', 'genie', 'supervisor'
   - response_time_ms INT
   - created_at TIMESTAMP DEFAULT NOW()

3. user_preferences:
   - device_id VARCHAR(50) PRIMARY KEY
   - preferred_language VARCHAR(10) DEFAULT 'ko'
   - notification_enabled BOOLEAN DEFAULT true
   - frequently_asked_topics TEXT[] -- 자주 묻는 주제 배열
   - last_interaction TIMESTAMP

4. agent_feedback:
   - feedback_id UUID PRIMARY KEY
   - message_id UUID REFERENCES chat_messages
   - is_helpful BOOLEAN
   - feedback_text TEXT
   - created_at TIMESTAMP DEFAULT NOW()
```

### Step 2: 에이전트에 Lakebase 연동

#### Genie Code 프롬프트

```
Supervisor Agent의 System Prompt에 대화 이력 저장 로직을 추가해줘.

규칙:
1. 새 대화 시작 시 chat_sessions에 세션 생성
2. 매 메시지마다 chat_messages에 저장 (user, assistant 모두)
3. agent_used에 실제 호출된 에이전트 기록
4. response_time_ms에 응답 소요 시간 기록
5. 사용자가 "도움이 됐어" / "아니" 등 피드백 시 agent_feedback에 저장
6. 대화 종료 시 session.ended_at과 total_messages 업데이트

Lakebase 연결 정보를 사용하여 구현해줘.
```

---

## Part E: 에이전트 고도화 팁

### 1. Knowledge Assistant 정확도 향상

| 방법 | 설명 | 효과 |
|------|------|------|
| **청킹 최적화** | content를 500자 단위로 분할, 오버랩 100자 | 검색 정밀도 향상 |
| **메타데이터 필터** | category 기반 사전 필터링 | 불필요한 문서 제외 |
| **Hybrid Search** | 키워드 + 벡터 검색 결합 | 정확한 용어 매칭 + 의미 검색 |
| **리랭킹** | 검색 결과 상위 20개를 LLM으로 재정렬 | 최종 답변 품질 향상 |

### 2. Genie Agent 정확도 향상

| 방법 | 설명 | 효과 |
|------|------|------|
| **샘플 질문 추가** | 실패한 질문을 샘플로 등록 | SQL 정확도 직접 향상 |
| **테이블 COMMENT 보강** | 컬럼 값 범위, 단위 명시 | Genie의 컬럼 선택 정확도 |
| **General Instructions** | 비즈니스 용어 사전 추가 | 도메인 용어 이해도 |
| **Gold 테이블 단순화** | 복잡한 조인 사전 수행 | Genie의 SQL 복잡도 감소 |

### 3. Supervisor 라우팅 정확도 향상

| 방법 | 설명 |
|------|------|
| **의도 분류 예시 추가** | System Prompt에 더 많은 예시 추가 |
| **Fallback 전략** | 라우팅 불확실 시 둘 다 호출하여 답변 통합 |
| **피드백 루프** | agent_feedback 테이블의 데이터로 지속 개선 |

---

## Part F: 실전 데모 시나리오

### 시나리오: "Smart TV CS 상담 어시스턴트"

교육 마무리 데모로 아래 대화를 시연합니다:

```
사용자: 최근 우리 TV에서 Netflix 버퍼링이 많이 발생하고 있나요?

AI: 최근 7일간 Netflix 스트리밍 품질을 분석한 결과입니다:
    - 버퍼링 발생률: 8.2% (전주 대비 +2.1%p 증가)
    - 평균 QoE 점수: 72/100 (전주 78에서 하락)
    - 주요 영향 지역: 한국(10.5%), 동남아(9.8%)
    - 4K 스트림에서 버퍼링 집중 (12.3% vs FHD 3.1%)

사용자: 왜 이렇게 늘었을까? 그리고 사용자한테 안내할 수 있는 해결 방법이 있어?

AI: [데이터 분석]
    펌웨어 03.33.80 디바이스에서 버퍼링이 집중되고 있습니다:
    - 03.33.80: 버퍼링률 15.2%
    - 03.33.85: 버퍼링률 4.1%
    최근 03.33.80 → 03.33.85 업데이트에 네트워크 스택 개선이 포함된 것으로 보입니다.

    [사용 가이드]
    사용자에게 안내할 수 있는 해결 방법:
    1. 펌웨어 업데이트 확인: 설정 → 지원 → 소프트웨어 업데이트
    2. Wi-Fi 최적화: 5GHz 대역 사용, 라우터와 TV 사이 장애물 제거
    3. DNS 변경: 설정 → 네트워크 → DNS를 8.8.8.8로 수동 설정
    4. 캐시 삭제: Netflix 앱 → 설정 → 캐시 삭제

    🔍 관련 질문:
    - 펌웨어 업데이트 미적용 디바이스는 몇 대인가요?
    - 지역별 네트워크 품질 차이를 볼 수 있나요?
    - Netflix 외 다른 앱도 비슷한 문제가 있나요?
```

---

## 핵심 포인트 정리

| 배운 것 | Databricks 기능 | 비즈니스 가치 |
|---------|----------------|-------------|
| Knowledge Assistant | Vector Search, RAG | 24시간 자동 CS, 매뉴얼 검색 자동화 |
| Genie Agent | Genie Space (NL2SQL) | 비개발자 셀프서비스 분석 |
| Supervisor Agent | Multi-Agent Orchestration | 단일 인터페이스로 모든 질문 해결 |
| Lakebase 연동 | PostgreSQL OLTP | 대화 이력, 선호도 저장 |
| 에이전트 평가 | MLflow Tracing | 품질 모니터링 및 지속 개선 |

---

## 전체 워크샵 완료!

이 워크샵을 통해 구축한 것:

| 단계 | 구축한 것 |
|------|---------|
| **데이터 생성** | 250만건 가상 데이터 (17 테이블) |
| **SDP 파이프라인** | Bronze → Silver → Gold 자동 처리 |
| **분석** | AI/BI 대시보드 3개 + Genie Space 3개 |
| **AI** | Supervisor Agent (KA + Genie Agent) |
| **OLTP** | Lakebase (대화 이력, 사용자 선호도) |
| **도구** | 모든 과정을 Genie Code + AI Dev Kit으로 구축 |
