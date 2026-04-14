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
description: LG Smart TV 데이터 ETL 표준 패턴 (CDC, 품질 검증, Medallion)
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

> 📸 **[스크린샷]**: Workspace 파일 브라우저에서 `.assistant/skills/` 디렉토리 구조

---

### 3. 슬래시 명령어

노트북 셀에서 `/`를 입력하면 모든 명령어가 표시됩니다:

> 📸 **[스크린샷]**: `/` 입력 시 나타나는 명령어 목록 (모든 명령어 보이게)

### 특히 유용한 숨겨진 기능

#### `/findTables` — 테이블 검색

```
/findTables 고객 구매 이력
```

Unity Catalog에서 관련 테이블을 검색합니다. 테이블 이름을 모를 때 **가장 먼저 쓰세요.**

> 📸 **[스크린샷]**: `/findTables` 결과 — 관련 테이블 목록 + 설명

#### `/findQueries` — 기존 쿼리 검색

```
/findQueries 시청 분석
```

워크스페이스에서 비슷한 SQL 쿼리를 검색합니다. 기존 작업을 재활용할 때 유용.

> 📸 **[스크린샷]**: `/findQueries` 결과

#### `/optimize` — SQL 최적화 (diff 뷰)

현재 셀의 SQL을 분석하고 최적화 버전을 diff 뷰로 보여줍니다.

> 📸 **[스크린샷]**: `/optimize` diff 뷰 — 원본 vs 최적화

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

AI Dev Kit MCP를 연결하면 Genie Code에 **44개 도구**가 추가됩니다. 단, **20개 도구 제한**이 있어 필요한 것만 활성화해야 합니다.

### 도구 제한 내 선택 전략

| Genie Code가 이미 잘 하는 것 | AI Dev Kit으로 추가해야 하는 것 |
|---------------------------|----------------------------|
| SQL 실행 | **Genie Space 생성/관리** |
| 코드 생성/실행 | **대시보드 생성 (크로스 프로덕트)** |
| Genie Space 질의 | **Job 생성/스케줄링** |
| Vector Search 검색 | **Knowledge Assistant 생성** |
| | **Supervisor Agent 생성** |
| | **Apps 배포** |
| | **Lakebase 관리** |

> 📸 **[스크린샷]**: Settings → MCP Servers → mcp-ai-dev-kit → 도구 ON/OFF 토글 화면

### 필요한 도구 물어보기

```
SDP 파이프라인 + 대시보드 + Genie Space를 만들려면 
어떤 MCP 도구를 활성화하면 좋을지 알려줘
```
