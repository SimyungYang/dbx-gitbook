# Databricks Vibe Coding 핸즈온 (Smart TV)

Databricks 환경에서 **Genie Code**와 **AI Dev Kit**을 활용한 Vibe Coding 실습입니다.

Smart TV webOS 텔레메트리 데이터를 기반으로, 자연어 프롬프트만으로 데이터 파이프라인부터 AI 에이전트까지 End-to-End로 구축합니다.

> **실습 환경**: Genie Code Agent Mode + AI Dev Kit MCP

---

## 구성

이 핸즈온은 **3단계**로 나뉩니다:

### 📖 사전 학습 — 실습 전에 읽어보세요

| 주제 | 소요 | 설명 |
|------|------|------|
| [Genie Code 완전 가이드](section-1-vibe-coding-intro/genie-code/) | ~30분 | 프롬프트 원칙, 꿀팁, 템플릿, Custom Instructions |
| [AI Gateway 소개](section-3-ai-tools-setup/ai-gateway.md) | ~10분 | 비용 관리 방법 (참고용) |
| [Claude Code 소개](section-3-ai-tools-setup/claude-code.md) | ~10분 | 외부 AI 코딩 도구 소개 (참고용) |

### 🔧 환경 구성 — 실습 전 한 번만 설정

| 단계 | 소요 | 설명 |
|------|------|------|
| [AI Builder App 배포](section-2-ai-builder-app/) | ~30분 | AI Dev Kit MCP 서버를 Databricks App으로 배포 |
| [AI Dev Kit 설치](section-3-ai-tools-setup/ai-dev-kit-setup.md) | ~10분 | Skills 배포 |
| [Genie Code + AI Dev Kit 연결](section-3-ai-tools-setup/genie-code-aidevkit.md) | ~20분 | MCP 서버 연결 + 도구 선택 + 테스트 |

### 🚀 핸즈온 실습 — 본 실습

| 모듈 | 소요 | 내용 |
|------|------|------|
| [01. 환경 설정](section-4-smart-tv-handson/01-setup.md) | ~5분 | 카탈로그/스키마 생성, Custom Instructions |
| [02. 가상 데이터 생성](section-4-smart-tv-handson/02-data-generation.md) | ~15분 | webOS TV 로그 17테이블 250만건 |
| [03. SDP 파이프라인](section-4-smart-tv-handson/03-sdp-pipeline.md) | ~1시간 | Bronze → Silver → Gold, 데이터 품질 |
| [04. 대시보드 & Genie Space](section-4-smart-tv-handson/04-dashboard-genie.md) | ~1.5시간 | 대시보드 3개, Genie Space 3개, 정확도 고도화 |
| [05. 에이전트 개발](section-4-smart-tv-handson/05-agent-development.md) | ~2시간 | KA + Genie Agent + Supervisor + Lakebase(선택) |

---

## 사전 요구사항

| 항목 | 확인 방법 |
|------|----------|
| Databricks Workspace (Premium 이상) | 워크스페이스 URL 접속 후 로그인 |
| 서버리스 컴퓨트 접근 권한 | 노트북에서 "Serverless" 선택 가능 |
| Genie Code Agent Mode | 노트북 우측 상단 Genie Code 아이콘 확인 |

> **처음 Databricks를 접하시는 분**: 모든 작업을 Genie Code로 자연어 프롬프트만으로 진행합니다. SQL이나 Python을 직접 작성할 필요가 없습니다.

---

## 참고 리소스

| 주제 | URL |
|------|-----|
| Genie Code + AI Dev Kit 구성 가이드 | [github.com/SimyungYang/genie-code-ai-dev-kit](https://github.com/SimyungYang/genie-code-ai-dev-kit) |
| AI Dev Kit GitHub | [github.com/databricks-solutions/ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) |
| Genie Code 공식 문서 | [docs.databricks.com/genie-code](https://docs.databricks.com/en/genie-code/index.html) |
