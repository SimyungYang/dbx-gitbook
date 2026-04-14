# 01. 환경 설정

> **소요 시간**: ~5분 | **핵심**: 워크스페이스 접속 → 카탈로그/스키마 생성 → Genie Code 준비

---

## Step 1: Databricks 워크스페이스 접속

1. 제공받은 워크스페이스 URL에 접속
2. 로그인 (SSO 또는 제공된 계정)

> 📸 **[스크린샷]**: Databricks 워크스페이스 랜딩 페이지

---

## Step 2: 노트북 생성

1. 왼쪽 사이드바 → **New** → **Notebook**
2. 노트북 이름: `00_Smart_TV_Workshop`
3. 언어: **Python**
4. 컴퓨트: **Serverless** (또는 할당된 클러스터)

> 📸 **[스크린샷]**: 새 노트북 생성 화면

---

## Step 3: Genie Code Agent Mode 확인

1. 우측 상단 **Genie Code 아이콘** 클릭 (사이드 패널 열림)
2. 하단 모드가 **Agent Mode**인지 확인 (아니면 드롭다운에서 전환)

> 📸 **[스크린샷]**: Genie Code 패널 + Agent Mode 선택

---

## Step 4: 카탈로그 / 스키마 / 볼륨 생성

Genie Code에 아래 프롬프트를 입력합니다:

```
Unity Catalog에 다음 환경을 설정해줘:
- 카탈로그: lge_smart_tv (이미 있으면 스킵)
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
lge_smart_tv 카탈로그의 모든 스키마를 보여줘
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

Genie Code Settings(⚙️) → Custom Instructions에 아래 내용을 붙여넣기 합니다:

```markdown
## 기본 규칙
- 한국어로 답변, 기술 용어는 영문 병기
- PySpark 기본 사용 (pandas 대신)
- SQL은 Databricks SQL 문법

## 네이밍
- 카탈로그: lge_smart_tv
- 스키마: bronze / silver / gold / quarantine
- 테이블/컬럼: snake_case

## 안전 규칙
- 기존 테이블 DROP/DELETE/UPDATE 금지
- CREATE OR REPLACE TABLE 사용
- 테스트 시 LIMIT 1000
- 모든 테이블에 COMMENT 추가
- Delta 형식, event_date 파티셔닝 기본
```

> 📸 **[스크린샷]**: Custom Instructions 편집 화면

> 💡 **꿀팁**: 이 설정을 해두면 이후 프롬프트에서 매번 "Delta로 저장해", "한국어로 해줘"를 반복하지 않아도 됩니다.

---

## Step 6: 환경 검증

모든 설정이 완료되면 간단한 테스트를 합니다:

```
lge_smart_tv.bronze 스키마에 test_table이라는 이름으로 
1행짜리 Delta 테이블을 만들고, 바로 삭제해줘. 
권한과 컴퓨트가 정상인지 확인하는 용도야.
```

성공하면 환경 설정 완료!

---

## 환경 요약

| 항목 | 값 |
|------|-----|
| 카탈로그 | `lge_smart_tv` |
| Bronze 스키마 | `lge_smart_tv.bronze` (17개 Raw 테이블) |
| Silver 스키마 | `lge_smart_tv.silver` (15개 정제 테이블) |
| Gold 스키마 | `lge_smart_tv.gold` (10개 집계 테이블) |
| Quarantine 스키마 | `lge_smart_tv.quarantine` (품질 위반 격리) |
| 볼륨 | `lge_smart_tv.bronze.raw_files` |
| 컴퓨트 | Serverless |
| Genie Code 모드 | Agent Mode |

---

## 다음 단계

- **[02. 가상 데이터 생성](02-data-generation.md)** — 17개 테이블, 250만건 webOS TV 로그 데이터 생성
