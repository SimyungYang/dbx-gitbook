# 내장 기능 둘러보기 — Skills, MCP, 숨겨진 기능

---

## Genie Code가 기본으로 가진 것들

### 1. Managed MCP (설정 없이 사용 가능)

Genie Code Settings에서 확인할 수 있습니다:

| MCP 서버 | 기능 | 설명 |
|----------|------|------|
| **DBSQL** | SQL 실행 | 자연어 → SQL 변환 및 실행 |
| **Genie Space** | Genie Space 질의 | 연결된 Genie Space에 자연어 질의 |
| **Vector Search** | 벡터 검색 | Vector Search 인덱스 조회 |
| **UC Functions** | 함수 실행 | Unity Catalog에 등록된 함수 실행 |

> 📸 **[스크린샷]**: Settings → MCP Servers → Managed MCP 섹션

### 확인 프롬프트

```
현재 사용 가능한 MCP 서버와 도구 목록을 보여줘
```

---

### 2. Workspace Skills

워크스페이스에 배포된 Skills는 Agent Mode에서 **자동으로 로딩**됩니다.

위치: `Workspace/.assistant/skills/`

> 📸 **[스크린샷]**: Settings → Skills 탭 — 활성화된 Skills 목록

### 확인 프롬프트

```
현재 사용 가능한 Skills 목록을 보여줘
```

```
Spark Declarative Pipeline 관련 Skill이 있어?
```

### Skills 직접 만들기

팀의 도메인 전문성을 Skill로 패키징할 수 있습니다:

```
Workspace/.assistant/skills/
  smart-tv-etl/
    SKILL.md              # 필수 — 메타데이터 + 지침
    etl-patterns.md       # 선택 — 참고 문서
    scripts/
      quality-check.py    # 선택 — 실행 가능 스크립트
```

**SKILL.md** 예시:
```markdown
---
name: smart-tv-etl
description: Smart TV 데이터 ETL 표준 패턴 (CDC, 품질 검증, Medallion)
---

## 사용 시점
ETL 파이프라인이나 데이터 변환 작업 시 이 Skill을 참고하세요.

## 규칙
1. Bronze→Silver에서 항상 중복 제거 (event_id 기준)
2. device_id 참조 무결성 검증 필수
3. NULL 처리: 비즈니스 키는 DROP, 분석 컬럼은 DEFAULT
4. 모든 Silver/Gold 테이블에 event_date 파티션
5. Expectations 최소 2개 이상 필수
```

### Skills 호출 방법

Skills는 두 가지 방법으로 호출됩니다:

| 방법 | 설명 | 예시 |
|------|------|------|
| **자동 로딩** | 프롬프트 내용에 맞는 Skill이 자동으로 로딩됨 | "SDP 파이프라인 만들어줘" → SDP Skill 자동 로딩 |
| **@멘션** | `@`를 입력한 뒤 스크롤 맨 아래에서 Skill 선택 | `@smart-tv-etl 시청 데이터 ETL을 표준 패턴으로 만들어줘` |

> 💡 **@멘션 사용법**: 프롬프트 입력창에서 `@`를 입력하면 테이블, 노트북 등과 함께 **Skills**도 목록에 나타납니다 (스크롤 하단). 특정 Skill을 확실히 사용하고 싶을 때 @멘션으로 직접 지정하세요.

> Skills 폴더 구조는 Workspace 파일 브라우저에서 `.assistant/skills/` 경로에서 확인할 수 있습니다.

---

### 3. 슬래시 명령어

노트북 셀에서 `/`를 입력하면 사용 가능한 명령어가 나타납니다. `/findTables`, `/fix`, `/optimize` 등 7개 명령어를 제공합니다.

> 전체 명령어 목록과 사용법은 [시작하기 — 슬래시 명령어](getting-started.md#슬래시-명령어)를 참조하세요.

---

### 4. 자연어 데이터 필터링

셀 실행 결과가 테이블로 나올 때, 상단의 **Filter 아이콘**을 클릭하면 자연어로 필터링:

```
한국 지역의 OLED TV만
매출 100만 이상
최근 7일
```

> 📸 **[스크린샷]**: 결과 테이블 상단 Filter 아이콘 → 자연어 입력 → 필터링된 결과

---

### 5. 이미지 업로드

Genie Code 대화창에 이미지를 **드래그&드롭** 또는 **Cmd+V**로 붙여넣을 수 있습니다:

| 이미지 유형 | 활용법 |
|------------|--------|
| 화이트보드 사진 | 아키텍처 → 코드 변환 |
| ERD 다이어그램 | 테이블 생성 SQL |
| 에러 스크린샷 | 에러 진단 |
| 차트/그래프 | 비슷한 시각화 생성 |
| UI 목업 | 대시보드 레이아웃 참고 |

```
(이미지 붙여넣기 후)
이 아키텍처 다이어그램을 기반으로 SDP 파이프라인 코드를 만들어줘
```

> 📸 **[스크린샷]**: 이미지 붙여넣기 → 코드 생성 과정

---

### 6. Diagnose Error + Quick Fix

에러 발생 시 셀 하단에 나타나는 두 가지 버튼:

| 버튼 | 동작 |
|------|------|
| **Diagnose Error** | 에러 원인 분석 + 설명 |
| **Quick Fix** | 수정 코드 제안 + "Accept and run" 원클릭 실행 |

> 📸 **[스크린샷]**: 에러 셀 하단의 "Diagnose Error" + "Quick Fix" 버튼
> 📸 **[스크린샷]**: Quick Fix 제안 — "Accept and run" 버튼

---

## MCP 확장: AI Dev Kit 연결 시 추가되는 기능

AI Dev Kit MCP를 연결하면 Genie Code에 **44개 도구**가 추가되어, Genie Space 생성, 대시보드, Job 스케줄링, Agent Bricks 등 **크로스 프로덕트 작업**이 가능해집니다. 단, **전체 MCP 서버에 걸쳐 최대 20개 도구**만 활성화할 수 있어 선택이 필요합니다.

> 상세 구성 방법, 도구 선택 전략, 프로필별 추천은 [Section 3: Genie Code + AI Dev Kit 연결](../../section-3-ai-tools-setup/genie-code-aidevkit.md)을 참조하세요.

---

## 다음 단계

Section 1이 완료되었습니다! 다음으로 이동하세요:

- **[Section 2: AI Builder App 배포](../../section-2-ai-builder-app/README.md)** — AI Dev Kit MCP 서버를 Databricks App으로 배포합니다.
