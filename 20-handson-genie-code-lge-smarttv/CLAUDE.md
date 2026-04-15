# Databricks Vibe Coding 핸즈온 (Smart TV)

## 프로젝트 개요

- **주제**: Databricks 환경에서의 Vibe Coding 실습
- **시나리오**: Smart TV 데이터 기반 End-to-End 데이터/AI 파이프라인 구축
- **배포 형태**: GitHub 개인 프로필 Push → GitBook 연동으로 교육 가이드 제공

## 교육 구성 (4개 섹션)

### Section 1: Databricks Vibe Coding 리소스 소개
Databricks 환경에서 사용 가능한 3가지 AI 코딩 리소스를 소개한다.

| 리소스 | 설명 | 특징 |
|--------|------|------|
| **Genie Code** | Databricks 내장 AI 코딩 어시스턴트 | 노트북/대시보드/파이프라인 에디터에서 `Cmd+I`로 호출, Agent Mode 지원 |
| **AI Dev Kit** | Claude Code/Cursor 연동 MCP 서버 + Skills | 44개 MCP 도구, 25개 Skills, 크로스 프로덕트 오케스트레이션 |
| **AI Builder App** | Databricks Apps 플랫폼 기반 웹 앱 배포 | FastAPI/React/Streamlit 등 지원, OAuth 인증, Lakebase 연동 |

### Section 2: AI Builder App 배포 핸즈온
Lakebase 미사용 시 제약사항 설명 및 git clone부터 상세 배포 과정 핸즈온.

- Lakebase 미사용 시 제약사항 (OLTP 기능 제한, 세션 관리 등)
- git clone → app.yaml 구성 → requirements.txt → 배포 → 테스트
- Databricks CLI를 통한 앱 생성/배포/관리 전 과정

### Section 3: Genie Code에 AI Dev Kit 구성하기
- **참조**: https://github.com/SimyungYang/genie-code-ai-dev-kit
- AI Dev Kit MCP 서버를 Databricks App으로 배포
- Genie Code Settings에서 MCP 서버 연결
- 15개 도구 제한 내 권장 프로필 선택
- Skills를 `/Workspace/.assistant/skills/`에 배포
- 크로스 프로덕트 오케스트레이션 테스트 (Genie Space 생성 + 대시보드 + Job 스케줄링)

### Section 4: Smart TV 시나리오 End-to-End 핸즈온
- **참조**: https://simyungyang.gitbook.io/databricks-enablement-resources/hands-on-workshop/smart-tv-vibe
- 가상 데이터 생성 (250만건, 17개 테이블) → 데이터 파이프라인 → 분석 → ML → GenAI 에이전트

#### 워크로드 시나리오: Smart TV 데이터 플랫폼

**데이터셋 (가상 데이터 — 17개 테이블, 약 250만건)**:

webOS TV 실제 텔레메트리 로그 체계(pmlogd, Luna Service API, rdxd)를 기반으로 설계.
상세 가이드: [02-data-generation.md](section-4-smart-tv-handson/02-data-generation.md)

| 카테고리 | 테이블 | 건수 | 설명 |
|---------|--------|------|------|
| Master | `bronze.devices` | 10,000 | TV 디바이스 마스터 (모델명, 패널, SoC, 지역 등) |
| System | `bronze.system_boot_events` | 50,000 | 부팅/전원 상태 전환 이벤트 |
| System | `bronze.resource_utilization` | 200,000 | CPU/메모리/GPU/온도 1분 간격 메트릭 |
| System | `bronze.firmware_updates` | 15,000 | OTA 펌웨어 업데이트 시퀀스 |
| Viewing | `bronze.viewing_logs` | 500,000 | 채널/앱 시청 기록 (장르, 해상도, HDR) |
| Viewing | `bronze.app_launch_events` | 300,000 | SAM 앱 실행/종료 이벤트 |
| Viewing | `bronze.input_switch_events` | 80,000 | HDMI 입력 전환 (CEC, ALLM, VRR) |
| Network | `bronze.wifi_connection_events` | 100,000 | WiFi 연결/해제/인증 이벤트 |
| Network | `bronze.streaming_buffer_events` | 150,000 | 스트리밍 버퍼/비트레이트 이벤트 |
| Media | `bronze.media_playback_events` | 200,000 | 코덱/해상도/HDR/DRM 재생 로그 |
| Ad | `bronze.acr_events` | 300,000 | ACR 자동 콘텐츠 인식 (Live Plus) |
| Ad | `bronze.ad_impressions` | 200,000 | VAST 광고 노출/클릭/전환 퍼널 |
| IoT | `bronze.thinq_device_events` | 50,000 | ThinQ 스마트홈 디바이스 연동 |
| Voice | `bronze.voice_command_events` | 80,000 | 음성 명령 인식/처리 이벤트 |
| App | `bronze.app_lifecycle_events` | 100,000 | 앱 설치/삭제/업데이트 |
| Display | `bronze.panel_diagnostics` | 30,000 | OLED 패널 케어/화질 진단 |
| Error | `bronze.error_crash_events` | 40,000 | 크래시/ANR/OOM/미디어 에러 |

**End-to-End 파이프라인 구성**:

| 순서 | 모듈 | 핵심 기능 | 소요시간 |
|------|------|---------|---------|
| 1 | 환경 설정 | Unity Catalog, Schema, Volume | ~5분 |
| 2 | 가상 데이터 생성 (250만건, 17테이블) | PySpark, Faker, Delta Lake | ~15분 |
| 3 | SDP 파이프라인 (Bronze→Silver→Gold) | Lakeflow Declarative Pipelines, Expectations, 증분 처리 | ~1시간 |
| 4 | AI/BI 대시보드 & Genie Space | Dashboard, Genie Space, 정확도 고도화 | ~1.5시간 |
| 5 | GenAI 에이전트 | Agent Bricks (KA + Genie Agent + Supervisor), Lakebase(선택) | ~2시간 |

**워크샵에서 다루는 Databricks 핵심 기능**:
Unity Catalog, Delta Lake, SDP (Lakeflow), AI/BI Dashboard, AI/BI Genie, Vector Search, Agent Bricks, Model Serving, Apps + Lakebase(선택)

**실습 환경**: 모든 실습을 **Genie Code Agent Mode + AI Dev Kit MCP** 환경에서 진행합니다.

## 시나리오 상세: Smart TV 비즈니스 컨텍스트

### 핵심 유스케이스

1. **시청 행동 분석**: 채널/앱별 시청 패턴, 시간대별 사용량, 장르 선호도
2. **광고 효과 측정**: 광고 노출→클릭→전환 퍼널 분석, CPM/CTR 최적화
3. **콘텐츠 추천**: 시청 이력 기반 ML 추천 모델, A/B 테스트
4. **디바이스 이상 탐지**: 패널 불량, 네트워크 오류, 앱 크래시 등 조기 감지
5. **실시간 모니터링**: 라이브 방송 시청률, 실시간 광고 성과 트래킹
6. **고객 서비스 에이전트**: GenAI 기반 Smart TV 사용 가이드, 트러블슈팅 챗봇

### Gold 테이블 (10개)

| Gold 테이블 | 소비자 | 설명 |
|------------|--------|------|
| `gold.daily_viewing_summary` | 대시보드, Genie | 디바이스별 일별 시청 통계 |
| `gold.content_popularity` | 대시보드, Genie | 프로그램별 인기도, 시청자 수 |
| `gold.hourly_engagement` | 대시보드 | 시간대별 활성 사용자 |
| `gold.ad_campaign_kpi` | 대시보드, Genie | 광고 캠페인 KPI (CTR, VCR, eCPM) |
| `gold.device_health_score` | 대시보드, ML | 디바이스 건강 점수 (0~100, A~F 등급) |
| `gold.streaming_qoe` | 대시보드, Genie | 스트리밍 QoE 지표 |
| `gold.voice_usage_analytics` | 대시보드 | 음성 사용 분석 |
| `gold.iot_ecosystem_stats` | 대시보드, Genie | IoT 생태계 통계 |
| `gold.error_rate_by_firmware` | 대시보드, Genie | 펌웨어별 에러율 |
| `gold.user_engagement_360` | ML, 에이전트 | 사용자 360도 프로파일 |

### 에이전트 아키텍처

```
Supervisor Agent (Smart TV AI 어시스턴트)
├── Knowledge Assistant: 100개 FAQ, RAG 기반 사용 가이드/트러블슈팅
└── Genie Agent: 3개 Genie Space 연동 데이터 분석
    ├── 시청 분석 Genie Space (15개 샘플 질문)
    ├── 광고 성과 Genie Space (5개 샘플 질문)
    └── 디바이스 운영 Genie Space
```

## 파일 구조

```
├── CLAUDE.md                            # 이 파일
├── README.md                            # ✅ GitBook 메인 페이지
├── SUMMARY.md                           # ✅ GitBook 목차
├── section-1-vibe-coding-intro/         # ✅ Section 1: 리소스 소개
│   └── genie-code/                      #    Genie Code 가이드 (9페이지)
├── section-2-ai-builder-app/            # ✅ Section 2: MCP 서버 앱 배포
└── section-4-smart-tv-handson/          # ✅ Section 4: E2E 핸즈온
    ├── 01-setup.md                      #    환경 설정
    ├── 02-data-generation.md            #    250만건 가상 데이터 (17 테이블)
    ├── 03-sdp-pipeline.md               #    SDP 파이프라인 + 증분 처리 + 데이터 품질
    ├── 04-dashboard-genie.md            #    대시보드 3개 + Genie Space 3개 + 정확도 고도화
    └── 05-agent-development.md          #    KA + Genie Agent + Supervisor + Lakebase
```

## 참고 리소스

| 주제 | URL |
|------|-----|
| Genie Code + AI Dev Kit 구성 가이드 | https://github.com/SimyungYang/genie-code-ai-dev-kit |
| Smart TV Vibe 워크샵 (기존) | https://simyungyang.gitbook.io/databricks-enablement-resources/hands-on-workshop/smart-tv-vibe |
| AI Dev Kit GitHub | https://github.com/databricks-solutions/ai-dev-kit |
| Databricks Agent Bricks 문서 | https://docs.databricks.com/generative-ai/agent-bricks |
| Lakebase 문서 | https://docs.databricks.com/database |
| SDP (Lakeflow) 문서 | https://docs.databricks.com/delta-live-tables |

## 작업 규칙

- 교육 가이드 문서는 **한국어**로 작성
- 코드 주석과 변수명은 **영어** 사용
- GitBook 호환 Markdown 형식 유지 (SUMMARY.md 기반 네비게이션)
- 각 섹션은 독립적으로 진행 가능하도록 구성
- 특정 조직/날짜를 직접 언급하지 않고 범용으로 작성
