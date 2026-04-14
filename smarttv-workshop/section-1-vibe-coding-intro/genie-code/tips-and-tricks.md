# 꿀팁 모음 — 현업에서 바로 쓰는 실전 팁 20가지

---

## 테이블 & 데이터 탐색

### 팁 1: `/findTables`로 테이블 이름 찾기

테이블 이름을 모를 때 직접 타이핑하지 마세요:

```
/findTables smart tv 시청 관련 테이블
```

> Genie Code가 Unity Catalog를 검색해서 관련 테이블 목록을 보여줍니다.

> 📸 **[스크린샷]**: `/findTables` 검색 결과

### 팁 2: "프로파일링해줘" 한마디로 전체 EDA

```
@lge_smart_tv.bronze.viewing_logs를 프로파일링해줘
```

이 한마디로 Genie Code가 자동으로:
- Row count, 컬럼 수
- 각 컬럼의 NULL 비율, 고유값, min/max/mean
- 분포 차트
를 한번에 생성합니다.

### 팁 3: 출력 테이블에서 자연어 필터링

셀 실행 결과 테이블 상단의 **Filter 아이콘**을 클릭하면 자연어로 필터링할 수 있습니다:

```
한국 지역에서 드라마 장르만
```

> 📸 **[스크린샷]**: 셀 출력 테이블의 Filter 아이콘 → 자연어 필터 입력

### 팁 4: `@`로 테이블 자동완성

프롬프트에 `@`를 입력하면 테이블, 노트북, 파이프라인 등을 **자동완성**으로 선택할 수 있습니다. 오타 걱정 없음!

> 📸 **[스크린샷]**: `@` 입력 후 드롭다운

---

## 코드 생성 & 수정

### 팁 5: 라이브러리를 명시하면 원하는 코드가 나옴

```
❌ "차트 만들어줘"          → 어떤 라이브러리를 쓸지 모름
✅ "matplotlib으로 만들어줘"  → matplotlib 코드 생성
✅ "plotly로 만들어줘"       → plotly 인터랙티브 차트
✅ "seaborn으로 만들어줘"    → seaborn 스타일 차트
```

### 팁 6: PySpark vs pandas 명시

데이터가 크면 반드시 PySpark를 지정하세요:

```
PySpark로 처리해줘. pandas 쓰지 마.
```

> 💡 **왜?** 미지정 시 Genie Code가 pandas를 선택할 수 있고, 대용량 데이터에서 OOM 에러 발생

### 팁 7: 에러 발생 → Diagnose Error 원클릭

에러가 발생하면 셀 하단에 **"Diagnose Error"** 버튼이 나타납니다. 클릭 한 번으로 Genie Code가 에러를 분석하고 수정을 제안합니다.

시도 순서: `Diagnose Error 버튼` → `/fix` → 직접 설명

> 📸 **[스크린샷]**: 에러 발생 셀의 "Diagnose Error" 버튼 + Quick Fix 제안

### 팁 8: 잘못된 코드 → "Stop" + 구체적 피드백

Genie Code가 잘못된 코드를 생성하면, 같은 말을 반복하지 마세요:

```
❌ "다시 해줘" → 같은 실수 반복

✅ "Stop. JOIN이 잘못됐어. 
   viewing_logs.device_id = devices.device_id로 조인해야 하는데
   viewing_logs.event_id로 조인했어. 수정해줘."
```

### 팁 9: 이미지를 붙여넣으면 코드로 변환

화이트보드에 그린 아키텍처, ERD, 플로우차트 사진을 **Cmd+V로 붙여넣기**하면:

```
이 다이어그램을 기반으로 파이프라인 코드를 만들어줘
```

> 📸 **[스크린샷]**: 이미지 드래그앤드롭 후 코드 생성되는 모습

---

## 대화 관리

### 팁 10: 새 작업 = 새 대화 (가장 중요!)

**하나의 대화에 여러 작업을 섞으면 환각이 발생합니다.** 
EDA, ETL, 대시보드는 각각 별도 대화에서 진행하세요.

### 팁 11: 대화 내에서 반복 개선은 OK

같은 작업을 개선하는 것은 대화를 이어가도 됩니다:

```
"이 차트를 막대에서 꺾은선으로 바꿔줘"
"x축 레이블을 45도 회전해줘"
"범례를 우측 상단으로 옮겨줘"
```

### 팁 12: 프롬프트 줄바꿈은 `Shift+Enter`

긴 프롬프트를 여러 줄로 작성할 때:
- `Enter` = 전송
- `Shift+Enter` = 줄바꿈 (전송 안 됨)

### 팁 13: 실행 중 탭 전환하지 마세요

Agent Mode 실행 중 **브라우저 탭을 전환하면 에이전트가 일시 중지**됩니다. 돌아오면 재개되지만, 복잡한 작업에서는 상태가 꼬일 수 있습니다.

**절대 금지**: 실행 중 페이지 새로고침 → 에이전트 세션 사망

---

## SDP 파이프라인

### 팁 14: Pipeline Editor에서 Genie Code 사용

Lakeflow Pipeline Editor에서 Genie Code를 열면 **SDP 코드를 자연어로 생성**할 수 있습니다:

```
Bronze→Silver→Gold medallion 파이프라인을 만들어줘.
Bronze는 Streaming Table, Gold는 Materialized View로.
각 테이블에 data quality expectations 추가해줘.
```

> 📸 **[스크린샷]**: Pipeline Editor에서 Genie Code가 SDP 코드를 생성하는 화면

### 팁 15: Expectations 추가를 요청하면 자동 적용

```
이 파이프라인에 data quality expectations를 추가해줘:
- valid_duration: duration_sec > 0 AND duration_sec <= 86400
- valid_device: device_id IS NOT NULL
- not_null_timestamp: timestamp IS NOT NULL
```

---

## 대시보드

### 팁 16: 위젯 타입과 레이아웃을 명시하면 정확한 대시보드

```
Row 1: KPI 카운터 4개 (총 노출수, CTR, VCR, 수익)
Row 2: 일별 추이 꺾은선 2개
Row 3: 막대 차트 2개 + 도넛 1개
필터: 날짜 범위, 지역
```

> 📸 **[스크린샷]**: 대시보드 편집 모드에서 Genie Code로 위젯 생성

### 팁 17: 기존 대시보드 위젯 수정도 가능

```
"Row 2의 두 번째 차트를 막대에서 꺾은선으로 바꿔줘"
"모든 차트의 색상을 LG 브랜드 컬러(#A50034)로 통일해줘"
```

---

## Genie Space

### 팁 18: 테이블 COMMENT가 Genie 정확도의 90%

Genie Space에 테이블을 추가하기 **전에** 반드시 COMMENT를 추가하세요:

```
@lge_smart_tv.gold 스키마의 모든 테이블과 컬럼에 
비즈니스 담당자가 이해할 수 있는 한국어 COMMENT를 달아줘.
값의 의미, 단위, 범위를 포함해줘.
```

> 💡 **꿀팁**: COMMENT가 없으면 Genie는 컬럼명만 보고 추측합니다. `total_viewing_min`이 "분" 단위인지 "건수"인지 모릅니다.

### 팁 19: 샘플 질문 등록이 정확도를 직접적으로 올림

Genie Space 설정에서 검증된 SQL과 함께 샘플 질문을 등록하면, 비슷한 질문이 들어올 때 **해당 패턴을 참고**합니다.

5개만 등록해도 정확도가 크게 올라갑니다. → [상세 가이드](../../section-4-smart-tv-handson/04-dashboard-genie.md)

> 📸 **[스크린샷]**: Genie Space 설정 — Sample Questions 등록 화면

### 팁 20: General Instructions에 비즈니스 용어 사전 넣기

```
## 비즈니스 용어
- "프라임타임": 20:00~23:00 KST
- "활성 디바이스": 당일 시청 기록이 1건 이상인 디바이스
- "Power User": 일 평균 시청 240분 이상
- 비율 계산 시 분모가 0이면 NULL 반환
- 날짜 미지정 시 기본 최근 7일
```

> 📸 **[스크린샷]**: Genie Space 설정 — General Instructions 편집

---

## 보너스: 숨겨진 기능

### MCP 도구로 Genie Code 확장

Settings → MCP Servers에서 추가 도구를 연결할 수 있습니다:

```
현재 연결된 MCP 서버와 활성화된 도구를 보여줘
```

> 📸 **[스크린샷]**: Settings → MCP Servers 화면

### Genie Code에게 필요한 도구 물어보기

특정 작업 전에 이렇게 물어볼 수 있습니다:

```
SDP 파이프라인 생성을 위해 활성화하면 도움 될 MCP 도구를 알려줘
```

### 자연어로 쿼리 결과 해석

SQL 결과가 나온 후:

```
이 결과를 비즈니스 관점에서 해석해줘. 
핵심 인사이트 3가지를 뽑아줘.
```
