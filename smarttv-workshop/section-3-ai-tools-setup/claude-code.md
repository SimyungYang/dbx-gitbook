# Claude Code 사용하기

> AI Gateway를 통해 비용을 통제할 수 있는 환경이 갖춰졌으니, 이제 **Claude Code**를 설치하고 사용합니다.

---

## Claude Code란?

Anthropic의 CLI 기반 AI 코딩 어시스턴트입니다. 터미널에서 자연어로 코드를 생성하고, 파일을 수정하고, 명령을 실행합니다.

| | Genie Code | **Claude Code** |
|---|---|---|
| 실행 환경 | Databricks 워크스페이스 안 | **로컬 터미널 (VS Code, iTerm 등)** |
| 데이터 접근 | Unity Catalog 직접 접근 | AI Dev Kit MCP 통해 접근 |
| 적합한 작업 | 노트북 기반 EDA, 대시보드, 파이프라인 | **프로젝트 단위 개발, CI/CD, 멀티파일 작업** |
| 비용 | Databricks 컴퓨트 | **AI Gateway 경유 → DBU 과금** |

> 💡 **핵심**: Genie Code는 "Databricks 안에서", Claude Code는 "Databricks 밖에서" 사용합니다. 둘 다 AI Gateway를 통해 비용이 관리됩니다.

---

## Step 1: 설치

```bash
# Node.js 18+ 필요
npm install -g @anthropic-ai/claude-code
```

설치 확인:
```bash
claude --version
```

> 📸 **[스크린샷]**: `claude --version` 실행 결과

---

## Step 2: Databricks 연결 (AI Gateway 경유)

Claude Code가 Databricks AI Gateway를 통해 Foundation Model API를 사용하도록 설정합니다:

```bash
# Databricks CLI 인증 확인
databricks auth login --host https://<your-workspace-url>
databricks current-user me
```

> 📸 **[스크린샷]**: Databricks CLI 인증 성공 화면

---

## Step 3: AI Dev Kit 설치

Claude Code에 Databricks AI Dev Kit을 설치하면, **44개 MCP 도구 + 25개 Skills**가 추가됩니다:

```bash
bash <(curl -sL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/install.sh)
```

설치 완료 후:
```bash
claude
```

> 📸 **[스크린샷]**: AI Dev Kit 설치 완료 메시지
> 📸 **[스크린샷]**: `claude` 실행 후 AI Dev Kit 도구 목록 표시

---

## Step 4: Claude Code 사용 예시

### 예시 1: 테이블 탐색

```
lge_smart_tv 카탈로그에 어떤 테이블이 있는지 보여줘
```

### 예시 2: 데이터 분석

```
lge_smart_tv.gold.daily_viewing_summary에서 
지역별 평균 시청 시간을 분석해줘
```

### 예시 3: 크로스 프로덕트 작업 (AI Dev Kit 기능)

```
gold 스키마 테이블로 Genie Space를 만들고,
매출 추이 대시보드도 만들어줘.
매일 6시에 리프레시하는 Job도 설정해줘.
```

> 이 크로스 프로덕트 작업은 Claude Code + AI Dev Kit에서만 가능합니다. Genie Code 단독으로는 불가.

> 📸 **[스크린샷]**: Claude Code에서 크로스 프로덕트 작업 실행 모습

---

## Genie Code vs Claude Code — 언제 무엇을?

| 상황 | 추천 도구 |
|------|----------|
| 노트북에서 빠른 EDA | **Genie Code** |
| 대시보드 UI에서 위젯 생성 | **Genie Code** |
| Pipeline Editor에서 SDP 코드 | **Genie Code** |
| 프로젝트 폴더 전체 작업 (여러 파일) | **Claude Code** |
| Git 연동 + CI/CD | **Claude Code** |
| 한 대화에서 Genie Space + 대시보드 + Job | **둘 다** (AI Dev Kit 필요) |

> 💡 **워크샵에서는 주로 Genie Code를 사용합니다.** Claude Code는 "이런 것도 된다"를 보여주는 데모용입니다.

---

## 비용 관리 확인

Claude Code 사용 후 비용을 확인하려면:

```sql
-- AI Gateway를 통한 Claude Code 사용량
SELECT
  user_identity.email,
  DATE(request_time) AS date,
  COUNT(*) AS requests,
  SUM(usage.total_tokens) AS tokens
FROM system.serving.served_entities_usage
WHERE request_time >= CURRENT_DATE - INTERVAL 1 DAY
GROUP BY 1, 2
ORDER BY tokens DESC
```

> 📸 **[스크린샷]**: 사용량 조회 결과

---

## 주요 문서 링크

| 주제 | URL |
|------|-----|
| Claude Code 공식 문서 | [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code/overview) |
| AI Dev Kit GitHub | [github.com/databricks-solutions/ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) |
| AI Dev Kit 설치 가이드 | [github.com/databricks-solutions/ai-dev-kit#installation](https://github.com/databricks-solutions/ai-dev-kit#installation) |

---

## 다음 단계

- **[AI Dev Kit 설치 상세](ai-dev-kit-setup.md)** — MCP 서버 앱 배포, Skills 워크스페이스 배포
