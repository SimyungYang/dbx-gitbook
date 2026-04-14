# AI Dev Kit 설치 & 구성

> **사전 조건**: Section 2에서 AI Builder App 배포 방법을 이해한 상태

---

## AI Dev Kit이란?

Databricks의 모든 기능을 **외부 AI 도구(Claude Code, Cursor 등)**에서 사용할 수 있게 하는 MCP 서버 + Skills 패키지입니다.

| 구성 요소 | 수량 | 설명 |
|----------|------|------|
| **MCP 도구** | 44개 | Genie Space 생성, 대시보드, Job, Agent Bricks, Lakebase 등 |
| **Skills** | 25개 | SDP 패턴, ML 워크플로우, 벡터 서치 등 도메인 지식 |

---

## 설치 방법 1: Claude Code에서 사용 (로컬)

```bash
# 원라인 설치
bash <(curl -sL https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/install.sh)

# 설치 확인
claude
# → "Databricks AI Dev Kit already set up." 메시지 확인
```

> 📸 **[스크린샷]**: AI Dev Kit 설치 완료 메시지

---

## 설치 방법 2: Genie Code에서 사용 (MCP 서버 앱 배포)

Genie Code에서 AI Dev Kit을 사용하려면 **Databricks App으로 MCP 서버를 배포**해야 합니다.

> **참조**: [Section 2: AI Builder App 배포 핸즈온](../section-2-ai-builder-app/README.md)에서 앱 배포 방법을 상세히 다룹니다.

### 요약 절차

```bash
# 1. 레포 클론
git clone https://github.com/databricks-solutions/ai-dev-kit.git
cd ai-dev-kit

# 2. 앱 생성 (이름 반드시 mcp- 접두사)
databricks apps create mcp-ai-dev-kit \
  --description "AI Dev Kit MCP Server for Genie Code"

# 3. 소스 업로드 & 배포
DBUSER=$(databricks current-user me | jq -r .userName)
APP_PATH="/Workspace/Users/$DBUSER/mcp-ai-dev-kit-app"
databricks workspace mkdirs "$APP_PATH"
for f in app/main.py app/app.yaml app/requirements.txt; do
  databricks workspace import "$APP_PATH/$(basename $f)" \
    --file "$f" --format RAW --overwrite
done
databricks apps deploy mcp-ai-dev-kit --source-code-path "$APP_PATH"

# 4. 서비스 프린시펄 권한 부여
SP_ID=$(databricks apps get mcp-ai-dev-kit -o json | jq -r .service_principal_id)
SP_CLIENT_ID=$(databricks apps get mcp-ai-dev-kit -o json | jq -r .service_principal_client_id)
# (상세 권한 설정은 Section 2 참조)

# 5. 상태 확인
databricks apps get mcp-ai-dev-kit
```

> 📸 **[스크린샷]**: 앱 배포 후 status: RUNNING 확인

---

## Skills 배포 (Workspace)

Skills는 MCP와 달리 Workspace에 파일만 올리면 **자동으로 로딩**됩니다.

```bash
# AI Dev Kit Skills 클론
git clone --depth 1 https://github.com/databricks-solutions/ai-dev-kit.git /tmp/ai-dev-kit

# Skills를 Workspace에 업로드
TARGET="/Workspace/.assistant/skills"
for skill_dir in /tmp/ai-dev-kit/databricks-skills/*/; do
  skill_name=$(basename "$skill_dir")
  [ "$skill_name" = "TEMPLATE" ] && continue
  databricks workspace mkdirs "$TARGET/$skill_name"
  for f in "$skill_dir"*; do
    [ -f "$f" ] || continue
    databricks workspace import "$TARGET/$skill_name/$(basename $f)" \
      --file "$f" --format RAW --overwrite
  done
  echo "✓ $skill_name"
done

# 배포 확인
databricks workspace list /Workspace/.assistant/skills/
```

> 📸 **[스크린샷]**: Skills 배포 완료 목록

---

## 주요 문서 링크

| 주제 | URL |
|------|-----|
| AI Dev Kit GitHub | [github.com/databricks-solutions/ai-dev-kit](https://github.com/databricks-solutions/ai-dev-kit) |
| Genie Code + AI Dev Kit 구성 가이드 | [github.com/SimyungYang/genie-code-ai-dev-kit](https://github.com/SimyungYang/genie-code-ai-dev-kit) |
| Databricks Apps 문서 | [docs.databricks.com/apps](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html) |

---

## 다음 단계

- **[Genie Code + AI Dev Kit 연결](genie-code-aidevkit.md)** — MCP 서버를 Genie Code에 연결하고 테스트
