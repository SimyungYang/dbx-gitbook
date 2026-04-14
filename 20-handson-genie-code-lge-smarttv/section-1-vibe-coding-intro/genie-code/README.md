# Genie Code 완전 가이드

Databricks 내장 AI 코딩 에이전트 **Genie Code**를 "잘" 쓰는 방법을 배웁니다.

> 핵심 수치: 실제 데이터 작업에서 **77.1% 성공률** (범용 코딩 AI 32.1% 대비 2.4배)

## 이 가이드를 읽기 전에 — 용어 정리

| 용어 | 설명 |
|------|------|
| **Genie Code** | Databricks 노트북/대시보드/파이프라인 에디터 안에 내장된 AI 코딩 어시스턴트. `Cmd+I`로 호출합니다. |
| **Agent Mode** | Genie Code의 실행 모드. 코드를 직접 생성 → 실행 → 결과 검증 → 에러 수정까지 자동으로 수행합니다. |
| **Unity Catalog (UC)** | Databricks의 통합 데이터 거버넌스 플랫폼. 카탈로그 > 스키마 > 테이블 3단계로 데이터를 관리합니다. |
| **MCP (Model Context Protocol)** | AI 도구가 외부 시스템과 통신하는 표준 프로토콜. Genie Code에 MCP 서버를 연결하면 기능이 확장됩니다. |
| **Skills** | Genie Code가 참고하는 도메인 전문 지식 파일. Workspace에 배포하면 자동으로 로딩됩니다. |
| **SDP (Spark Declarative Pipelines)** | 이전 이름 DLT(Delta Live Tables). 선언적으로 데이터 파이프라인을 정의하는 Databricks 기능입니다. |
| **Serverless Compute** | Databricks가 관리하는 서버리스 컴퓨트. 클러스터 생성/관리 없이 코드를 바로 실행합니다. |
| **AI/BI Dashboard** | SQL 기반으로 KPI 카운터, 차트, 필터를 조합한 비즈니스 대시보드를 만드는 기능입니다. |
| **Genie Space** | 비개발자가 자연어로 질문하면 AI가 SQL을 생성하여 데이터를 분석하는 공간입니다. |
| **Agent Bricks** | 코드 없이 AI 에이전트(문서 Q&A, 데이터 분석, 오케스트레이션)를 생성하는 Databricks 기능입니다. |
| **Vector Search** | 텍스트를 벡터로 변환하여 의미적으로 유사한 문서를 찾는 검색 엔진. RAG 에이전트의 핵심입니다. |
| **Lakebase** | Databricks에 내장된 PostgreSQL 호환 OLTP 데이터베이스. 에이전트 세션 저장 등에 사용합니다. (선택) |

## 목차

| 주제 | 내용 |
|------|------|
| [Genie Code란?](what-is-genie-code.md) | 일반 코딩 AI와 뭐가 다른지 |
| [시작하기](getting-started.md) | 모드 선택, 단축키, 슬래시 명령어 |
| [프롬프트 5대 원칙](prompt-principles.md) | 잘 쓰는 프롬프트 vs 못 쓰는 프롬프트 |
| [꿀팁 모음](tips-and-tricks.md) | 현업에서 바로 쓰는 실전 팁 20가지 |
| [상황별 프롬프트 템플릿](prompt-templates.md) | 복붙해서 바로 쓸 수 있는 프롬프트 |
| [Custom Instructions](custom-instructions.md) | 팀 규칙을 Genie Code에 심는 방법 |
| [자주 하는 실수](common-mistakes.md) | 시간 낭비를 피하는 안티패턴 |
| [보안 제한사항](security-limitations.md) | 뭐가 되고 뭐가 안 되는지 (Serverless, 권한, Rate Limit) |
| [내장 기능 둘러보기](built-in-features.md) | Skills, MCP, 슬래시 명령어 확인법 |
| [스크린샷 가이드](screenshot-guide.md) | 교육 자료 준비용 캡처 체크리스트 |
