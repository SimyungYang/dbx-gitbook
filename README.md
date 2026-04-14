# Databricks 가이드 — GitBook 통합 사이트

Databricks 한국어 가이드를 하나의 GitBook Site로 통합 관리하기 위한 프로젝트입니다.
각 Space는 독립된 GitHub 리포로 관리되며, GitBook GitHub Sync로 연결합니다.

## Spaces

| Space | GitHub 리포 | 설명 | 페이지 수 |
|-------|------------|------|----------|
| Databricks Blog | [databricks-enablement-blog](https://github.com/SimyungYang/databricks-enablement-blog) | Enablement 가이드 — AI Trends, Platform Setup, GenAI, RAG, Blog 번역 등 | ~265 |
| Databricks Training | [simyung-dbx-training](https://github.com/SimyungYang/simyung-dbx-training) | 종합 교육자료 — 플랫폼, 레이크하우스, 컴퓨트, DE, DW, UC, ML, Agent, Lakebase | ~231 |
| SmartTV Workshop | [genie-code-workshop-smarttv](https://github.com/SimyungYang/genie-code-workshop-smarttv) | AI Vibe Coding — LG Smart TV 핸즈온 워크샵 | ~28 |

## GitBook 연동 방법

1. GitBook에서 Site 1개 생성
2. 각 리포를 Space로 import (Settings → Connections → GitHub)
3. Site Structure에서 3개 Space를 섹션으로 추가
4. Publish
