# dbx-gitbook 프로젝트 가이드

## 프로젝트 구조

이 레포는 여러 독립 git repo를 모아놓은 상위 프로젝트. 각 하위 폴더는 원래 별도 git repo로 관리됨.

### 독립 git repo (`.gitignore`에 포함, 메인 repo에서 추적하지 않음)
- `00-databricks-blog/` - 블로그 가이드 원본
- `01-databricks-training/` - 교육자료 원본
- `02-blog-translations/` - 블로그 번역 원본
- `03-ai-trends/` - AI 동향 원본
- `20-handson-genie-code-lge-smarttv/` - LGE Smart TV 핸즈온 원본

### Mintlify 배포용 (메인 repo에 포함)
- `docs-mintlify/` - 위 독립 repo들의 콘텐츠를 Mintlify용 .mdx로 변환한 통합 사이트
  - `docs.json` - Mintlify 네비게이션/설정 파일
  - `blog/` - 블로그 가이드 & 핸즈온
  - `training/` - 교육자료
  - `translations/` - Databricks 공식 블로그 번역
  - `ai-trends/` - AI 동향
  - `workshop/` - 워크샵

> **주의**: `docs-mintlify/`도 원래 독립 git repo였으나, Mintlify가 main 브랜치에서 직접 읽어야 하므로 `.git` 제거 후 메인 repo에 포함시킴 (2026-04-15)

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

## 변경 이력

- 2026-04-15: docs-mintlify를 main 브랜치에 추가, Mintlify monorepo 설정으로 배포
- 2026-04-15: blog/overview.mdx title에서 이미지 마크다운 제거 ("Databricks Enablements")
- 2026-04-15: translations 블로그 목록 최신순 정렬 (docs.json)
