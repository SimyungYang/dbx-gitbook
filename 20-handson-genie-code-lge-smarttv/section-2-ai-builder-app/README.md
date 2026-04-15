# AI Builder App 배포 핸즈온

> **소요 시간**: ~30분 | **핵심**: Databricks Apps에 AI Dev Kit MCP 서버를 배포하기

---

## 이 모듈에서 사용하는 Databricks 기능

| 기능 | 설명 | 공식 문서 |
|------|------|----------|
| **Databricks Apps** | Databricks 워크스페이스 안에서 웹 애플리케이션(FastAPI, Streamlit 등)을 배포·관리하는 플랫폼입니다. 앱마다 서비스 프린시펄(Service Principal)이 자동 생성되어 권한 관리가 됩니다. | [docs](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html) |
| **MCP (Model Context Protocol)** | AI 도구가 외부 시스템과 통신하는 표준 프로토콜입니다. MCP 서버를 앱으로 배포하면 Genie Code에서 추가 도구를 사용할 수 있습니다. | [spec](https://modelcontextprotocol.io/) |
| **Service Principal** | 사람이 아닌 **앱/자동화 프로세스 전용 계정**입니다. 앱이 API를 호출할 때 이 계정의 권한으로 동작합니다. 앱이 사용자 없이도 24시간 자동으로 Databricks 리소스에 접근해야 하기 때문에 별도 계정이 필요합니다. | [docs](https://docs.databricks.com/en/admin/users-groups/service-principals.html) |
| **Databricks CLI** | 터미널에서 Databricks 리소스를 관리하는 명령줄 도구입니다. `databricks apps create`, `databricks apps deploy` 등의 명령을 사용합니다. | [docs](https://docs.databricks.com/en/dev-tools/cli/index.html) |

## 개요

AI Dev Kit의 MCP 서버를 **Databricks App**으로 배포하면, Genie Code에서 MCP 도구로 연결하여 크로스 프로덕트 작업(Genie Space 생성, 대시보드 생성, Job 스케줄링 등)이 가능해집니다.

이 핸즈온에서는 git clone부터 앱 배포, 권한 설정까지 전 과정을 다룹니다.

### 전체 흐름 미리보기

```
Step 1: 사전 준비 (CLI 설치 + 인증)
  ↓
Step 2: AI Dev Kit 소스 코드 다운로드 (git clone)
  ↓
Step 3: Databricks에 앱 생성 (mcp-ai-dev-kit)
  ↓
Step 4: 소스 코드를 Workspace에 업로드 → 앱 배포
  ↓
Step 5: 앱의 서비스 프린시펄에 권한 부여
  ↓
Step 6: 배포 성공 확인
```

> ⚠️ **모든 명령어는 로컬 터미널(macOS Terminal, iTerm, VS Code 터미널 등)에서 실행합니다.** Databricks 노트북이 아닙니다.

---

## Lakebase 미사용 시 제약사항

| 항목 | Lakebase 사용 시 | Lakebase 미사용 시 |
|------|----------------|-----------------|
| OLTP 기능 | PostgreSQL 호환 CRUD | 사용 불가 |
| 에이전트 세션 저장 | Lakebase에 저장 | Delta 테이블 대체 (제한적) |
| 실시간 피드백 저장 | 즉시 저장 | 배치 저장 |
| Apps 상태 관리 | Lakebase로 관리 | 메모리/파일 기반 (앱 재시작 시 초기화) |

> 💡 **워크샵에서는 Lakebase 없이 진행 가능합니다.** 에이전트 세션 저장 등 OLTP 기능만 제한됩니다.

---

## Step 1: 사전 준비

### 필수 도구 설치 확인

아래 3가지 도구가 로컬 터미널에 설치되어 있어야 합니다:

```bash
# 1) Git — 소스 코드 다운로드에 필요
git --version
# → "git version 2.x.x" 가 나오면 OK
# 안 나오면: brew install git (macOS) 또는 https://git-scm.com/downloads

# 2) Databricks CLI — 앱 배포에 필요
databricks --version
# → "Databricks CLI v0.x.x" 가 나오면 OK
# 안 나오면 아래 중 하나로 설치:
```

Databricks CLI가 없다면:
```bash
# 방법 1: Homebrew (macOS 권장)
brew install databricks

# 방법 2: 공식 설치 스크립트
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# 방법 3: pip
pip install databricks-cli
```

> 💡 `pip install databricks-sdk`는 Python SDK이며, CLI와 다릅니다. 터미널 명령어(`databricks apps create` 등)를 사용하려면 **Databricks CLI**가 필요합니다.

### 인증

```bash
databricks auth login --host https://<your-workspace-url>
databricks current-user me
```

> **워크스페이스 URL 형식**: `https://<workspace-id>.azuredatabricks.net` (Azure) 또는 `https://<workspace-id>.cloud.databricks.com` (AWS). 브라우저에서 Databricks 워크스페이스에 접속했을 때 주소창에 표시되는 URL을 그대로 사용하세요.

> 📸 **[스크린샷]**: `databricks current-user me` 실행 결과 — 사용자 정보 확인

### jq 설치 (JSON 파싱용)

```bash
# macOS
brew install jq

# 확인
jq --version
```

---

## Step 2: AI Dev Kit 소스 코드 다운로드

로컬 터미널에서 AI Dev Kit GitHub 레포지토리를 클론(복사)합니다:

```bash
# 원하는 작업 디렉토리로 이동 (예: 홈 디렉토리)
cd ~

# AI Dev Kit 소스 코드 다운로드
git clone https://github.com/databricks-solutions/ai-dev-kit.git

# ⚠️ 중요: 반드시 클론한 디렉토리 안으로 이동
cd ai-dev-kit
```

> ⚠️ **`cd ai-dev-kit`을 반드시 실행하세요.** 이후 Step 4에서 `app/main.py`, `app/app.yaml` 등의 파일을 참조하는데, 현재 디렉토리가 `ai-dev-kit/`이 아니면 "파일을 찾을 수 없습니다" 에러가 발생합니다.

클론 후 디렉토리 구조를 확인합니다:

```bash
ls app/
# 기대 결과: app.yaml  main.py  requirements.txt (등)
```

> 📸 **[스크린샷]**: git clone 완료 → `ls app/` 결과 확인

---

## Step 3: 앱 생성

> **중요**: 앱 이름은 반드시 `mcp-`로 시작해야 Genie Code에서 인식됩니다.

```bash
databricks apps create mcp-ai-dev-kit \
  --description "AI Dev Kit MCP Server for Genie Code"
```

> 📸 **[스크린샷]**: 앱 생성 결과 — app_url, service_principal 등 출력

---

## Step 4: 소스 코드 업로드 & 배포

> **현재 디렉토리 확인**: 이 단계를 실행하기 전에 `pwd`를 실행하여 `ai-dev-kit` 디렉토리 안에 있는지 확인하세요.

아래 스크립트를 **한 번에 복사하여 터미널에 붙여넣기**하면 됩니다:

```bash
# 현재 사용자의 워크스페이스 경로 설정
DBUSER=$(databricks current-user me | jq -r .userName)
APP_PATH="/Workspace/Users/$DBUSER/mcp-ai-dev-kit-app"
echo "배포 경로: $APP_PATH"

# Workspace에 디렉토리 생성
databricks workspace mkdirs "$APP_PATH"

# 3개 파일 업로드 (main.py, app.yaml, requirements.txt)
for f in app/main.py app/app.yaml app/requirements.txt; do
  echo "업로드 중: $f"
  databricks workspace import "$APP_PATH/$(basename $f)" \
    --file "$f" --format RAW --overwrite
done
echo "✅ 파일 업로드 완료"

# 앱 배포 시작
databricks apps deploy mcp-ai-dev-kit --source-code-path "$APP_PATH"
echo "⏳ 배포 진행 중... 1~2분 소요됩니다."
```

배포 후 상태를 확인합니다:

```bash
# 상태 확인 (RUNNING이 나올 때까지 반복)
databricks apps get mcp-ai-dev-kit
```

> **기대 결과**: `status`가 `RUNNING`이면 성공입니다. `DEPLOYING`이면 1~2분 더 기다린 후 다시 확인하세요. `FAILED`이면 [트러블슈팅](#트러블슈팅) 섹션을 참조하세요.

> 📸 **[스크린샷]**: 배포 결과 — status: RUNNING 확인

---

## Step 5: 서비스 프린시펄 권한 부여

앱이 워크스페이스 리소스에 접근하려면 서비스 프린시펄에 권한이 필요합니다.

### 5-1. 서비스 프린시펄 ID 확인

```bash
SP_CLIENT_ID=$(databricks apps get mcp-ai-dev-kit -o json | jq -r .service_principal_client_id)
SP_ID=$(databricks apps get mcp-ai-dev-kit -o json | jq -r .service_principal_id)
echo "Client ID: $SP_CLIENT_ID"
echo "SP ID: $SP_ID"
```

### 5-2. 엔타이틀먼트 부여

```bash
databricks api patch /api/2.0/preview/scim/v2/ServicePrincipals/$SP_ID --json '{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [{"op": "add", "value": {
    "entitlements": [
      {"value": "allow-cluster-create"},
      {"value": "workspace-access"},
      {"value": "databricks-sql-access"}
    ]
  }}]
}'
```

### 5-3. 카탈로그 권한 부여

> **이 SQL은 Databricks 노트북 또는 SQL Editor에서 실행합니다** (로컬 터미널이 아닙니다).
> Databricks 왼쪽 사이드바 → **SQL Editor** 클릭 → 아래 SQL을 붙여넣고 실행하세요.

```sql
-- <sp_client_id>를 위 5-1에서 확인한 Client ID로 교체
GRANT ALL PRIVILEGES ON CATALOG smart_tv TO `<sp_client_id>`;
```

> 💡 **Client ID 확인**: 위 Step 5-1에서 출력된 `Client ID` 값을 `<sp_client_id>` 자리에 넣으세요.

### 5-4. SQL Warehouse 사용 권한

> **`<your_warehouse_id>` 찾는 방법**: Databricks 왼쪽 사이드바 → **SQL Warehouses** → 사용할 웨어하우스 클릭 → URL 주소창에서 `/sql/warehouses/` 뒤의 문자열이 ID입니다.
> 
> 또는 터미널에서 `databricks warehouses list -o json | jq '.[].id'`로 확인할 수 있습니다.

```bash
WH_ID="<your_warehouse_id>"  # ← 위에서 확인한 Warehouse ID로 교체
TOKEN=$(databricks auth token | jq -r .access_token)
HOST=$(databricks auth env | jq -r .env.DATABRICKS_HOST)

curl -X PATCH "$HOST/api/2.0/permissions/warehouses/$WH_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"access_control_list\": [{
    \"service_principal_name\": \"$SP_CLIENT_ID\",
    \"permission_level\": \"CAN_USE\"
  }]}"
```

> 📸 **[스크린샷]**: 권한 부여 후 확인 — SQL Warehouse Permissions 화면

---

## Step 6: 배포 확인

```bash
# 앱 상태 확인
databricks apps get mcp-ai-dev-kit

# 앱 URL 확인
databricks apps get mcp-ai-dev-kit -o json | jq -r .url
```

앱이 `RUNNING` 상태이면 성공입니다!

> 📸 **[스크린샷]**: 앱 상태 RUNNING + URL 확인

---

## 배포 확인 프롬프트

앱 배포가 완료되면, Genie Code에서 아래 프롬프트로 상태를 확인할 수 있습니다:

```
mcp-ai-dev-kit 앱이 정상적으로 배포됐는지 확인해줘.
앱 상태, URL, 서비스 프린시펄 ID를 알려줘.
```

> **`<your_warehouse_id>` 찾는 방법**: Databricks 왼쪽 사이드바 → "SQL Warehouses" → 사용할 웨어하우스 클릭 → URL에서 `/sql/warehouses/` 뒤의 문자열이 ID입니다. 또는 Genie Code에 이렇게 물어보세요:
> ```
> 내가 사용할 수 있는 SQL Warehouse 목록과 각 ID를 알려줘.
> ```

---

## 트러블슈팅

### 배포 시 자주 발생하는 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| 앱 상태 `FAILED` | requirements.txt 의존성 오류 | `databricks apps logs mcp-ai-dev-kit`로 로그 확인 |
| Genie Code에서 안 보임 | 앱 이름이 `mcp-`로 시작 안 함 | 앱 삭제 후 `mcp-` 접두사로 재생성 |
| 권한 오류 | 서비스 프린시펄 권한 부족 | Step 5 재실행 |
| 도구가 20개 초과 | MCP 도구 제한 | Settings에서 필요한 도구만 ON |

### MCP 서버 운영 중 문제 (Genie Code에서 사용 시)

| 문제 | 증상 | 원인 | 해결 |
|------|------|------|------|
| **MCP 도구 호출 타임아웃** | "Tool call timed out" 또는 응답 없음 | 앱이 슬립 상태이거나 과부하 | 앱 상태 확인 후 재시작: `databricks apps stop mcp-ai-dev-kit && databricks apps start mcp-ai-dev-kit` |
| **MCP 도구 호출 실패** | "Error calling tool: manage_genie" | 서비스 프린시펄 권한 부족 또는 앱 크래시 | 1) `databricks apps logs mcp-ai-dev-kit`로 에러 확인 2) 권한 재부여 3) 앱 재배포 |
| **앱이 갑자기 CRASHED** | Settings에서 서버가 빨간색 | 메모리 초과 또는 내부 오류 | `databricks apps get mcp-ai-dev-kit`로 상태 확인 후 재배포: `databricks apps deploy mcp-ai-dev-kit --source-code-path "$APP_PATH"` |
| **새 도구가 반영 안 됨** | AI Dev Kit 업데이트 후 도구 목록이 그대로 | 앱 소스 코드가 이전 버전 | git pull → 소스 재업로드 → 재배포 |
| **Genie Space 생성 시 권한 에러** | `manage_genie` 호출 후 403 | 서비스 프린시펄에 Genie Space CAN_MANAGE 권한 없음 | [Section 3 Step 4](../section-3-ai-tools-setup/genie-code-aidevkit.md) 권한 부여 스크립트 실행 |
| **SQL 실행 도구 에러** | `execute_sql` 호출 시 "Warehouse not found" | 서비스 프린시펄에 SQL Warehouse 접근 권한 없음 | Step 5의 SQL Warehouse 권한 부여 재실행 |

### MCP 서버 상태 진단 프롬프트

문제가 발생하면 Genie Code에서 아래 프롬프트로 진단할 수 있습니다:

```
MCP 서버 상태를 진단해줘:
1. mcp-ai-dev-kit 앱이 RUNNING 상태인지
2. 현재 활성화된 MCP 도구 목록
3. 각 도구가 정상 응답하는지 간단한 테스트 (manage_uc_objects로 카탈로그 목록 조회)
```

### MCP 앱 재배포 방법

문제가 해결되지 않으면 앱을 재배포합니다:

```bash
# 1. 최신 소스 가져오기
cd ai-dev-kit && git pull

# 2. 소스 재업로드
DBUSER=$(databricks current-user me | jq -r .userName)
APP_PATH="/Workspace/Users/$DBUSER/mcp-ai-dev-kit-app"
for f in app/main.py app/app.yaml app/requirements.txt; do
  databricks workspace import "$APP_PATH/$(basename $f)" \
    --file "$f" --format RAW --overwrite
done

# 3. 재배포
databricks apps deploy mcp-ai-dev-kit --source-code-path "$APP_PATH"

# 4. 상태 확인 (RUNNING이 될 때까지 대기)
watch databricks apps get mcp-ai-dev-kit
```

---

## 다음 단계

앱 배포가 완료되면 **[Section 3: Genie Code에 AI Dev Kit 연결](../section-3-ai-tools-setup/genie-code-aidevkit.md)**으로 이동하여 MCP 서버를 Genie Code에 연결하고 도구를 활성화합니다.

> Section 3에는 AI Gateway(비용 관리), Claude Code(참고용) 소개도 포함되어 있지만, 실습에서 필수적인 것은 **[Genie Code + AI Dev Kit 연결](../section-3-ai-tools-setup/genie-code-aidevkit.md)** 페이지입니다.
