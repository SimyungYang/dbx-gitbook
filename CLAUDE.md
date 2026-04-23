# dbx-gitbook 프로젝트 가이드

## 프로젝트 구조

모든 콘텐츠를 하나의 git repo에서 통합 관리 (2026-04-15부터).

### 원본 콘텐츠 (.md 형식)
- `00-databricks-blog/` - 블로그 가이드 원본
- `01-databricks-training/` - 교육자료 원본
- `02-blog-translations/` - 블로그 번역 원본
- `03-ai-trends/` - AI 동향 원본
- `20-handson-genie-code-lge-smarttv/` - Smart TV 핸즈온 원본

### Mintlify 배포용 (.mdx 형식)
- `docs-mintlify/` - 위 원본들을 Mintlify용 .mdx로 변환한 통합 사이트
  - `docs.json` - Mintlify 네비게이션/설정 파일
  - `blog/` - 블로그 가이드 & 핸즈온
  - `training/` - 교육자료
  - `translations/` - Databricks 공식 블로그 번역
  - `ai-trends/` - AI 동향
  - `workshop/` - 워크샵

### 레거시
- `mint.json` - 이전 Mintlify 설정 (사용하지 않음, `docs-mintlify/docs.json`이 실제 설정)

## Mintlify 배포 설정

- **커스텀 도메인**: docs.sifi.life (GoDaddy DNS, CNAME → cname.mintlify-dns.com)
- **Mintlify 서브도메인**: ysm-259734fb.mintlify.app
- **GitHub 레포**: simyungyang/dbx-gitbook
- **브랜치**: main
- **Monorepo 설정**: 켜짐, 경로 `docs-mintlify`
- **플랜**: Pro (트라이얼, 2026-04-28까지)
- 서브도메인 이름은 Mintlify에서 자동 부여되며, 대시보드에서 직접 변경 불가 (서포트 문의 필요)

## 작업 시 주의사항

### .gitignore 관리
- `docs-mintlify/`는 .gitignore에서 **제외**되어 있어야 함 (Mintlify가 main 브랜치에서 읽음)
- `00-databricks-blog/`, `01-databricks-training/` 등은 독립 git repo이므로 .gitignore에 포함

### docs-mintlify 내부 .git 금지
- `docs-mintlify/` 안에 `.git` 폴더가 있으면 서브모듈로 인식되어 push 시 내용이 빠짐
- 반드시 `rm -rf docs-mintlify/.git` 후 일반 폴더로 관리

### Mintlify frontmatter 규칙
- `title` 필드에 마크다운 이미지 문법(`![alt](url)`) 사용 불가 - 텍스트로 그대로 렌더링됨
- 이미지가 필요하면 본문에서 사용

### 네비게이션 순서 (docs.json)
- `translations/` 블로그 번역 목록은 **최신순(내림차순)** 정렬
- `overview` 페이지는 그룹 맨 위에 배치

### 페이지 분할 규칙 (필수)
페이지를 분할할 때 **반드시 서브그룹으로 계층화**해야 합니다. 절대 flat으로 나열하지 마세요.

**올바른 예 (서브그룹):**
```json
{
  "group": "DBU와 가격",
  "pages": [
    "training/.../databricks-pricing",
    "training/.../databricks-pricing-basics",
    "training/.../databricks-pricing-advanced"
  ]
}
```

**잘못된 예 (flat 나열) — 절대 금지:**
```json
"training/.../databricks-pricing",
"training/.../databricks-pricing-basics",
"training/.../databricks-pricing-advanced"
```

분할 후 반드시:
1. **docs.json에서 부모+자식을 서브그룹으로 묶을 것**
2. **깨진 링크 전수 검사** (분할로 경로가 바뀜)
3. **전체 문서에서 구 탭명/구 페이지명 참조 확인**
4. **한 페이지 목표: 1-2분 (약 150줄 이하)**

### 서브페이지 제목 규칙 (필수)
"기초/심화" 같은 무의미한 라벨을 **절대 사용하지 마세요.** 각 서브페이지 제목은 **실제 내용을 알 수 있는 설명적 이름**이어야 합니다.

**올바른 예:**
- "DBU 과금 체계" / "SKU별 비용 비교" / "비용 최적화 전략"
- "pip 설치와 초기 설정" / "고급 설정과 프로파일"

**잘못된 예 — 절대 금지:**
- "기초" / "심화" / "Part 1" / "Part 2"

길이로 기계적으로 자르지 말고, **관련 있는 내용끼리 묶어서** 논리적으로 분리하세요.

### 특정 고객 참조 금지 (중요)
문서에 **특정 고객사, 제품명, 프로젝트명을 절대 언급하지 마세요.** 이 문서는 공개 사이트입니다.

- **금지**: IC360, LG, 삼성, 특정 고객 프로젝트명 등
- **허용**: "외부 포털", "고객사 시스템", "운영 시스템" 등 일반적 표현

고객 질문을 레시피로 만들 때는 반드시 **일반화**하세요.
- ❌ "IC360 포털에서 SP 1개로..."
- ✅ "외부 포털에서 SP 1개로..."

### URL 경로 규칙 (주의)
**Mintlify는 기존 디렉토리 구조 변경에 매우 민감합니다.** 새 디렉토리로 대규모 파일 이동을 하면 Mintlify 빌드가 깨질 수 있습니다 (전체 404 발생 경험 있음).

현재 파일 경로는 역사적 구조를 유지합니다:
- `training/` → Databricks 소개 탭 (번호 접두어 포함: 02-, 03- 등)
- `blog/guides/` → 모범 사례 가이드 + AI/ML 탭
- `ai-trends/` → AI/ML & 동향 탭 (동향 부분)
- `translations/` → 공식 블로그 내용 탭
- `releases/` → 릴리스 & 로드맵 탭
- `workshop/` → Genie Code 워크샵 탭
- `blog/hands-on/` → MLOps 핸즈온 탭

**절대 대규모 파일 이동을 시도하지 마세요.** URL 미관보다 사이트 동작이 우선입니다.

## 변경 이력

- 2026-04-15: docs-mintlify를 main 브랜치에 추가, Mintlify monorepo 설정으로 배포
- 2026-04-15: blog/overview.mdx title에서 이미지 마크다운 제거 ("Databricks Enablements")
- 2026-04-15: translations 블로그 목록 최신순 정렬 (docs.json)
