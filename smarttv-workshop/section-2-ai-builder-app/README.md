# AI Builder App 배포 핸즈온

> **소요 시간**: ~30분 | **핵심**: Databricks Apps에 AI Dev Kit MCP 서버를 배포하기

---

## 개요

AI Dev Kit의 MCP 서버를 **Databricks App**으로 배포하면, Genie Code에서 MCP 도구로 연결하여 크로스 프로덕트 작업이 가능해집니다.

이 핸즈온에서는 git clone부터 앱 배포, 권한 설정까지 전 과정을 다룹니다.

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

### Databricks CLI 설치 확인

```bash
databricks --version
```

설치가 안 되어 있다면:
```bash
# macOS
brew install databricks

# pip (최신 Databricks SDK)
pip install databricks-sdk
```

### 인증

```bash
databricks auth login --host https://<your-workspace-url>
databricks current-user me
```

> 📸 **[스크린샷]**: `databricks current-user me` 실행 결과 — 사용자 정보 확인

### jq 설치 (JSON 파싱용)

```bash
# macOS
brew install jq

# 확인
jq --version
```

---

## Step 2: 레포 클론

```bash
git clone https://github.com/databricks-solutions/ai-dev-kit.git
cd ai-dev-kit
```

> 📸 **[스크린샷]**: git clone 완료 후 디렉토리 구조

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

```bash
# 현재 사용자의 워크스페이스 경로 설정
DBUSER=$(databricks current-user me | jq -r .userName)
APP_PATH="/Workspace/Users/$DBUSER/mcp-ai-dev-kit-app"

# 디렉토리 생성
databricks workspace mkdirs "$APP_PATH"

# 파일 업로드 (app.yaml, main.py, requirements.txt)
for f in app/main.py app/app.yaml app/requirements.txt; do
  databricks workspace import "$APP_PATH/$(basename $f)" \
    --file "$f" --format RAW --overwrite
done

# 배포
databricks apps deploy mcp-ai-dev-kit --source-code-path "$APP_PATH"

# 상태 확인
databricks apps get mcp-ai-dev-kit
```

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

### 5-3. 카탈로그 권한 (SQL Warehouse에서 실행)

```sql
GRANT ALL PRIVILEGES ON CATALOG lge_smart_tv TO `<sp_client_id>`;
```

### 5-4. SQL Warehouse 사용 권한

```bash
WH_ID="<your_warehouse_id>"
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

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| 앱 상태 `FAILED` | requirements.txt 의존성 오류 | `databricks apps logs mcp-ai-dev-kit`로 로그 확인 |
| Genie Code에서 안 보임 | 앱 이름이 `mcp-`로 시작 안 함 | 앱 삭제 후 `mcp-` 접두사로 재생성 |
| 권한 오류 | 서비스 프린시펄 권한 부족 | Step 5 재실행 |
| 도구가 20개 초과 | MCP 도구 제한 | Settings에서 필요한 도구만 ON |

---

## 다음 단계

앱 배포가 완료되면 **[Section 3: Genie Code에 AI Dev Kit 구성하기](../section-3-genie-code-aidevkit/README.md)**로 이동하여 Genie Code와 연결합니다.
