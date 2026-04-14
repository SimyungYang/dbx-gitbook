# Genie Code에 AI Dev Kit 구성하기

> **소요 시간**: ~30분 | **사전 조건**: Section 2 AI Builder App 배포 완료
>
> **참조**: [genie-code-ai-dev-kit 전체 가이드](https://github.com/SimyungYang/genie-code-ai-dev-kit)

---

## 왜 이 구성이 필요한가?

Genie Code는 **각 제품 영역 안에서는** 강력하지만, **크로스 프로덕트 작업**은 할 수 없습니다.

| 요청 | Genie Code 단독 | Genie Code + AI Dev Kit |
|------|----------------|----------------------|
| "이 테이블로 Genie Space 만들어줘" | ❌ (질의만 가능, 생성 불가) | ✅ `manage_genie` |
| "대시보드 만들고 Job 스케줄 걸어줘" | ❌ (각각 다른 UI에서) | ✅ 한 대화에서 동시에 |
| "Knowledge Assistant 만들어줘" | ❌ 기능 없음 | ✅ `manage_ka` |
| "Supervisor Agent 구성해줘" | ❌ 기능 없음 | ✅ `manage_mas` |
| "Lakebase DB 만들어줘" | ❌ 기능 없음 | ✅ `manage_lakebase_database` |

> **핵심**: Genie Code = "Single Product Area" / AI Dev Kit = **"Across Products"**

> 📸 **[스크린샷]**: Genie Code에서 "Genie Space 만들어줘" → "죄송합니다, 그 기능은..." 응답 화면

---

## 구성 아키텍처

```
┌──────────────────────────────────────────────────┐
│                  Genie Code                       │
│  ┌────────────────┐  ┌─────────────────────────┐ │
│  │ Built-in (OOB)  │  │ MCP: mcp-ai-dev-kit App │ │
│  │ - SQL 실행      │  │ - Genie Space 생성/관리   │ │
│  │ - Genie 질의    │  │ - 대시보드 생성           │ │
│  │ - Vector Search │  │ - Job 스케줄링           │ │
│  │ - UC Functions  │  │ - KA/MAS/Apps 관리       │ │
│  └────────────────┘  │ - Lakebase/VS 관리       │ │
│                      │ - UC 권한 관리            │ │
│  ┌────────────────┐  │   ... 44개 도구           │ │
│  │ Workspace Skills│  └─────────────────────────┘ │
│  │ (자동 로딩)     │                              │
│  └────────────────┘                              │
└──────────────────────────────────────────────────┘
```

Genie Code를 확장하는 **두 가지 경로**:

| 경로 | 방식 | 설정 |
|------|------|------|
| **MCP Tools** | App 배포 → Settings에서 서버 추가 | 수동 (이 가이드) |
| **Skills** | `/Workspace/.assistant/skills/`에 배포 | 자동 로딩 |

---

## Step 1: Genie Code에서 MCP 서버 연결

> **사전 조건**: Section 2에서 `mcp-ai-dev-kit` 앱이 RUNNING 상태여야 합니다.

1. Databricks Workspace 접속
2. 아무 노트북 열기
3. 우측 상단 **Genie Code 아이콘** 클릭
4. 하단에서 **Agent Mode** 확인
5. 하단 ⚙️ **Settings** 클릭
6. **MCP Servers** → **"+ Add Server"**
7. 드롭다운에서 **`mcp-ai-dev-kit`** 선택
8. **Save**

> 📸 **[스크린샷]**: Settings → MCP Servers → "+ Add Server" 클릭
> 📸 **[스크린샷]**: 드롭다운에서 mcp-ai-dev-kit 선택
> 📸 **[스크린샷]**: Save 후 서버 연결 완료 (도구 목록 표시)

---

## Step 2: 도구 20개 제한 — 필요한 것만 켜기

AI Dev Kit은 44개 도구를 제공하지만, Genie Code는 **전체 MCP 서버에 걸쳐 최대 20개**만 활성화 가능합니다.

### 선택 전략

> Genie Code가 **이미 잘 하는 것은 OFF**, AI Dev Kit **고유 기능만 ON**

| OFF 권장 (OOB와 중복) | 이유 |
|---------------------|------|
| `ask_genie` | Genie Code OOB Genie Space MCP가 처리 |
| `query_vs_index` | Genie Code OOB Vector Search MCP가 처리 |
| `execute_sql` | Genie Code OOB DBSQL MCP가 처리 |

### 워크샵 권장 프로필: 올라운드 (15개)

이 워크샵에서는 데이터 파이프라인 + 대시보드 + 에이전트를 모두 다루므로:

| # | 도구 | 용도 |
|---|------|------|
| 1 | `manage_genie` | Genie Space 생성/수정/테이블 연결 |
| 2 | `manage_mas` | Supervisor Agent 생성/관리 |
| 3 | `manage_ka` | Knowledge Assistant 생성/관리 |
| 4 | `manage_dashboard` | 대시보드 생성 (크로스 프로덕트) |
| 5 | `manage_jobs` | Job 생성/스케줄/관리 |
| 6 | `manage_job_runs` | Job 실행/모니터링 |
| 7 | `manage_pipeline` | SDP 파이프라인 관리 |
| 8 | `manage_app` | Databricks App 관리 |
| 9 | `manage_lakebase_database` | Lakebase DB 생성/관리 |
| 10 | `manage_serving_endpoint` | Model Serving 배포 |
| 11 | `execute_code` | 클러스터에서 Python/Scala 실행 |
| 12 | `manage_uc_objects` | 카탈로그/스키마/테이블 CRUD |
| 13 | `manage_uc_grants` | 권한 GRANT/REVOKE |
| 14 | `manage_vs_index` | Vector Search 인덱스 생성 |
| 15 | `manage_workspace_files` | 워크스페이스 파일 관리 |

> 📸 **[스크린샷]**: Settings → mcp-ai-dev-kit → 도구별 ON/OFF 토글 화면

### 다른 업무 프로필

<details>
<summary>데이터 엔지니어 프로필 (파이프라인 + Job 중심)</summary>

`manage_pipeline`, `manage_jobs`, `manage_job_runs`, `execute_code`, `execute_sql`, `manage_uc_objects`, `manage_uc_grants`, `manage_dashboard`, `manage_workspace_files`, `manage_cluster`, `manage_sql_warehouse`, `manage_genie`, `get_table_stats_and_schema`, `list_compute`, `manage_pipeline_run`

</details>

<details>
<summary>AI/ML 엔지니어 프로필 (Agent Bricks + Serving 중심)</summary>

`manage_mas`, `manage_ka`, `manage_genie`, `manage_serving_endpoint`, `manage_vs_index`, `manage_vs_endpoint`, `manage_vs_data`, `execute_code`, `manage_uc_objects`, `manage_uc_grants`, `manage_app`, `manage_jobs`, `manage_job_runs`, `manage_workspace_files`, `manage_lakebase_database`

</details>

<details>
<summary>데이터 분석가 프로필 (대시보드 + Genie 중심)</summary>

`manage_dashboard`, `manage_genie`, `execute_sql`, `execute_sql_multi`, `get_table_stats_and_schema`, `manage_uc_objects`, `manage_jobs`, `manage_job_runs`, `manage_uc_grants`, `manage_workspace_files`, `execute_code`, `manage_ka`, `manage_mas`, `manage_sql_warehouse`, `list_compute`

</details>

> 💡 **꿀팁**: 작업 전에 Genie Code에게 물어보세요:
> ```
> SDP 파이프라인 생성을 위해 활성화하면 도움 될 MCP 도구를 알려줘
> ```

---

## Step 3: Skills를 Workspace에 배포

Skills는 MCP와 달리 **설정 없이 자동 로딩**됩니다. Agent Mode에서 문맥에 맞는 Skill이 자동으로 활성화됩니다.

### 배포 방법

```bash
# AI Dev Kit Skills 소스 클론
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

> 📸 **[스크린샷]**: 배포 완료 후 `databricks workspace list` 결과 — Skills 목록

### Skills 확인

Genie Code에서:
```
현재 사용 가능한 Skills 목록을 보여줘
```

> 📸 **[스크린샷]**: Genie Code Settings → Skills 탭

---

## Step 4: Genie Space 접근 권한 부여 (선택)

Genie Agent를 구성할 때 MCP 서버가 Genie Space에 접근해야 합니다:

```bash
SPACE_ID="<genie_space_id>"
TOKEN=$(databricks auth token | jq -r .access_token)
HOST=$(databricks auth env | jq -r .env.DATABRICKS_HOST)
SP_CLIENT_ID=$(databricks apps get mcp-ai-dev-kit -o json | jq -r .service_principal_client_id)

curl -X PATCH "$HOST/api/2.0/permissions/genie/$SPACE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"access_control_list\": [{
    \"service_principal_name\": \"$SP_CLIENT_ID\",
    \"permission_level\": \"CAN_RUN\"
  }]}"
```

---

## Step 5: 테스트

### 테스트 1: Skills 자동 로딩 확인

```
Spark Declarative Pipeline으로 medallion 아키텍처를 구성하려면 어떻게 해야 돼?
```

> Genie Code가 SDP 관련 Skill을 자동으로 참조하여 답변하면 성공

### 테스트 2: MCP 도구 — Genie Space 생성

```
@lge_smart_tv.gold.daily_viewing_summary와 @lge_smart_tv.gold.content_popularity 테이블로
"Smart TV 시청 분석" Genie Space를 만들어줘.

General Instructions:
- 날짜 미지정 시 최근 7일
- 비율은 소수점 1자리
```

> Genie Code가 `manage_genie` MCP 도구를 호출하여 Genie Space를 생성하면 성공

> 📸 **[스크린샷]**: Genie Code에서 MCP 도구 호출 로그 — "Using tool: manage_genie"

### 테스트 3: 크로스 프로덕트 오케스트레이션

```
다음 3가지를 한번에 해줘:
1. gold 스키마 테이블들로 Genie Space 생성
2. 같은 데이터로 매출 추이 대시보드 만들기
3. 매일 오전 6시에 데이터를 리프레시하는 Job 설정
```

> 한 대화에서 Genie Space + 대시보드 + Job이 모두 생성되면 성공

> 📸 **[스크린샷]**: 크로스 프로덕트 작업 완료 — Genie Space, 대시보드, Job 각각 생성 확인

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| MCP 서버가 Settings에 안 보임 | 앱 이름이 `mcp-`로 시작 안 함 | 앱 이름 확인, `mcp-` 접두사 필수 |
| "도구 제한 초과" 경고 | 20개 초과 활성화 | 불필요한 도구 OFF |
| `manage_genie` 호출 실패 | 서비스 프린시펄 권한 부족 | Step 4 Genie Space 권한 부여 |
| Skills가 로딩 안 됨 | 경로가 틀림 | `/Workspace/.assistant/skills/` 확인 |
| Agent Mode가 아님 | Chat Mode 선택됨 | MCP/Skills는 Agent Mode에서만 동작 |

---

## 핵심 정리

| 구성 요소 | 역할 | 설정 방식 |
|----------|------|----------|
| **Genie Code OOB** | SQL 실행, Genie 질의, Vector Search | 설정 불필요 |
| **MCP (AI Dev Kit)** | 크로스 프로덕트 작업 44개 도구 | 수동 — Settings에서 서버 추가 + 도구 선택 |
| **Skills** | 도메인 전문 지식 자동 로딩 | 자동 — Workspace에 배포하면 끝 |

---

## 다음 단계

구성이 완료되었으면 **[Section 4: LG Smart TV E2E 핸즈온](../section-4-smart-tv-handson/02-data-generation.md)**으로 이동하여 실제 데이터 플랫폼을 구축합니다.
