#!/usr/bin/env python3
"""
Databricks Workshop — 모든 Lab에 드래프트 콘텐츠 채우기.

전략:
1. workshop_content_data.LAB_DATA 에 정의된 Lab은 그대로 사용
2. 정의되지 않은 Lab은 카테고리별 자동 fallback 콘텐츠 생성
3. 모든 mdx 파일을 (덮어쓰기 모드로) 다시 작성

실행: python3 scripts/build-workshop-content.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from workshop_content_data import LAB_DATA  # noqa: E402
import importlib.util as _il  # noqa: E402

# Import MODULES, APPENDIX from skeleton builder by loading as module
_spec = _il.spec_from_file_location("skel", Path(__file__).resolve().parent / "build-workshop-skeleton.py")
_skel = _il.module_from_spec(_spec)
_spec.loader.exec_module(_skel)
MODULES = _skel.MODULES
APPENDIX = _skel.APPENDIX
WORKSHOP_DIR = ROOT / "docs-mintlify" / "blog" / "dbx-workshop"


# ============================================================
# 카테고리별 자동 콘텐츠 — Lab 데이터가 없을 때 fallback
# ============================================================

# Module → Category 매핑
MODULE_CATEGORY = {
    "00": "ui_navigate",
    "01": "ui_admin",
    "02": "compute_config",
    "03": "notebook_use",
    "04": "uc_object_create",
    "05": "uc_rbac_grant",
    "06": "uc_abac",
    "07": "uc_fine_grained",
    "08": "uc_external",
    "09": "uc_audit",
    "10": "uc_boundary",
    "11": "delta_sql",
    "12": "ingest",
    "13": "pipeline_python",
    "14": "job_config",
    "15": "dbsql",
    "16": "dashboard_ui",
    "17": "genie_ui",
    "18": "genie_perm",
    "19": "one_persona",
    "20": "ai_func_sql",
    "21": "vector_search",
    "22": "agent_bricks",
    "23": "agent_perm",
    "24": "genie_code",
    "25": "mlflow_python",
    "26": "serving_ui",
    "27": "apps_yaml",
    "28": "apps_perm",
    "29": "lakebase",
    "30": "sharing",
    "31": "cli_bash",
    "32": "sdk_python",
    "33": "dbconnect",
    "34": "ide",
    "35": "dab_yaml",
    "36": "terraform",
    "37": "rest_api",
    "38": "cicd",
    "39": "secret",
    "40": "testing",
    "99": "cleanup",
}

# Appendix → Category
APPENDIX_CATEGORY = {
    "A-account-console-tour": "appendix_navigate",
    "B-identity-management":  "appendix_identity",
    "C-workspace-management": "appendix_workspace",
    "D-uc-metastore-admin":   "appendix_metastore",
    "E-cloud-resources":      "appendix_cloud",
    "F-logs-audit":           "appendix_logs",
    "G-budget-cost":          "appendix_budget",
    "H-marketplace-provider": "appendix_marketplace",
    "I-account-api-automation": "appendix_api",
}


def fallback_content(lab_num: str, lab_title: str, category: str) -> dict:
    """카테고리별 표준 콘텐츠 생성 — Lab 제목을 참고."""
    base = {
        "duration": "10분",
        "difficulty": "⭐⭐",
        "prereq": [],
        "code_lang": "text",
        "code": f"# {lab_title}\n# 작업 코드 또는 명령은 본 Lab 진행 중 채워집니다.",
        "ui_steps": [
            (f"Workspace UI 진입 — {lab_title}", "step1-entry.png"),
            ("관련 메뉴 / 설정으로 이동", "step2-navigate.png"),
            ("핵심 작업 수행", "step3-action.png"),
            ("결과 확인", "step4-result.png"),
        ],
        "validation": [f"{lab_title} 완료", "결과가 기대한 대로 표시됨"],
        "errors": [("권한 부족", "필요 권한 미보유", "선행 Lab 확인 또는 Admin 문의")],
        "cleanup": "Module 끝의 Cleanup Lab에서 일괄 정리합니다.",
    }

    if category == "uc_rbac_grant":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- 권한 부여\n"
            "GRANT <PRIVILEGE> ON <SECURABLE> <OBJECT> TO `<principal>`;\n\n"
            "-- 권한 조회\n"
            "SHOW GRANTS ON <SECURABLE> <OBJECT>;\n\n"
            "-- 권한 회수\n"
            "REVOKE <PRIVILEGE> ON <SECURABLE> <OBJECT> FROM `<principal>`;"
        )
        base["ui_steps"] = [
            ("Catalog Explorer에서 대상 객체 열기", "step1-catalog-explorer.png"),
            ("Permissions 탭 → Grant 버튼", "step2-permissions-tab.png"),
            ("Principal (User/Group/SP) 검색 → 권한 체크박스", "step3-grant-dialog.png"),
            ("두 번째 사용자 창에서 권한 효과 검증", "step4-verify.png"),
        ]
        base["cleanup"] = "REVOKE 로 권한 회수."

    elif category == "uc_object_create":
        base["code_lang"] = "sql"
        base["code"] = (
            f"-- {lab_title}\n"
            "CREATE <OBJECT_TYPE> IF NOT EXISTS workshop_<name>.<schema>.<object>\n"
            "  (<column_spec>)\n"
            "  COMMENT '<설명>'\n"
            "  TBLPROPERTIES ('owner' = current_user());\n\n"
            "-- 메타데이터 확인\n"
            "DESCRIBE EXTENDED workshop_<name>.<schema>.<object>;"
        )
        base["ui_steps"] = [
            ("Catalog Explorer → Catalog/Schema 선택", "step1-explorer.png"),
            ("Create 버튼 → 대상 객체 종류 선택", "step2-create-button.png"),
            ("이름/스키마/옵션 입력 → Create", "step3-config.png"),
            ("Catalog Explorer에서 객체 노출 확인", "step4-verify.png"),
        ]
        base["cleanup"] = f"`DROP <OBJECT_TYPE> IF EXISTS ...`"

    elif category == "uc_abac":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- Tag 정의 + Column에 부여\n"
            "ALTER TABLE workshop_<name>.default.customers\n"
            "  ALTER COLUMN ssn SET TAGS ('sensitivity' = 'pii');\n\n"
            "-- ABAC Policy (예: PII Column 자동 마스킹)\n"
            "CREATE POLICY mask_pii\n"
            "ON CATALOG workshop_<name>\n"
            "TO ALL\n"
            "WHEN MATCH TAG sensitivity = 'pii'\n"
            "APPLY MASK (col) -> CASE\n"
            "  WHEN is_member('pii-allowed') THEN col\n"
            "  ELSE '***'\n"
            "END;"
        )
        base["ui_steps"] = [
            ("Catalog Explorer → 객체 → Tags 탭", "step1-tags-tab.png"),
            ("Sensitivity tag 부여", "step2-add-tag.png"),
            ("ABAC Policies 페이지에서 Policy 생성", "step3-create-policy.png"),
            ("다른 사용자로 SELECT — 마스킹 결과 확인", "step4-masking-result.png"),
        ]

    elif category == "uc_fine_grained":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- Row Filter Function\n"
            "CREATE FUNCTION workshop_<name>.default.region_filter(region STRING)\n"
            "RETURNS BOOLEAN\n"
            "RETURN region = current_user_region();\n\n"
            "-- 테이블에 Row Filter 적용\n"
            "ALTER TABLE workshop_<name>.default.sales\n"
            "  SET ROW FILTER workshop_<name>.default.region_filter\n"
            "  ON (region);"
        )
        base["ui_steps"] = [
            ("SQL Editor에서 Function 생성", "step1-create-func.png"),
            ("Catalog Explorer → 테이블 → Row Filter 적용", "step2-set-filter.png"),
            ("다른 사용자로 검증", "step3-verify.png"),
        ]

    elif category == "uc_external":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- Storage Credential 생성 (UI 권장)\n"
            "CREATE STORAGE CREDENTIAL <name>\n"
            "  WITH AWS_IAM_ROLE 'arn:aws:iam::<acct>:role/<role>'\n"
            "  COMMENT 'Workshop external';\n\n"
            "-- External Location 등록\n"
            "CREATE EXTERNAL LOCATION <loc-name>\n"
            "  URL 's3://<bucket>/<path>'\n"
            "  WITH (STORAGE CREDENTIAL <name>);"
        )
        base["ui_steps"] = [
            ("Catalog → External Data → Storage Credentials", "step1-storage-creds.png"),
            ("Create → IAM Role ARN 입력", "step2-create-cred.png"),
            ("External Locations → Create", "step3-create-loc.png"),
            ("Test connection", "step4-test.png"),
        ]

    elif category == "uc_audit":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- 최근 1일 audit 이벤트\n"
            "SELECT event_time, user_identity.email, action_name, request_params\n"
            "FROM system.access.audit\n"
            "WHERE event_date >= current_date() - 1\n"
            "ORDER BY event_time DESC\n"
            "LIMIT 100;\n\n"
            "-- Table Lineage 조회\n"
            "SELECT * FROM system.access.table_lineage\n"
            "WHERE target_table_full_name = 'workshop_<name>.default.customers';"
        )
        base["ui_steps"] = [
            ("SQL Editor → system.access 쿼리", "step1-system-access.png"),
            ("Catalog Explorer → 테이블 → Lineage 탭", "step2-lineage-ui.png"),
        ]

    elif category == "delta_sql":
        base["code_lang"] = "sql"
        base["code"] = (
            f"-- {lab_title}\n"
            "-- Delta Lake 핵심 명령 예시:\n\n"
            "-- 1) 생성\n"
            "CREATE TABLE workshop_<name>.default.events (\n"
            "  event_id BIGINT, event_type STRING, ts TIMESTAMP\n"
            ") USING DELTA;\n\n"
            "-- 2) 변경\n"
            "UPDATE workshop_<name>.default.events SET event_type = 'click' WHERE event_id = 1;\n\n"
            "-- 3) 이력 확인\n"
            "DESCRIBE HISTORY workshop_<name>.default.events;\n\n"
            "-- 4) Time Travel\n"
            "SELECT * FROM workshop_<name>.default.events VERSION AS OF 0;"
        )
        base["ui_steps"] = [
            ("SQL Editor에서 위 명령 차례로 실행", "step1-sql-execute.png"),
            ("Catalog Explorer → History 탭에서 버전 확인", "step2-history-tab.png"),
        ]

    elif category == "ingest":
        base["code_lang"] = "python"
        base["code"] = (
            "# Auto Loader 패턴\n"
            "df = (\n"
            "  spark.readStream\n"
            "    .format('cloudFiles')\n"
            "    .option('cloudFiles.format', 'json')\n"
            "    .option('cloudFiles.schemaLocation', '/Volumes/workshop/_chk/schema')\n"
            "    .load('/Volumes/workshop/raw/')\n"
            ")\n\n"
            "(df.writeStream\n"
            "   .option('checkpointLocation', '/Volumes/workshop/_chk/state')\n"
            "   .trigger(availableNow=True)\n"
            "   .toTable('workshop_<name>.bronze.events'))"
        )
        base["ui_steps"] = [
            ("UI: Add Data → Upload files", "step1-add-data.png"),
            ("또는 노트북에서 위 코드 실행", "step2-notebook-run.png"),
            ("Catalog Explorer에서 Bronze 테이블 확인", "step3-bronze-table.png"),
        ]

    elif category == "pipeline_python":
        base["code_lang"] = "python"
        base["code"] = (
            "import dlt\n"
            "from pyspark.sql.functions import col\n\n"
            "@dlt.table(comment='Bronze raw events')\n"
            "def bronze_events():\n"
            "    return spark.readStream.format('cloudFiles') \\\n"
            "        .option('cloudFiles.format', 'json') \\\n"
            "        .load('/Volumes/workshop/raw/')\n\n"
            "@dlt.table(comment='Silver — cleaned')\n"
            "@dlt.expect_or_drop('valid_id', 'event_id IS NOT NULL')\n"
            "def silver_events():\n"
            "    return dlt.read_stream('bronze_events').filter(col('event_type').isNotNull())"
        )
        base["ui_steps"] = [
            ("Jobs & Pipelines → Create pipeline", "step1-create-pipeline.png"),
            ("Source code → 위 노트북 선택", "step2-source.png"),
            ("Start → 그래프 시각화 확인", "step3-graph.png"),
        ]

    elif category == "job_config":
        base["code_lang"] = "yaml"
        base["code"] = (
            "# Jobs UI에서 만든 Job을 YAML로 보면 다음 형태\n"
            "name: workshop-etl\n"
            "tasks:\n"
            "  - task_key: ingest\n"
            "    notebook_task:\n"
            "      notebook_path: /Workspace/Users/<email>/notebooks/ingest\n"
            "    job_cluster_key: main\n"
            "job_clusters:\n"
            "  - job_cluster_key: main\n"
            "    new_cluster:\n"
            "      spark_version: 15.4.x-scala2.12\n"
            "      node_type_id: i3.xlarge\n"
            "      num_workers: 2\n"
            "schedule:\n"
            "  quartz_cron_expression: '0 0 4 * * ?'\n"
            "  timezone_id: Asia/Seoul"
        )
        base["ui_steps"] = [
            ("Jobs & Pipelines → Create job", "step1-create-job.png"),
            ("Task 추가 → Notebook 지정 + Job Cluster 설정", "step2-task.png"),
            ("Schedule / Notifications 설정", "step3-schedule.png"),
            ("Run now → 결과 확인", "step4-run.png"),
        ]

    elif category == "dbsql":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- SQL Editor에서 실행\n"
            "SELECT\n"
            "  o_orderstatus,\n"
            "  COUNT(*) AS orders,\n"
            "  SUM(o_totalprice) AS revenue\n"
            "FROM samples.tpch.orders\n"
            "WHERE o_orderdate >= DATE '1995-01-01'\n"
            "GROUP BY o_orderstatus\n"
            "ORDER BY revenue DESC;"
        )
        base["ui_steps"] = [
            ("SQL → SQL Editor", "step1-sql-editor.png"),
            ("위 쿼리 실행", "step2-run-query.png"),
            ("결과 패널 → \"+\" → Visualization 추가", "step3-add-viz.png"),
        ]

    elif category == "dashboard_ui":
        base["code_lang"] = "text"
        base["code"] = "AI/BI Dashboard는 코드 없이 UI로 구성 — 아래 단계 참조."
        base["ui_steps"] = [
            ("SQL → Dashboards → Create dashboard", "step1-create-dash.png"),
            ("Data 탭 → Dataset 추가 (SQL Warehouse)", "step2-add-dataset.png"),
            ("Canvas → Widget 드래그", "step3-add-widget.png"),
            ("Filter 추가 + Cross-filter 설정", "step4-filter.png"),
            ("Publish → URL 공유", "step5-publish.png"),
        ]

    elif category == "genie_ui":
        base["code_lang"] = "text"
        base["code"] = "Genie는 UI 중심 — 자연어 질의 + Trusted Asset 등록."
        base["ui_steps"] = [
            ("Genie → New Genie space", "step1-new-space.png"),
            ("Tables 선택 → Schema 추가", "step2-tables.png"),
            ("Instructions / Sample Questions 작성", "step3-instructions.png"),
            ("자연어 질의 입력 → SQL 결과 확인", "step4-nl-query.png"),
        ]

    elif category == "genie_perm":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- Genie Space에 underlying 데이터 접근 권한 부여\n"
            "GRANT USE CATALOG ON CATALOG workshop_<name>   TO `analyst_group`;\n"
            "GRANT USE SCHEMA  ON SCHEMA  workshop_<name>.default TO `analyst_group`;\n"
            "GRANT SELECT      ON SCHEMA  workshop_<name>.default TO `analyst_group`;\n\n"
            "-- Genie Space 자체 권한은 UI: Genie Space → Share → Add"
        )
        base["ui_steps"] = [
            ("Genie Space → Share 버튼", "step1-share.png"),
            ("User/Group 추가 + Permission level (Can View / Run / Edit)", "step2-add-perm.png"),
            ("Underlying 데이터 권한도 SQL로 부여", "step3-data-grant.png"),
        ]

    elif category == "one_persona":
        base["code_lang"] = "text"
        base["code"] = (
            "Databricks One URL: https://<workspace>/one\n\n"
            "Persona:\n"
            "  - Builder   : 모든 워크스페이스 기능 (개발자/엔지니어)\n"
            "  - Consumer  : Genie + Dashboards + Apps 만 (비즈니스 사용자)\n\n"
            "Consumer 권한만 부여하려면 Workspace Admin이:\n"
            "  Workspace Settings → Users → 사용자 선택 → Persona = Consumer"
        )
        base["ui_steps"] = [
            ("https://<workspace>/one 접속", "step1-one-entry.png"),
            ("좌상단 Persona 전환", "step2-persona-switch.png"),
            ("Workspace Settings → User Persona 설정", "step3-persona-config.png"),
        ]

    elif category == "ai_func_sql":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- AI Function 예시\n"
            "SELECT\n"
            "  review_text,\n"
            "  ai_classify(review_text, ARRAY('positive','neutral','negative')) AS sentiment,\n"
            "  ai_summarize(review_text, 100) AS summary\n"
            "FROM samples.nyctaxi.feedback\n"
            "LIMIT 10;"
        )
        base["ui_steps"] = [
            ("SQL Editor에서 ai_* 함수 사용", "step1-ai-func-editor.png"),
            ("결과 컬럼에서 LLM 추론 결과 확인", "step2-result.png"),
        ]

    elif category == "vector_search":
        base["code_lang"] = "python"
        base["code"] = (
            "from databricks.vector_search.client import VectorSearchClient\n\n"
            "vsc = VectorSearchClient()\n\n"
            "# Endpoint 생성\n"
            "vsc.create_endpoint(name='workshop-vs', endpoint_type='STANDARD')\n\n"
            "# Delta Sync Index\n"
            "vsc.create_delta_sync_index(\n"
            "    endpoint_name='workshop-vs',\n"
            "    index_name='workshop_<name>.default.docs_idx',\n"
            "    source_table_name='workshop_<name>.default.docs',\n"
            "    pipeline_type='TRIGGERED',\n"
            "    primary_key='doc_id',\n"
            "    embedding_source_column='content',\n"
            "    embedding_model_endpoint_name='databricks-bge-large-en',\n"
            ")"
        )
        base["ui_steps"] = [
            ("Compute → Vector Search → Create endpoint", "step1-vs-endpoint.png"),
            ("Catalog Explorer → 테이블 → Create vector index", "step2-create-index.png"),
            ("Status: ONLINE 대기", "step3-status.png"),
            ("Search 테스트 (위 코드 또는 SDK)", "step4-search.png"),
        ]

    elif category == "agent_bricks":
        base["code_lang"] = "text"
        base["code"] = "Agent Bricks는 UI 중심 — 코드 없이 RAG 봇/추출/Supervisor를 만들 수 있음."
        base["ui_steps"] = [
            ("Agents → Knowledge Assistant → Create", "step1-ka-create.png"),
            ("Data sources → Volume / Vector Index 추가", "step2-data-sources.png"),
            ("Test in playground → 질의 입력", "step3-playground.png"),
            ("Evaluate → 정확도 측정", "step4-evaluate.png"),
            ("Deploy → Endpoint 생성", "step5-deploy.png"),
        ]

    elif category == "agent_perm":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- Agent (Endpoint) 권한\n"
            "GRANT EXECUTE ON ENDPOINT <agent-endpoint> TO `users`;\n\n"
            "-- FMAPI / Foundation Model Endpoint 권한\n"
            "GRANT USAGE ON SERVING ENDPOINT databricks-meta-llama-3-1-70b-instruct TO `users`;"
        )
        base["ui_steps"] = [
            ("Serving → Endpoint → Permissions", "step1-endpoint-perm.png"),
            ("User/Group 추가 + Can Query 선택", "step2-grant-query.png"),
        ]

    elif category == "genie_code":
        base["code_lang"] = "text"
        base["code"] = "Genie Code (구 Assistant) — Notebook 우측 / Cmd+I로 활성화."
        base["ui_steps"] = [
            ("노트북 셀에서 Cmd+I (Mac) / Ctrl+I", "step1-cmd-i.png"),
            ("자연어로 요청 (\"...를 만드는 PySpark 코드\")", "step2-prompt.png"),
            ("Accept / Reject / Regenerate", "step3-accept.png"),
            ("Genie Code 채팅 패널 — 코드 설명 / 디버깅 요청", "step4-chat.png"),
        ]

    elif category == "mlflow_python":
        base["code_lang"] = "python"
        base["code"] = (
            "import mlflow\n"
            "import mlflow.sklearn\n"
            "from sklearn.linear_model import LogisticRegression\n"
            "from sklearn.datasets import load_iris\n\n"
            "mlflow.autolog()\n\n"
            "X, y = load_iris(return_X_y=True)\n"
            "with mlflow.start_run() as run:\n"
            "    model = LogisticRegression(max_iter=200).fit(X, y)\n"
            "    print('Run ID:', run.info.run_id)\n\n"
            "# UC Models에 등록\n"
            "mlflow.register_model(\n"
            "    model_uri=f'runs:/{run.info.run_id}/model',\n"
            "    name='workshop_<name>.default.iris_clf',\n"
            ")"
        )
        base["ui_steps"] = [
            ("ML → Experiments에서 Run 확인", "step1-experiment.png"),
            ("Catalog Explorer → workshop_<name>.default → Models", "step2-uc-models.png"),
            ("Model 버전 → Alias 부여 (@champion)", "step3-alias.png"),
        ]

    elif category == "serving_ui":
        base["code_lang"] = "python"
        base["code"] = (
            "# 등록된 UC Model을 1클릭으로 서빙\n"
            "# Catalog Explorer → Models → 버전 → \"Serve this model\"\n\n"
            "# 또는 SDK로:\n"
            "from databricks.sdk import WorkspaceClient\n"
            "w = WorkspaceClient()\n"
            "w.serving_endpoints.create(\n"
            "    name='workshop-iris',\n"
            "    config={\n"
            "        'served_entities': [{\n"
            "            'name': 'iris-clf',\n"
            "            'entity_name': 'workshop_<name>.default.iris_clf',\n"
            "            'entity_version': '1',\n"
            "            'workload_size': 'Small',\n"
            "            'scale_to_zero_enabled': True,\n"
            "        }]\n"
            "    }\n"
            ")"
        )
        base["ui_steps"] = [
            ("Catalog Explorer → Model → Serve this model", "step1-serve.png"),
            ("Endpoint 설정 (Workload size, Scale to zero)", "step2-config.png"),
            ("Status = Ready 대기", "step3-ready.png"),
            ("Query 탭에서 테스트 호출", "step4-query.png"),
        ]

    elif category == "apps_yaml":
        base["code_lang"] = "yaml"
        base["code"] = (
            "# app.yaml — Databricks App 정의\n"
            "command:\n"
            "  - python\n"
            "  - app.py\n\n"
            "env:\n"
            "  - name: DATABRICKS_WAREHOUSE_ID\n"
            "    valueFrom: workshop_warehouse  # Resource binding\n\n"
            "# requirements.txt 와 app.py 는 같은 디렉토리에"
        )
        base["ui_steps"] = [
            ("Apps → Create app → Streamlit template", "step1-create-app.png"),
            ("app.yaml + app.py 편집", "step2-edit-code.png"),
            ("Deploy → 빌드 로그 확인", "step3-deploy.png"),
            ("App URL 접속", "step4-open-url.png"),
        ]

    elif category == "apps_perm":
        base["code_lang"] = "python"
        base["code"] = (
            "# OBO (On-Behalf-Of-User) 인증으로 사용자 권한으로 쿼리\n"
            "from databricks.sdk import WorkspaceClient\n"
            "from fastapi import Request\n\n"
            "def get_obo_client(req: Request):\n"
            "    user_token = req.headers.get('X-Forwarded-Access-Token')\n"
            "    return WorkspaceClient(host=os.environ['DATABRICKS_HOST'], token=user_token)\n\n"
            "# App SP 인증 (default)\n"
            "w = WorkspaceClient()  # APP_SP token 자동 사용"
        )
        base["ui_steps"] = [
            ("App → Settings → Permissions", "step1-app-perm.png"),
            ("App SP 자동 생성 확인 (Service Principals)", "step2-app-sp.png"),
            ("Resources 탭 → Warehouse 바인딩", "step3-resource-bind.png"),
        ]

    elif category == "lakebase":
        base["code_lang"] = "bash"
        base["code"] = (
            "# psql 클라이언트로 연결\n"
            "psql -h <lakebase-host> -p 5432 -U <user> -d <database> -W\n\n"
            "# SQL\n"
            "CREATE TABLE app_state (\n"
            "  id BIGSERIAL PRIMARY KEY,\n"
            "  data JSONB,\n"
            "  created_at TIMESTAMPTZ DEFAULT NOW()\n"
            ");"
        )
        base["ui_steps"] = [
            ("Compute → Lakebase → Create instance", "step1-create-lb.png"),
            ("Database 생성 (UI 또는 psql)", "step2-create-db.png"),
            ("Connection string 복사 → psql 연결", "step3-connect.png"),
        ]

    elif category == "sharing":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- Share 만들기\n"
            "CREATE SHARE workshop_share;\n"
            "ALTER SHARE workshop_share ADD TABLE workshop_<name>.default.events;\n\n"
            "-- Recipient 생성 (D2D 또는 Open)\n"
            "CREATE RECIPIENT partner_<name>\n"
            "  USING ID '<partner-sharing-identifier>';  -- D2D\n"
            "-- 또는 Open Sharing: CREATE RECIPIENT ... (no USING ID)\n\n"
            "-- Recipient에 Share 권한 부여\n"
            "GRANT SELECT ON SHARE workshop_share TO RECIPIENT partner_<name>;"
        )
        base["ui_steps"] = [
            ("Catalog → Delta Sharing → Shared by me", "step1-shared-by-me.png"),
            ("Create share → Add tables", "step2-create-share.png"),
            ("Recipients → Create recipient", "step3-recipient.png"),
            ("Activation Link 공유", "step4-activation.png"),
        ]

    elif category == "cli_bash":
        base["code_lang"] = "bash"
        base["code"] = (
            f"# {lab_title}\n"
            "# Databricks CLI 명령\n"
            "databricks --version\n\n"
            "# 예: workspace, clusters, jobs, sql, apps 등 서브 명령\n"
            "databricks workspace list /\n"
            "databricks clusters list --output json | jq '.[] | {name, state}'"
        )
        base["ui_steps"] = [
            ("터미널에서 `databricks --help` 실행", "step1-cli-help.png"),
            ("해당 서브 명령 실행 후 결과 비교", "step2-subcommand.png"),
        ]

    elif category == "sdk_python":
        base["code_lang"] = "python"
        base["code"] = (
            "from databricks.sdk import WorkspaceClient\n\n"
            "w = WorkspaceClient()  # Profile / env var 자동 사용\n\n"
            "# 예: 클러스터 목록\n"
            "for c in w.clusters.list():\n"
            "    print(c.cluster_id, c.cluster_name, c.state.name)"
        )
        base["ui_steps"] = [
            ("Python 환경에서 `pip install databricks-sdk`", "step1-install.png"),
            ("위 코드 실행 → 결과 확인", "step2-run.png"),
        ]

    elif category == "dbconnect":
        base["code_lang"] = "python"
        base["code"] = (
            "from databricks.connect import DatabricksSession\n\n"
            "spark = DatabricksSession.builder.profile('workshop').getOrCreate()\n\n"
            "df = spark.table('samples.tpch.customer')\n"
            "df.show(5)"
        )
        base["ui_steps"] = [
            ("로컬 venv에서 `pip install databricks-connect`", "step1-install.png"),
            ("`databricks configure --profile workshop` (PAT)", "step2-configure.png"),
            ("위 Python 코드 실행", "step3-run-local.png"),
        ]

    elif category == "ide":
        base["code_lang"] = "text"
        base["code"] = "IDE 통합은 GUI 중심 — Step 따라 진행."
        base["ui_steps"] = [
            ("VS Code Marketplace → \"Databricks\" 검색 → Install", "step1-install-ext.png"),
            ("VS Code → Cmd+Shift+P → \"Databricks: Configure\"", "step2-configure.png"),
            ("Workspace folder 연결 + Sync 활성화", "step3-sync.png"),
        ]

    elif category == "dab_yaml":
        base["code_lang"] = "yaml"
        base["code"] = (
            "# databricks.yml — 최상위\n"
            "bundle:\n"
            "  name: workshop_bundle\n\n"
            "include:\n"
            "  - resources/jobs/*.yml\n"
            "  - resources/pipelines/*.yml\n\n"
            "targets:\n"
            "  dev:\n"
            "    workspace:\n"
            "      profile: workshop-dev\n"
            "    default: true\n"
            "  prod:\n"
            "    workspace:\n"
            "      profile: workshop-prod"
        )
        base["ui_steps"] = [
            ("터미널: `databricks bundle init`", "step1-bundle-init.png"),
            ("`databricks bundle validate`", "step2-validate.png"),
            ("`databricks bundle deploy --target dev`", "step3-deploy.png"),
            ("Workspace UI에서 배포 결과 확인", "step4-ws-check.png"),
        ]

    elif category == "terraform":
        base["code_lang"] = "hcl"
        base["code"] = (
            'terraform {\n'
            '  required_providers {\n'
            '    databricks = { source = "databricks/databricks" }\n'
            '  }\n'
            '}\n\n'
            'provider "databricks" { profile = "workshop" }\n\n'
            'resource "databricks_catalog" "workshop" {\n'
            '  name    = "workshop_tf"\n'
            '  comment = "Created by Terraform"\n'
            '}\n\n'
            'resource "databricks_schema" "default" {\n'
            '  catalog_name = databricks_catalog.workshop.name\n'
            '  name         = "default"\n'
            '}'
        )
        base["ui_steps"] = [
            ("`terraform init`", "step1-init.png"),
            ("`terraform plan` → 변경 사항 확인", "step2-plan.png"),
            ("`terraform apply` → Catalog Explorer 확인", "step3-apply.png"),
        ]

    elif category == "rest_api":
        base["code_lang"] = "bash"
        base["code"] = (
            "# REST API 직접 호출\n"
            "curl -X POST \\\n"
            "  -H \"Authorization: Bearer $DATABRICKS_TOKEN\" \\\n"
            "  -H \"Content-Type: application/json\" \\\n"
            "  $DATABRICKS_HOST/api/2.1/jobs/run-now \\\n"
            "  -d '{\"job_id\": 12345}'"
        )
        base["ui_steps"] = [
            ("Postman / curl 환경 준비 (PAT)", "step1-setup.png"),
            ("위 API 호출 → 200 응답 확인", "step2-call-api.png"),
        ]

    elif category == "cicd":
        base["code_lang"] = "yaml"
        base["code"] = (
            "# .github/workflows/databricks-dab.yml\n"
            "name: DAB Deploy\n"
            "on:\n"
            "  push: { branches: [main] }\n"
            "  pull_request:\n"
            "jobs:\n"
            "  validate:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: databricks/setup-cli@main\n"
            "      - run: databricks bundle validate --target dev\n"
            "        env:\n"
            "          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}\n"
            "          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}"
        )
        base["ui_steps"] = [
            ("GitHub Repo → Settings → Secrets에 DATABRICKS_TOKEN 등록", "step1-secrets.png"),
            ("위 워크플로우 commit + push", "step2-push.png"),
            ("Actions 탭에서 실행 결과 확인", "step3-actions.png"),
        ]

    elif category == "secret":
        base["code_lang"] = "bash"
        base["code"] = (
            "# Secret Scope 생성\n"
            "databricks secrets create-scope workshop_secrets\n\n"
            "# Secret 등록\n"
            "databricks secrets put-secret workshop_secrets api_key --string-value '<value>'\n\n"
            "# 노트북에서 사용\n"
            "# api_key = dbutils.secrets.get('workshop_secrets', 'api_key')"
        )
        base["ui_steps"] = [
            ("CLI로 Scope 생성", "step1-create-scope.png"),
            ("Secret put", "step2-put-secret.png"),
            ("노트북에서 dbutils.secrets.get", "step3-use-secret.png"),
        ]

    elif category == "testing":
        base["code_lang"] = "python"
        base["code"] = (
            "# tests/test_transform.py\n"
            "import pytest\n"
            "from notebooks.transform import clean\n\n"
            "def test_clean_drops_null():\n"
            "    df = spark.createDataFrame([(1, 'a'), (2, None)], ['id', 'name'])\n"
            "    out = clean(df)\n"
            "    assert out.count() == 1\n\n"
            "# 실행: pytest tests/ (Databricks Connect로 원격 cluster 활용)"
        )
        base["ui_steps"] = [
            ("로컬에 PyTest + Databricks Connect 환경", "step1-setup.png"),
            ("`pytest tests/` 실행 → 모든 케이스 PASS", "step2-run-tests.png"),
        ]

    elif category == "cleanup":
        base["code_lang"] = "sql"
        base["code"] = (
            "-- 모든 Workshop catalog 삭제\n"
            "DROP CATALOG IF EXISTS workshop_<name> CASCADE;\n\n"
            "-- 또는 단계별 정리: Pipeline → Job → Cluster → Warehouse → Catalog\n"
            "-- CLI 일괄:\n"
            "--   databricks pipelines delete --pipeline-id ...\n"
            "--   databricks jobs delete ...\n"
            "--   databricks clusters delete ...\n"
            "--   databricks warehouses delete ..."
        )
        base["ui_steps"] = [
            ("각 자원 페이지에서 Delete", "step1-delete-each.png"),
            ("Catalog Explorer에서 Workshop catalog 삭제 확인", "step2-verify.png"),
        ]

    # Appendix categories
    elif category == "appendix_navigate":
        base["code_lang"] = "text"
        base["code"] = "Account Console URL: accounts.cloud.databricks.com\nAccount Admin 권한 필요."
        base["ui_steps"] = [
            ("accounts.cloud.databricks.com 접속", "step1-account-console.png"),
            ("좌측 메뉴 탐색", "step2-menu.png"),
        ]

    elif category == "appendix_identity":
        base["code_lang"] = "text"
        base["code"] = (
            "Account Console → User Management\n"
            "  - Users / Groups / Service Principals 탭\n"
            "  - Authentication: SSO / SCIM 설정"
        )
        base["ui_steps"] = [
            ("User management 진입", "step1-user-mgmt.png"),
            ("대상 작업 수행", "step2-action.png"),
        ]

    elif category == "appendix_workspace":
        base["code_lang"] = "text"
        base["code"] = "Account Console → Workspaces 에서 Workspace 라이프사이클 관리."
        base["ui_steps"] = [
            ("Workspaces 메뉴", "step1-workspaces.png"),
            ("대상 Workspace 클릭 → 설정 / 권한 / 삭제", "step2-action.png"),
        ]

    elif category == "appendix_metastore":
        base["code_lang"] = "text"
        base["code"] = "Account Console → Catalog (Metastore) 에서 Region별 Metastore 관리."
        base["ui_steps"] = [
            ("Catalog 메뉴 → 대상 Metastore 선택", "step1-metastore.png"),
            ("Admin / Storage Root / Catalog 관리", "step2-admin.png"),
        ]

    elif category == "appendix_cloud":
        base["code_lang"] = "text"
        base["code"] = (
            "Cloud Resources (AWS 기준):\n"
            "  - Credential Configuration (IAM Role)\n"
            "  - Storage Configuration (S3 Bucket)\n"
            "  - Network Configuration (VPC)\n"
            "  - VPC Endpoint / Private Access Settings (PrivateLink)\n"
            "  - Customer Managed Key (CMK)\n\n"
            "상세 설정은 [AWS Workspace 구성 가이드](/blog/platform-setup/aws/overview) 참조."
        )
        base["ui_steps"] = [
            ("Cloud resources 메뉴 진입", "step1-cloud-menu.png"),
            ("해당 탭으로 이동", "step2-tab.png"),
            ("Add → ARN/ID 입력 → 등록", "step3-register.png"),
        ]

    elif category == "appendix_logs":
        base["code_lang"] = "text"
        base["code"] = (
            "Logs 설정:\n"
            "  - Audit Log Delivery (S3 destination)\n"
            "  - Billable Usage Log Delivery\n"
            "  - System Tables 활성화\n\n"
            "System Tables 활성화 API:\n"
            "  curl -X PUT $DATABRICKS_HOST/api/2.0/unity-catalog/metastores/<id>/systemschemas/access \\\n"
            "    -H \"Authorization: Bearer $TOKEN\""
        )
        base["ui_steps"] = [
            ("Settings → Logs (Audit log delivery)", "step1-logs-tab.png"),
            ("Add delivery configuration", "step2-add.png"),
            ("S3 bucket + IAM role 입력", "step3-config.png"),
        ]

    elif category == "appendix_budget":
        base["code_lang"] = "text"
        base["code"] = (
            "Budget Policies:\n"
            "  - 월별 한도 / 알림\n"
            "  - Cluster Policy 연동\n"
            "  - Custom Tags로 추적\n\n"
            "비용 분석 쿼리:\n"
            "  SELECT usage_date, sku_name, SUM(usage_quantity * pricing.default) AS cost\n"
            "  FROM system.billing.usage u JOIN system.billing.list_prices pricing USING (sku_name)\n"
            "  GROUP BY usage_date, sku_name ORDER BY usage_date DESC;"
        )
        base["ui_steps"] = [
            ("Settings → Budget policies", "step1-budget.png"),
            ("Create policy → 한도 설정", "step2-create.png"),
        ]

    elif category == "appendix_marketplace":
        base["code_lang"] = "text"
        base["code"] = "Account Console → Marketplace → Provider 등록 + Listing 관리."
        base["ui_steps"] = [
            ("Marketplace 메뉴", "step1-marketplace.png"),
            ("Provider profile 생성", "step2-provider.png"),
            ("Listing 생성 → Audience 설정", "step3-listing.png"),
        ]

    elif category == "appendix_api":
        base["code_lang"] = "bash"
        base["code"] = (
            "# Account API 호출 예\n"
            "ACCOUNT_ID=<your-account-id>\n"
            "TOKEN=<oauth-token>\n\n"
            "curl -H \"Authorization: Bearer $TOKEN\" \\\n"
            "  https://accounts.cloud.databricks.com/api/2.0/accounts/$ACCOUNT_ID/workspaces"
        )
        base["ui_steps"] = [
            ("OAuth Token 발급 (SP 기반)", "step1-token.png"),
            ("API 호출 → 응답 확인", "step2-call.png"),
        ]

    elif category == "notebook_use":
        base["code_lang"] = "python"
        base["code"] = (
            "# Cell 1 — Python\n"
            "df = spark.range(10)\n"
            "display(df)\n\n"
            "# Cell 2 — SQL (Magic command)\n"
            "# %sql\n"
            "# SELECT * FROM samples.tpch.customer LIMIT 5;"
        )
        base["ui_steps"] = [
            ("Workspace → Create → Notebook", "step1-create-notebook.png"),
            ("셀에 코드 입력 → Shift+Enter", "step2-run-cell.png"),
            ("셀 좌상단 언어 선택기 (Python/SQL/Scala/R) 또는 매직커맨드", "step3-language.png"),
        ]

    elif category == "compute_config":
        base["code_lang"] = "text"
        base["code"] = f"# {lab_title}\n# Compute 관련 설정은 UI 중심 — 아래 Step 따라 진행."
        base["ui_steps"] = [
            ("Compute 메뉴 진입", "step1-compute.png"),
            ("해당 옵션 설정", "step2-option.png"),
            ("상태 확인", "step3-status.png"),
        ]

    elif category == "ui_navigate":
        # already default
        pass

    elif category == "ui_admin":
        base["code_lang"] = "text"
        base["code"] = "Account Console / Workspace Admin Settings에서 관리 작업."

    return base


def render_lab(lab_num: str, lab_title: str, category: str, mod_num: str, mod_slug: str, mod_title: str) -> str:
    data = LAB_DATA.get(lab_num) or fallback_content(lab_num, lab_title, category)

    duration = data.get("duration", "10분")
    difficulty = data.get("difficulty", "⭐⭐")
    prereq = data.get("prereq", [])
    what = data.get("what",
                    f"본 Lab은 **{lab_title}** 을 단일 기능 단위로 직접 수행하며 동작을 체감하는 것이 목적입니다. "
                    f"`{mod_title}` 의 핵심 흐름 안에서 이 단계가 어떤 역할을 하는지 위치를 잡습니다.")

    options = data.get("options")
    code_lang = data.get("code_lang", "text")
    code = data.get("code", "")
    ui_steps = data.get("ui_steps", [])
    validation = data.get("validation", [])
    errors = data.get("errors", [])
    cleanup = data.get("cleanup", "")

    # Frontmatter & Info
    prereq_str = "TBD" if not prereq else ", ".join(f"Lab {p}" for p in prereq)
    out = []
    out.append(f"---\ntitle: \"Lab {lab_num} — {lab_title}\"\n---\n")
    out.append(f"<Info>\n**소요 시간**: {duration} | **난이도**: {difficulty}\n**선행**: {prereq_str}\n**기능 분류**: {category}\n</Info>\n")

    # 1) What
    out.append("## 🧭 이 기능은 무엇이고 언제 쓰나\n")
    out.append(what + "\n")

    # 2) Options
    out.append("## ⚙️ 핵심 옵션 / 파라미터\n")
    if options:
        out.append("| 옵션 | 타입 | 기본 | 설명 |\n|------|------|------|------|")
        for opt, typ, dflt, desc in options:
            out.append(f"| `{opt}` | {typ} | {dflt} | {desc} |")
        out.append("")
    else:
        out.append("| 옵션 | 설명 |\n|------|------|\n| 본 Lab에서 다루는 핵심 변수 | 샘플 코드의 `<...>` 부분을 본인 환경에 맞게 교체 |\n")

    # 3) Sample code
    out.append("## 💻 샘플 코드\n")
    if code:
        out.append(f"```{code_lang}\n{code}\n```\n")
    else:
        out.append("```text\n작성 예정\n```\n")

    # 4) UI 등가
    out.append("## 🖥 UI 등가 작업 — 스크린샷 위치\n")
    img_base = f"images/dbx-workshop/{mod_num}-{mod_slug}/{lab_num.replace('.', '-')}"
    if ui_steps:
        for i, step in enumerate(ui_steps, 1):
            if isinstance(step, tuple):
                text, shot = step
            else:
                text, shot = step, f"step{i}.png"
            out.append(f"**Step {i}.** {text}")
            out.append(f"")
            out.append(f"![{lab_title} — Step {i}](/{img_base}/{shot})")
            out.append(f"")
    else:
        out.append("(UI 단계 작성 예정)\n")

    # 5) Validation
    out.append("## ✅ Validation\n")
    if validation:
        for v in validation:
            out.append(f"- [ ] {v}")
        out.append("")
    else:
        out.append("- [ ] 작업이 에러 없이 완료\n- [ ] 결과가 UI / 쿼리로 확인됨\n")

    # 6) Errors
    out.append("## 🚧 자주 만나는 오류\n")
    out.append("| 에러 | 원인 | 해결 |\n|------|------|------|")
    if errors:
        for e in errors:
            err, cause, fix = e
            out.append(f"| `{err}` | {cause} | {fix} |")
    else:
        out.append("| 권한 부족 | Workspace/UC 권한 미보유 | 선행 Lab 확인 또는 Admin 문의 |")
    out.append("")

    # 7) Cleanup
    out.append("## 🧹 Cleanup\n")
    out.append((cleanup or "Module 끝의 Cleanup Lab에서 일괄 정리합니다.") + "\n")

    return "\n".join(out) + "\n"


def render_module_overview(mod: dict, kind: str = "module") -> str:
    title = mod["title"]
    subtitle = mod["subtitle"]
    labs = mod["labs"]
    lab_list = "\n".join(f"- **Lab {num}** — {t}" for num, _, t in labs)

    return f"""---
title: "{title}"
---

> **{subtitle}**

본 Module은 다음 Lab으로 구성됩니다. 순서대로 진행하세요.

## 📋 Lab 목록

{lab_list}

## 🎯 학습 목표

- 본 Module이 다루는 기능 영역의 **핵심 객체 / 명령 / UI 진입점**을 익힌다
- 각 Lab의 5블록 (무엇/옵션/코드/UI/검증)을 순서대로 진행
- Module 끝의 정리 Lab으로 리소스 cleanup

## ⏱ 예상 시간

약 {sum_duration(labs)}분 (Lab당 평균 10분 기준)

## 🔗 권장 사전 조건

- 이전 Module들 (낮은 번호) 완료 권장
- 권한 Lab의 경우 [Lab 1.1 ~ 1.5](../01-identity/overview)에서 만든 두 번째 사용자 / SP 필요

---

준비됐다면 첫 Lab으로 진입하세요.
"""


def sum_duration(labs):
    # 단순 추정: Lab 수 × 10
    return len(labs) * 10


# ============================================================
# 실행
# ============================================================

def build_all():
    # Main modules
    for mod in MODULES:
        mod_num = mod["num"]
        mod_slug = mod["slug"]
        mod_title = mod["title"]
        category = MODULE_CATEGORY.get(mod_num, "ui_navigate")

        d = WORKSHOP_DIR / f"{mod_num}-{mod_slug}"
        # overview
        (d / "overview.mdx").write_text(render_module_overview(mod), encoding="utf-8")
        # labs
        for num, slug, title in mod["labs"]:
            content = render_lab(num, title, category, mod_num, mod_slug, mod_title)
            (d / f"{slug}.mdx").write_text(content, encoding="utf-8")

    # Appendix
    app_dir = WORKSHOP_DIR / "appendix"
    for mod in APPENDIX:
        mod_slug = mod["slug"]
        mod_title = mod["title"]
        category = APPENDIX_CATEGORY.get(mod_slug, "appendix_navigate")
        d = app_dir / mod_slug
        (d / "overview.mdx").write_text(render_module_overview(mod), encoding="utf-8")
        for num, slug, title in mod["labs"]:
            content = render_lab(num, title, category, mod_slug, mod_slug, mod_title)
            (d / f"{slug}.mdx").write_text(content, encoding="utf-8")

    print(f"✅ 모든 Lab/Module overview 콘텐츠 작성 완료")


if __name__ == "__main__":
    build_all()
