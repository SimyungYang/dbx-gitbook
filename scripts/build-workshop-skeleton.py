#!/usr/bin/env python3
"""
Databricks Workshop 껍데기 생성 스크립트.

이 스크립트는:
1. docs-mintlify/blog/dbx-workshop/ 디렉토리 구조 생성
2. 각 Module/Lab의 빈 mdx 파일 (frontmatter + placeholder) 생성
3. Module Overview, Workshop Overview, Prerequisites, Appendix Overview 생성
4. docs.json에 "Databricks Workshop" 탭 추가

실행: python3 scripts/build-workshop-skeleton.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSHOP_DIR = ROOT / "docs-mintlify" / "blog" / "dbx-workshop"
DOCS_JSON = ROOT / "docs-mintlify" / "docs.json"

# (lab_num, slug, title)
MODULES = [
    {
        "num": "00",
        "slug": "workspace-tour",
        "title": "M0. Workspace Tour & Account Console",
        "subtitle": "Workspace UI와 Account Console 진입부터 시작",
        "labs": [
            ("0.1", "workspace-login",       "Workspace 첫 접속과 URL 형식"),
            ("0.2", "sidebar-tour",          "사이드바 둘러보기 (Workspace/Catalog/Compute/Jobs/SQL)"),
            ("0.3", "user-settings",         "User Settings — PAT / Git / SSH 키"),
            ("0.4", "account-id-region",     "Account ID와 Region 확인"),
            ("0.5", "admin-vs-user",         "Account Admin vs Workspace Admin vs Metastore Admin 권한 차이"),
            ("0.6", "identity-federation",   "Identity Federation 활성화 여부 확인"),
        ],
    },
    {
        "num": "01",
        "slug": "identity",
        "title": "M1. Identity — User / Group / Service Principal",
        "subtitle": "Workshop에서 사용할 사용자/그룹/SP 준비",
        "labs": [
            ("1.1", "user-account-add",      "User Account 추가 (Account Console)"),
            ("1.2", "group-create",          "Account-level Group 생성"),
            ("1.3", "service-principal-create", "Service Principal 생성"),
            ("1.4", "sp-oauth-secret",       "SP OAuth Secret 발급"),
            ("1.5", "test-user-workspace-add", "두 번째 테스트 User를 Workspace에 할당"),
            ("1.6", "pat-token",             "Personal Access Token 발급"),
            ("1.7", "sso-saml-overview",     "SSO/SAML 개요 (UI 확인)"),
            ("1.8", "scim-overview",         "SCIM Provisioning 개요 (UI 확인)"),
        ],
    },
    {
        "num": "02",
        "slug": "compute",
        "title": "M2. Compute — Cluster / Warehouse / Serverless",
        "subtitle": "Workshop에서 사용할 컴퓨트 리소스 준비",
        "labs": [
            ("2.1", "serverless-notebook",   "Serverless Compute에 노트북 attach"),
            ("2.2", "classic-cluster-create", "Classic All-Purpose Cluster 생성"),
            ("2.3", "cluster-config-detail", "Cluster 설정 옵션 (Photon, autoscale, DBR 버전)"),
            ("2.4", "cluster-policy",        "Cluster Policy 만들기"),
            ("2.5", "sql-warehouse-create",  "SQL Warehouse 생성"),
            ("2.6", "sql-warehouse-types",   "Serverless vs Pro vs Classic Warehouse 비교"),
            ("2.7", "job-cluster-vs-all-purpose", "Job Cluster vs All-Purpose 차이"),
            ("2.8", "autoscale-observe",     "Auto-scaling 동작 관찰"),
            ("2.9", "cluster-permissions",   "Cluster Permissions"),
            ("2.10", "compute-cleanup",      "Compute Cleanup"),
        ],
    },
    {
        "num": "03",
        "slug": "notebook",
        "title": "M3. Notebook, Workspace Files, Git",
        "subtitle": "노트북 환경 마스터하기",
        "labs": [
            ("3.1", "notebook-create",       "첫 노트북 생성 + Serverless attach"),
            ("3.2", "multi-language-cells",  "Python/SQL/Scala/R 다중 언어 셀"),
            ("3.3", "magic-commands",        "매직커맨드 (%sql, %md, %sh, %pip, %run)"),
            ("3.4", "variable-explorer",     "변수 탐색기 (Variable Explorer)"),
            ("3.5", "git-folder",            "Git Folder 연결 (GitHub repo clone)"),
            ("3.6", "co-edit",               "실시간 협업 (Co-edit)"),
            ("3.7", "comments",              "셀 댓글 + 노트북 댓글"),
            ("3.8", "dashboard-mode",        "Notebook을 Dashboard 모드로"),
            ("3.9", "dbutils-basics",        "dbutils 기본 (fs, widgets, secrets)"),
            ("3.10", "notebook-run-job",     "Notebook을 Job으로 실행"),
            ("3.11", "notebook-import-export", "Notebook Import / Export"),
            ("3.12", "notebook-permissions", "Notebook Permissions"),
        ],
    },
    {
        "num": "04",
        "slug": "uc-objects",
        "title": "M4. UC 객체 — Catalog / Schema / Table / View / Volume / Function / Model / Connection",
        "subtitle": "Unity Catalog의 모든 객체를 직접 만들어보기",
        "labs": [
            ("4.1", "catalog-explorer-tour", "Catalog Explorer 둘러보기"),
            ("4.2", "catalog-create",        "Catalog 생성"),
            ("4.3", "schema-create",         "Schema 생성 + Default Location"),
            ("4.4", "managed-table",         "Managed Table 만들기"),
            ("4.5", "external-table",        "External Table 만들기"),
            ("4.6", "view-create",           "View 생성"),
            ("4.7", "materialized-view",     "Materialized View 생성"),
            ("4.8", "streaming-table",       "Streaming Table 생성"),
            ("4.9", "volume-managed",        "Managed Volume 생성"),
            ("4.10", "volume-external",      "External Volume 생성"),
            ("4.11", "volume-files",         "Volume에 파일 업로드/다운로드"),
            ("4.12", "uc-function-sql",      "UC SQL Function 등록"),
            ("4.13", "uc-function-python",   "UC Python Function 등록"),
            ("4.14", "uc-connection",        "UC Connection 생성"),
            ("4.15", "foreign-catalog",      "Foreign Catalog (Snowflake/MySQL)"),
            ("4.16", "uc-model",             "UC Model 등록"),
            ("4.17", "catalog-explorer-search", "Catalog Explorer 검색"),
            ("4.18", "catalog-explorer-tags-comments", "Catalog Explorer Tag & Comment + AI Comment"),
        ],
    },
    {
        "num": "05",
        "slug": "uc-rbac",
        "title": "M5. UC RBAC — Role-Based Access Control",
        "subtitle": "GRANT/REVOKE, Privilege Hierarchy, Ownership",
        "labs": [
            ("5.1", "privilege-hierarchy",   "Securable Object 계층 이해 (Metastore → Catalog → Schema → Table)"),
            ("5.2", "use-catalog",           "USE CATALOG 권한 부여"),
            ("5.3", "use-schema",            "USE SCHEMA 권한 부여"),
            ("5.4", "select-grant",          "SELECT 권한 부여"),
            ("5.5", "modify-grant",          "MODIFY 권한 (INSERT/UPDATE/DELETE)"),
            ("5.6", "create-grant",          "CREATE TABLE / CREATE SCHEMA 권한"),
            ("5.7", "execute-grant",         "EXECUTE 권한 (Function)"),
            ("5.8", "volume-rw-grant",       "READ VOLUME / WRITE VOLUME 권한"),
            ("5.9", "browse-grant",          "BROWSE 권한 (메타데이터만)"),
            ("5.10", "apply-tag-grant",      "APPLY TAG 권한"),
            ("5.11", "all-privileges",       "ALL PRIVILEGES 일괄 부여"),
            ("5.12", "grant-with-option",    "WITH GRANT OPTION (위임 권한)"),
            ("5.13", "revoke",               "REVOKE 권한 회수"),
            ("5.14", "show-grants",          "SHOW GRANTS 권한 조회"),
            ("5.15", "inheritance",          "권한 상속 검증 (Catalog → Schema → Table)"),
            ("5.16", "ownership-transfer",   "Ownership 변경 (ALTER OWNER TO)"),
            ("5.17", "group-grant",          "Group 단위 권한 부여"),
            ("5.18", "account-vs-workspace-group", "Account-level vs Workspace-local Group"),
            ("5.19", "sp-grant",             "Service Principal 권한 부여"),
            ("5.20", "multi-user-validation", "두 번째 사용자/SP로 권한 검증"),
        ],
    },
    {
        "num": "06",
        "slug": "uc-abac",
        "title": "M6. UC ABAC — Attribute-Based Access Control",
        "subtitle": "Tag 기반 정책으로 동적 권한 관리",
        "labs": [
            ("6.1", "abac-vs-rbac",          "ABAC vs RBAC 차이 + 시나리오"),
            ("6.2", "sensitivity-tags-define", "Sensitivity Tag 정의 (pii, phi, confidential)"),
            ("6.3", "column-tag-ui",         "Column에 Tag 부여 (UI)"),
            ("6.4", "column-tag-sql",        "Column에 Tag 부여 (SQL ALTER)"),
            ("6.5", "schema-catalog-tags",   "Schema/Catalog 레벨 Tag"),
            ("6.6", "abac-policy-create",    "첫 ABAC Policy — Tag 기반 마스킹"),
            ("6.7", "abac-policy-apply",     "Policy를 Catalog/Schema에 적용"),
            ("6.8", "abac-policy-validate",  "다른 사용자로 마스킹 결과 검증"),
            ("6.9", "abac-with-row-filter",  "ABAC + Row Filter 조합"),
            ("6.10", "abac-rbac-priority",   "RBAC vs ABAC 충돌 시 우선순위"),
            ("6.11", "abac-policy-disable",  "Policy 비활성화 / 삭제"),
            ("6.12", "abac-audit",           "Audit Log에서 ABAC 적용 추적"),
        ],
    },
    {
        "num": "07",
        "slug": "uc-fine-grained",
        "title": "M7. UC Fine-grained Security — Row Filter, Column Mask, Dynamic View",
        "subtitle": "행/열 수준 접근 제어",
        "labs": [
            ("7.1", "row-filter-function",   "Row Filter Function 작성 (SQL UDF)"),
            ("7.2", "row-filter-apply",      "ALTER TABLE SET ROW FILTER 적용"),
            ("7.3", "row-filter-validate",   "Row Filter 검증 (Group 멤버십 기반)"),
            ("7.4", "column-mask-function",  "Column Mask Function 작성"),
            ("7.5", "column-mask-apply",     "ALTER COLUMN SET MASK"),
            ("7.6", "dynamic-view",          "Dynamic View — current_user(), is_member()"),
            ("7.7", "combined-row-column",   "Row Filter + Column Mask 조합"),
            ("7.8", "cleanup-filters-masks", "Filter / Mask 제거 + Cleanup"),
        ],
    },
    {
        "num": "08",
        "slug": "uc-external-resources",
        "title": "M8. UC External Resources — Storage Credential, External Location, Connection",
        "subtitle": "외부 스토리지와 데이터 소스 연결",
        "labs": [
            ("8.1", "storage-credential-create", "Storage Credential 생성"),
            ("8.2", "external-location-create", "External Location 생성"),
            ("8.3", "external-location-permissions", "External Location 권한"),
            ("8.4", "file-events-enable",    "File Events 활성화 (SNS/SQS)"),
            ("8.5", "uc-connection-types",   "UC Connection 종류 비교"),
            ("8.6", "foreign-catalog-mysql", "Foreign Catalog (MySQL) 연결"),
            ("8.7", "delta-sharing-receive", "Delta Sharing 받기"),
            ("8.8", "delta-sharing-provide", "Delta Sharing 제공"),
        ],
    },
    {
        "num": "09",
        "slug": "uc-audit-lineage",
        "title": "M9. UC Audit & Lineage",
        "subtitle": "System Tables, Audit Log, Lineage 추적",
        "labs": [
            ("9.1", "system-tables-enable",  "System Tables 활성화"),
            ("9.2", "system-access-audit",   "system.access.audit 쿼리"),
            ("9.3", "grant-revoke-history",  "GRANT/REVOKE 이력 추적"),
            ("9.4", "table-lineage",         "Table Lineage 자동 추적"),
            ("9.5", "column-lineage",        "Column Lineage 추적"),
            ("9.6", "catalog-explorer-lineage", "Catalog Explorer Lineage 그래프"),
            ("9.7", "notebook-lineage",      "Notebook → 테이블 Lineage"),
            ("9.8", "audit-dashboard",       "Audit 자동화 대시보드"),
        ],
    },
    {
        "num": "10",
        "slug": "uc-governance-boundary",
        "title": "M10. UC Governance Boundary — Catalog Binding, Network Binding",
        "subtitle": "Catalog/Network 경계 관리",
        "labs": [
            ("10.1", "catalog-binding",       "Catalog Binding (Workspace 단위)"),
            ("10.2", "catalog-isolation",     "Catalog Isolation 모드"),
            ("10.3", "network-binding",       "Network Binding"),
            ("10.4", "metastore-admin",       "Metastore Admin"),
            ("10.5", "default-catalog",       "Default Catalog 설정"),
            ("10.6", "cross-region-considerations", "Cross-region 고려사항"),
        ],
    },
    {
        "num": "11",
        "slug": "delta-lake",
        "title": "M11. Delta Lake — ACID, Time Travel, OPTIMIZE, CDF, Liquid Clustering",
        "subtitle": "Delta Lake의 모든 기능을 직접 체험",
        "labs": [
            ("11.1", "delta-create-insert",   "Delta Table 생성 + INSERT"),
            ("11.2", "update-delete-merge",   "UPDATE / DELETE / MERGE"),
            ("11.3", "time-travel-version",   "Time Travel (VERSION AS OF)"),
            ("11.4", "time-travel-timestamp", "Time Travel (TIMESTAMP AS OF)"),
            ("11.5", "describe-history",      "DESCRIBE HISTORY"),
            ("11.6", "restore",               "RESTORE TABLE TO VERSION"),
            ("11.7", "optimize",              "OPTIMIZE (Compaction)"),
            ("11.8", "zorder",                "Z-ORDER"),
            ("11.9", "vacuum",                "VACUUM"),
            ("11.10", "liquid-clustering",    "Liquid Clustering"),
            ("11.11", "change-data-feed",     "Change Data Feed (CDF)"),
            ("11.12", "schema-evolution",     "Schema Evolution (mergeSchema)"),
            ("11.13", "generated-columns",    "Generated Columns"),
            ("11.14", "clone",                "DEEP CLONE / SHALLOW CLONE"),
        ],
    },
    {
        "num": "12",
        "slug": "data-ingestion",
        "title": "M12. Data Ingestion — Upload / COPY INTO / Auto Loader / Lakeflow Connect",
        "subtitle": "파일에서 테이블까지 모든 인제스트 방법",
        "labs": [
            ("12.1", "ui-upload-data",        "UI \"Add Data\" — CSV/Parquet 업로드"),
            ("12.2", "copy-into",             "COPY INTO 명령"),
            ("12.3", "auto-loader-directory", "Auto Loader (Directory Listing)"),
            ("12.4", "auto-loader-file-events", "Auto Loader (File Events / SQS)"),
            ("12.5", "schema-inference-evolution", "Schema Inference & Evolution"),
            ("12.6", "rescued-data",          "Rescued Data 처리"),
            ("12.7", "lakeflow-connect-salesforce", "Lakeflow Connect — Salesforce"),
            ("12.8", "foreign-table-query",   "Foreign Table 직접 조회"),
        ],
    },
    {
        "num": "13",
        "slug": "lakeflow-pipelines",
        "title": "M13. Lakeflow Declarative Pipelines (구 DLT)",
        "subtitle": "선언형 ETL 파이프라인",
        "labs": [
            ("13.1", "pipeline-create",       "첫 파이프라인 생성 (UI)"),
            ("13.2", "streaming-table-bronze", "Streaming Table (Bronze)"),
            ("13.3", "materialized-view-silver", "Materialized View (Silver)"),
            ("13.4", "gold-aggregation",      "Gold Aggregation"),
            ("13.5", "expectations",          "Expectations (@expect, @expect_or_drop)"),
            ("13.6", "pipeline-monitoring",   "파이프라인 모니터링"),
            ("13.7", "pipeline-event-log",    "Event Log 분석"),
            ("13.8", "pipeline-permissions",  "Pipeline 권한"),
        ],
    },
    {
        "num": "14",
        "slug": "jobs-workflow",
        "title": "M14. Jobs & Workflow + Run-As Permissions",
        "subtitle": "Job DAG, 스케줄, 알림, 권한",
        "labs": [
            ("14.1", "job-single-task",       "단일 노트북 Job 생성"),
            ("14.2", "job-multi-task-dag",    "다중 태스크 (DAG)"),
            ("14.3", "job-parameters",        "파라미터 전달"),
            ("14.4", "job-cluster",           "Job Cluster 설정"),
            ("14.5", "conditional-retry",     "조건부 실행 + 재시도"),
            ("14.6", "schedule-cron",         "스케줄 (Cron)"),
            ("14.7", "file-arrival-trigger",  "File Arrival Trigger"),
            ("14.8", "notifications",         "알림 (Email/Slack/Webhook)"),
            ("14.9", "run-as",                "Run As (User vs SP)"),
            ("14.10", "job-permissions",      "Job Permissions"),
        ],
    },
    {
        "num": "15",
        "slug": "dbsql",
        "title": "M15. DBSQL — SQL Editor, Query, Visualization",
        "subtitle": "SQL 분석가 트랙",
        "labs": [
            ("15.1", "sql-editor",            "SQL Editor 사용"),
            ("15.2", "saved-query",           "Saved Query 저장 + 공유"),
            ("15.3", "query-parameters",      "Query Parameters"),
            ("15.4", "query-history",         "Query History"),
            ("15.5", "query-profile",         "Query Profile (성능 분석)"),
            ("15.6", "visualization-chart",   "Visualization — Chart"),
            ("15.7", "visualization-pivot",   "Pivot / Counter / Table"),
            ("15.8", "sql-snippets",          "SQL Snippets"),
            ("15.9", "sql-aliases",           "Catalog Aliases"),
            ("15.10", "warehouse-monitoring", "Warehouse Monitoring"),
        ],
    },
    {
        "num": "16",
        "slug": "aibi-dashboard",
        "title": "M16. AI/BI Dashboard + Dashboard 권한",
        "subtitle": "드래그앤드롭 대시보드 + 권한",
        "labs": [
            ("16.1", "dashboard-create",      "Dashboard 생성"),
            ("16.2", "dashboard-widgets",     "Widget 종류 (Counter/Chart/Table/Text)"),
            ("16.3", "dashboard-filters",     "Filter & Cross-filter"),
            ("16.4", "dashboard-publish",     "Dashboard 게시"),
            ("16.5", "dashboard-embed",       "Dashboard 임베드"),
            ("16.6", "dashboard-permissions", "Dashboard 권한 (Can View/Run/Edit/Manage)"),
            ("16.7", "sql-alert",             "SQL Alert 설정"),
            ("16.8", "alert-notifications",   "Alert 알림 채널 (Slack/Email)"),
        ],
    },
    {
        "num": "17",
        "slug": "genie-spaces",
        "title": "M17. Genie Spaces — 자연어 NLQ",
        "subtitle": "자연어로 SQL 자동 생성",
        "labs": [
            ("17.1", "genie-space-create",    "Genie Space 생성"),
            ("17.2", "sample-questions",      "Sample Question 등록"),
            ("17.3", "instructions",          "Instruction 작성"),
            ("17.4", "trusted-assets",        "Trusted Asset 등록"),
            ("17.5", "nl-query",              "자연어 질의 → SQL 자동 생성"),
            ("17.6", "sql-function-genie",    "SQL Function을 Genie에 노출"),
            ("17.7", "genie-history",         "History & Curation"),
            ("17.8", "genie-share",           "Genie Space 공유"),
            ("17.9", "genie-embed",           "Genie 임베드 (외부 포털)"),
            ("17.10", "genie-evaluation",     "Genie 정확도 평가"),
        ],
    },
    {
        "num": "18",
        "slug": "genie-permissions",
        "title": "M18. Genie Permissions — Space + Underlying Data 분리",
        "subtitle": "Genie의 2-layer 권한 모델",
        "labs": [
            ("18.1", "space-level-permissions", "Genie Space-level 권한 (Can View/Run/Edit/Manage)"),
            ("18.2", "underlying-data-permissions", "Underlying Data 권한 (SELECT 필요)"),
            ("18.3", "permission-mismatch",   "권한 불일치 시나리오 — 에러 체험"),
            ("18.4", "sp-genie-run",          "Service Principal로 Genie 실행"),
            ("18.5", "trusted-function-execute", "Trusted Function EXECUTE 권한"),
            ("18.6", "group-batch-grant",     "Group 단위 일괄 권한"),
        ],
    },
    {
        "num": "19",
        "slug": "databricks-one",
        "title": "M19. Databricks One — Persona, Consumer Mode",
        "subtitle": "Consumer/Builder Persona 통합 진입점",
        "labs": [
            ("19.1", "databricks-one-entry", "Databricks One URL 진입"),
            ("19.2", "persona-switch",        "Persona 전환 (Builder ↔ Consumer)"),
            ("19.3", "consumer-ui",           "Consumer UI 둘러보기"),
            ("19.4", "default-genie-space",   "Default Genie Space 할당"),
            ("19.5", "consumer-only-permission", "Consumer 권한만 부여"),
            ("19.6", "publish-to-one",        "Genie/Dashboard/App을 One에 게시"),
            ("19.7", "consumer-validation",   "Consumer 사용자로 검증"),
            ("19.8", "embedded-genie-portal", "Embedded Genie — 외부 포털"),
        ],
    },
    {
        "num": "20",
        "slug": "ai-functions",
        "title": "M20. AI Functions — SQL로 LLM 호출",
        "subtitle": "SQL 한 줄로 AI 호출",
        "labs": [
            ("20.1", "ai-query",              "ai_query() 기본"),
            ("20.2", "ai-classify",           "ai_classify"),
            ("20.3", "ai-extract",            "ai_extract"),
            ("20.4", "ai-summarize",          "ai_summarize"),
            ("20.5", "ai-translate",          "ai_translate / ai_fix_grammar"),
            ("20.6", "ai-parse-document",     "ai_parse_document (PDF)"),
            ("20.7", "ai-forecast",           "ai_forecast (시계열)"),
            ("20.8", "ai-sentiment-similarity", "ai_analyze_sentiment / ai_similarity"),
        ],
    },
    {
        "num": "21",
        "slug": "vector-search",
        "title": "M21. Vector Search + Endpoint/Index 권한",
        "subtitle": "벡터 검색 + 권한 관리",
        "labs": [
            ("21.1", "vs-endpoint-create",    "Vector Search Endpoint 생성"),
            ("21.2", "vs-delta-sync-index",   "Delta Sync Index 만들기"),
            ("21.3", "vs-direct-index",       "Direct Vector Access Index"),
            ("21.4", "vs-query",              "벡터 검색 쿼리"),
            ("21.5", "vs-metadata-filter",    "메타데이터 필터"),
            ("21.6", "vs-hybrid-search",      "Hybrid Search (Keyword + Vector)"),
            ("21.7", "vs-permissions",        "VS Endpoint/Index 권한"),
            ("21.8", "vs-monitoring",         "VS Monitoring"),
        ],
    },
    {
        "num": "22",
        "slug": "agent-bricks",
        "title": "M22. Agent Bricks — KA / MAS / Information Extraction",
        "subtitle": "코드 없는 AI Agent",
        "labs": [
            ("22.1", "ai-playground",         "AI Playground에서 모델 비교"),
            ("22.2", "ka-create",             "Knowledge Assistant 생성"),
            ("22.3", "ka-upload-docs",        "KA에 문서 업로드"),
            ("22.4", "ka-evaluate",           "KA 평가"),
            ("22.5", "ka-improve",            "KA 개선"),
            ("22.6", "information-extraction", "Information Extraction"),
            ("22.7", "supervisor-create",     "Multi-Agent Supervisor 생성"),
            ("22.8", "supervisor-routing",    "Supervisor Routing"),
            ("22.9", "supervisor-tools",      "Supervisor Tools 연동"),
            ("22.10", "agent-cleanup",        "Agent Cleanup"),
        ],
    },
    {
        "num": "23",
        "slug": "agent-bricks-permissions",
        "title": "M23. Agent Bricks Permissions",
        "subtitle": "KA / FMAPI / Supervisor 권한",
        "labs": [
            ("23.1", "ka-permissions",        "KA 권한"),
            ("23.2", "fmapi-endpoint-perm",   "FMAPI Endpoint 권한"),
            ("23.3", "ka-data-source-perm",   "KA Data Source 권한"),
            ("23.4", "supervisor-permissions", "Supervisor 권한"),
            ("23.5", "sp-agent-run",          "SP로 Agent 실행"),
        ],
    },
    {
        "num": "24",
        "slug": "genie-code",
        "title": "M24. Genie Code (구 Databricks Assistant)",
        "subtitle": "자연어 → 코드, 디버깅",
        "labs": [
            ("24.1", "genie-code-enable",     "Genie Code 활성화"),
            ("24.2", "nl-to-code",            "자연어로 코드 생성"),
            ("24.3", "code-explain",          "코드 설명"),
            ("24.4", "code-refactor",         "코드 리팩토링"),
            ("24.5", "sql-generate",          "SQL 자동 생성"),
            ("24.6", "error-debug",           "에러 자동 진단"),
        ],
    },
    {
        "num": "25",
        "slug": "mlflow",
        "title": "M25. MLflow — Tracking / Tracing / Evaluation",
        "subtitle": "ML 라이프사이클 + LLM Observability",
        "labs": [
            ("25.1", "sklearn-autolog",       "scikit-learn + Autolog"),
            ("25.2", "mlflow-experiment-compare", "Experiment 비교"),
            ("25.3", "mlflow-uc-models-register", "UC Models 등록"),
            ("25.4", "model-alias",           "Model Alias (@champion, @challenger)"),
            ("25.5", "model-version-stage",   "모델 버전 전환"),
            ("25.6", "mlflow-tracing-llm",    "MLflow Tracing (LLM)"),
            ("25.7", "mlflow-tracing-langchain", "MLflow Tracing (LangChain/LangGraph)"),
            ("25.8", "mlflow-evaluation-llm", "MLflow LLM Evaluation"),
            ("25.9", "mlflow-prompt-registry", "MLflow Prompt Registry"),
            ("25.10", "mlflow-feedback",      "MLflow Feedback API"),
            ("25.11", "mlflow-permissions",   "MLflow Permissions"),
            ("25.12", "mlflow-cleanup",       "Cleanup"),
        ],
    },
    {
        "num": "26",
        "slug": "model-serving",
        "title": "M26. Model Serving + Endpoint 권한",
        "subtitle": "1클릭 모델 배포",
        "labs": [
            ("26.1", "endpoint-deploy",       "Model Serving 엔드포인트 배포"),
            ("26.2", "endpoint-query",        "엔드포인트 쿼리"),
            ("26.3", "traffic-split",         "A/B 트래픽 분할"),
            ("26.4", "inference-table",       "Inference Table 자동 로깅"),
            ("26.5", "fmapi-call",            "FMAPI 호출"),
            ("26.6", "custom-model-serving",  "Custom Model Serving (Python class)"),
            ("26.7", "endpoint-monitoring",   "Endpoint Monitoring"),
            ("26.8", "endpoint-permissions",  "Endpoint Permissions (Can Query / Manage)"),
        ],
    },
    {
        "num": "27",
        "slug": "databricks-apps",
        "title": "M27. Databricks Apps",
        "subtitle": "Streamlit/Dash/FastAPI 빠른 배포",
        "labs": [
            ("27.1", "app-streamlit-template", "Streamlit Template 배포"),
            ("27.2", "app-sql-warehouse",     "SQL Warehouse 연결"),
            ("27.3", "app-lakebase",          "Lakebase 연결"),
            ("27.4", "app-sso",               "SSO + 권한"),
            ("27.5", "app-local-dev",         "로컬 개발"),
            ("27.6", "app-deploy",            "App 배포"),
            ("27.7", "app-resources",         "App Resources 바인딩"),
            ("27.8", "app-monitoring",        "App Logs / Monitoring"),
        ],
    },
    {
        "num": "28",
        "slug": "apps-permissions",
        "title": "M28. Apps Permissions — OBO + App SP",
        "subtitle": "On-behalf-of-user vs Service Principal 인증",
        "labs": [
            ("28.1", "app-permission",        "App-level 권한 (Can Use / Can Manage)"),
            ("28.2", "app-sp-auto",           "App Service Principal 자동 생성"),
            ("28.3", "app-sp-grant",          "App SP에 권한 부여"),
            ("28.4", "obo-auth",              "On-behalf-of-user 인증"),
            ("28.5", "app-resource-binding",  "Resource 바인딩으로 권한 자동 부여"),
            ("28.6", "obo-vs-sp",             "OBO vs SP 동작 비교"),
        ],
    },
    {
        "num": "29",
        "slug": "lakebase",
        "title": "M29. Lakebase — Postgres OLTP + 권한",
        "subtitle": "Managed Postgres 사용법",
        "labs": [
            ("29.1", "lakebase-instance",     "Lakebase Instance 생성"),
            ("29.2", "lakebase-database",     "Database / Branch"),
            ("29.3", "lakebase-sync",         "Delta → Lakebase Sync"),
            ("29.4", "lakebase-psql",         "psql 클라이언트 연결"),
            ("29.5", "lakebase-from-app",     "App에서 Lakebase 사용"),
            ("29.6", "lakebase-permissions",  "DB 권한 (Postgres GRANT)"),
            ("29.7", "lakebase-branching",    "Branching 활용"),
            ("29.8", "lakebase-monitoring",   "Lakebase Monitoring"),
        ],
    },
    {
        "num": "30",
        "slug": "marketplace-sharing",
        "title": "M30. Marketplace + Delta Sharing",
        "subtitle": "데이터셋 공유와 소비",
        "labs": [
            ("30.1", "marketplace-get-dataset", "Marketplace 데이터셋 받기"),
            ("30.2", "marketplace-install",   "데이터셋 설치"),
            ("30.3", "delta-sharing-recipient", "Recipient 생성"),
            ("30.4", "delta-sharing-share",   "Share 만들기"),
            ("30.5", "delta-sharing-open",    "Open Sharing (외부)"),
            ("30.6", "delta-sharing-d2d",     "Databricks-to-Databricks Sharing"),
            ("30.7", "sharing-audit",         "Sharing Audit"),
            ("30.8", "sharing-permissions",   "Sharing Permissions"),
        ],
    },
    {
        "num": "31",
        "slug": "databricks-cli",
        "title": "M31. Databricks CLI",
        "subtitle": "Command line으로 모든 것 다루기",
        "labs": [
            ("31.1", "cli-install",           "CLI 설치 (brew/curl)"),
            ("31.2", "cli-auth",              "Profile 인증 (databricks auth login)"),
            ("31.3", "cli-workspace",         "Workspace 파일 다루기"),
            ("31.4", "cli-uc",                "UC 객체 다루기 (catalog/schema/table)"),
            ("31.5", "cli-jobs",              "Job 실행 / 관리"),
            ("31.6", "cli-clusters",          "Cluster 관리"),
            ("31.7", "cli-volumes",           "Volume 업로드 / 다운로드 (fs cp)"),
            ("31.8", "cli-repos",             "Repos 동기화"),
            ("31.9", "cli-warehouses",        "SQL Warehouse 관리"),
            ("31.10", "cli-apps",             "Apps 배포 (databricks apps deploy)"),
        ],
    },
    {
        "num": "32",
        "slug": "databricks-sdk",
        "title": "M32. Databricks SDK (Python)",
        "subtitle": "Python SDK로 자동화",
        "labs": [
            ("32.1", "sdk-install",           "SDK 설치 + WorkspaceClient 초기화"),
            ("32.2", "sdk-auth-methods",      "인증 방식 (PAT / OAuth U2M / M2M / Profile)"),
            ("32.3", "sdk-jobs-run",          "Job 실행 + 결과 가져오기"),
            ("32.4", "sdk-sql-statement",     "SQL Statement Execution API"),
            ("32.5", "sdk-files",             "Workspace Files / Volume 관리"),
            ("32.6", "sdk-uc-objects",        "UC 객체 생성"),
            ("32.7", "sdk-clusters",          "Cluster 생성 / 모니터링"),
            ("32.8", "sdk-webhook",           "Webhook + Notification"),
        ],
    },
    {
        "num": "33",
        "slug": "databricks-connect",
        "title": "M33. Databricks Connect — 로컬 IDE에서 원격 Spark",
        "subtitle": "로컬에서 Cluster 코드 실행",
        "labs": [
            ("33.1", "dbconnect-install",     "Databricks Connect 설치"),
            ("33.2", "dbconnect-auth",        "인증 설정 (Cluster ID + Profile)"),
            ("33.3", "dbconnect-spark",       "로컬 IDE에서 원격 Cluster로 Spark 실행"),
            ("33.4", "dbconnect-dataframe",   "DataFrame 조작 + display()"),
            ("33.5", "dbconnect-debug",       "로컬 디버깅 (Local stack trace)"),
            ("33.6", "dbconnect-serverless",  "Serverless Compute에 Connect"),
        ],
    },
    {
        "num": "34",
        "slug": "ide-integration",
        "title": "M34. IDE 통합 — VS Code / Cursor / JetBrains",
        "subtitle": "IDE에서 Databricks 직접 다루기",
        "labs": [
            ("34.1", "vscode-extension-install", "VS Code Databricks Extension 설치"),
            ("34.2", "vscode-workspace-link", "Workspace 폴더 연결"),
            ("34.3", "vscode-notebook-sync",  "Notebook 동기화 + 원격 실행"),
            ("34.4", "vscode-dab-integration", "Asset Bundle 통합"),
            ("34.5", "cursor-jetbrains",      "Cursor / JetBrains IDE 연동"),
            ("34.6", "ssh-cluster",           "SSH로 클러스터 디버깅"),
        ],
    },
    {
        "num": "35",
        "slug": "dab-deep-dive",
        "title": "M35. Databricks Asset Bundle (DAB) — Deep Dive",
        "subtitle": "IaC로 Databricks 리소스 관리",
        "labs": [
            ("35.1", "dab-overview",          "DAB 개념 + databricks.yml 구조"),
            ("35.2", "dab-init",              "bundle init 템플릿 (default-python / mlops-stacks)"),
            ("35.3", "dab-first-job",         "첫 Job을 DAB로 정의"),
            ("35.4", "dab-job-cluster",       "Job + Job Cluster 정의"),
            ("35.5", "dab-pipeline",          "Lakeflow Pipeline 정의"),
            ("35.6", "dab-app",               "Databricks App 정의"),
            ("35.7", "dab-dashboard",         "AI/BI Dashboard 정의"),
            ("35.8", "dab-serving",           "Model Serving Endpoint 정의"),
            ("35.9", "dab-uc-resources",      "UC Volume / Schema / Model 정의"),
            ("35.10", "dab-variables",        "Variables (var.xxx)"),
            ("35.11", "dab-targets",          "Targets (dev / staging / prod)"),
            ("35.12", "dab-validate",         "bundle validate"),
            ("35.13", "dab-deploy",           "bundle deploy"),
            ("35.14", "dab-run",              "bundle run"),
            ("35.15", "dab-state-destroy",    "State 관리 + bundle destroy"),
        ],
    },
    {
        "num": "36",
        "slug": "terraform",
        "title": "M36. Terraform Provider",
        "subtitle": "Terraform으로 Databricks 관리",
        "labs": [
            ("36.1", "tf-provider-setup",     "Provider 설정 + 인증"),
            ("36.2", "tf-workspace-resources", "Workspace 자원 (Job/Cluster/Pipeline)"),
            ("36.3", "tf-uc-resources",       "UC 자원 (Catalog/Schema/Table/Grant)"),
            ("36.4", "tf-account-resources",  "Account-level 자원 (Workspace/Group/SP/Metastore)"),
            ("36.5", "tf-state",              "State 관리"),
            ("36.6", "tf-vs-dab",             "DAB vs Terraform — 언제 무엇을"),
        ],
    },
    {
        "num": "37",
        "slug": "rest-api",
        "title": "M37. REST API + Webhook",
        "subtitle": "직접 REST API 호출",
        "labs": [
            ("37.1", "api-auth",              "REST API 인증 (PAT, OAuth)"),
            ("37.2", "api-curl-job",          "curl로 Job 트리거"),
            ("37.3", "api-sql-statement",     "SQL Statement Execution API"),
            ("37.4", "api-catalog",           "Catalog API"),
            ("37.5", "api-webhook",           "Webhook (Model Registry, Job)"),
            ("37.6", "api-openapi",           "OpenAPI 스펙 + 코드 생성"),
        ],
    },
    {
        "num": "38",
        "slug": "cicd",
        "title": "M38. CI/CD — DAB + GitHub Actions",
        "subtitle": "GitOps 워크플로우",
        "labs": [
            ("38.1", "cicd-github-actions-template", "DAB + GitHub Actions 템플릿"),
            ("38.2", "cicd-pr-validate",      "PR마다 validate"),
            ("38.3", "cicd-dev-deploy",       "main merge → dev 배포"),
            ("38.4", "cicd-prod-deploy",      "Tag → prod 배포"),
            ("38.5", "cicd-pytest",           "PyTest 통합"),
        ],
    },
    {
        "num": "39",
        "slug": "secret-management",
        "title": "M39. Secret Management",
        "subtitle": "Secret Scope + Cloud KMS 연동",
        "labs": [
            ("39.1", "secret-scope-create",   "Secret Scope 생성 (Databricks-backed)"),
            ("39.2", "secret-aws-sm",         "AWS Secrets Manager 연동"),
            ("39.3", "secret-azure-kv",       "Azure Key Vault 연동"),
            ("39.4", "secret-use",            "dbutils.secrets.get / 환경변수"),
        ],
    },
    {
        "num": "40",
        "slug": "testing-quality",
        "title": "M40. Testing & Quality",
        "subtitle": "Notebook 테스트 + 품질 확인",
        "labs": [
            ("40.1", "pytest-notebook",       "PyTest로 노트북 테스트"),
            ("40.2", "dlt-expectations-test", "DLT Expectations 테스트"),
            ("40.3", "query-profile-perf",    "DBSQL Query Profile 성능 분석"),
            ("40.4", "code-lineage",          "Code Lineage 확인"),
            ("40.5", "nutter-framework",      "nutter / OSS 테스트 프레임워크"),
        ],
    },
    {
        "num": "99",
        "slug": "cleanup",
        "title": "M99. Final Cleanup",
        "subtitle": "Workshop에서 만든 모든 리소스 정리",
        "labs": [
            ("99.1", "cleanup-all",           "전체 리소스 일괄 정리"),
        ],
    },
]

APPENDIX = [
    {
        "num": "A",
        "slug": "A-account-console-tour",
        "title": "Appendix A. Account Console 개요",
        "subtitle": "Account Admin 트랙 시작점",
        "labs": [
            ("A.1", "account-console-entry", "Account Console 진입 (accounts.cloud.databricks.com)"),
            ("A.2", "menu-tour",             "좌측 메뉴 둘러보기"),
            ("A.3", "admin-tiers",           "Admin Tier 비교 (Account/Workspace/Metastore)"),
            ("A.4", "account-region-id",     "Account ID / Region 확인"),
            ("A.5", "federation-check",      "Identity Federation 활성화 여부"),
        ],
    },
    {
        "num": "B",
        "slug": "B-identity-management",
        "title": "Appendix B. Identity Management",
        "subtitle": "User / Group / SP / SSO / SCIM",
        "labs": [
            ("B.1", "user-add",              "User 수동 추가"),
            ("B.2", "user-deactivate",       "User 비활성화 / 삭제"),
            ("B.3", "group-account-level",   "Account-level Group 생성"),
            ("B.4", "nested-groups",         "Nested Group"),
            ("B.5", "sp-create",             "Service Principal 생성 + Secret"),
            ("B.6", "sso-saml",              "SSO (SAML 2.0) 설정"),
            ("B.7", "scim-provision",        "SCIM Provisioning (Okta/Entra)"),
            ("B.8", "identity-federation-enable", "Identity Federation 활성화"),
            ("B.9", "workspace-assign-vs-auto", "Workspace 수동 vs 자동 할당"),
            ("B.10", "pat-policy",           "PAT 정책 (TTL, 최대 수)"),
        ],
    },
    {
        "num": "C",
        "slug": "C-workspace-management",
        "title": "Appendix C. Workspace 관리",
        "subtitle": "Workspace 생성 / 설정 / 삭제",
        "labs": [
            ("C.1", "workspace-create-quickstart", "Workspace 생성 (Quick start)"),
            ("C.2", "workspace-create-custom", "Workspace 생성 (Custom — IAM/Storage/Network)"),
            ("C.3", "workspace-settings",    "Workspace 설정 변경 (Pricing Tier 등)"),
            ("C.4", "workspace-admin-assign", "Workspace Admin 지정"),
            ("C.5", "workspace-delete",      "Workspace 삭제 (Soft → Hard)"),
            ("C.6", "metastore-assign",      "Workspace에 Metastore 할당 / 해제"),
        ],
    },
    {
        "num": "D",
        "slug": "D-uc-metastore-admin",
        "title": "Appendix D. UC Metastore Admin",
        "subtitle": "Metastore 생성 / 관리",
        "labs": [
            ("D.1", "metastore-create",      "Metastore 생성"),
            ("D.2", "metastore-admin-assign", "Metastore Admin 지정"),
            ("D.3", "metastore-default-catalog", "Default Catalog 설정"),
            ("D.4", "metastore-storage-root", "Storage Root 위치"),
            ("D.5", "metastore-multi-workspace", "다중 Workspace 할당"),
        ],
    },
    {
        "num": "E",
        "slug": "E-cloud-resources",
        "title": "Appendix E. Cloud Resources (AWS 중심)",
        "subtitle": "IAM / S3 / VPC / PrivateLink / CMK / NCC",
        "labs": [
            ("E.1", "credential-config",     "Credential Configuration (Cross-Account IAM Role)"),
            ("E.2", "storage-config",        "Storage Configuration (Root S3 Bucket)"),
            ("E.3", "network-config",        "Network Configuration (VPC + Subnet)"),
            ("E.4", "vpc-endpoint",          "VPC Endpoint (REST API + SCC Relay)"),
            ("E.5", "private-access",        "Private Access Settings"),
            ("E.6", "cmk",                   "Customer Managed Key (CMK)"),
            ("E.7", "ncc",                   "Network Connectivity Configuration (NCC)"),
            ("E.8", "cloud-region-diff",     "Cloud / Region 별 차이 (AWS/Azure/GCP)"),
        ],
    },
    {
        "num": "F",
        "slug": "F-logs-audit",
        "title": "Appendix F. Logs & Audit",
        "subtitle": "Audit Log Delivery + System Tables",
        "labs": [
            ("F.1", "audit-log-delivery",    "Audit Log Delivery 설정 (S3)"),
            ("F.2", "audit-log-format",      "Audit Log 포맷 + 쿼리"),
            ("F.3", "billable-usage-delivery", "Billable Usage Log Delivery"),
            ("F.4", "system-tables-activate", "System Tables 활성화"),
            ("F.5", "system-tables-permission", "System Tables 권한"),
            ("F.6", "compliance-profile",    "Compliance Profile (HIPAA/PCI/FedRAMP)"),
        ],
    },
    {
        "num": "G",
        "slug": "G-budget-cost",
        "title": "Appendix G. Budget & Cost",
        "subtitle": "비용 관리 + Tag",
        "labs": [
            ("G.1", "budget-policy",         "Budget Policy 생성"),
            ("G.2", "budget-apply",          "Budget을 Compute에 적용"),
            ("G.3", "custom-tags",           "Custom Tags 정의"),
            ("G.4", "tag-auto-apply",        "Tag 자동 적용 (Workspace/Compute/Job)"),
            ("G.5", "usage-dashboard",       "비용 분석 대시보드 (system.billing.usage)"),
        ],
    },
    {
        "num": "H",
        "slug": "H-marketplace-provider",
        "title": "Appendix H. Marketplace Provider",
        "subtitle": "데이터 / 모델 Provider 등록",
        "labs": [
            ("H.1", "provider-register",     "Provider 등록"),
            ("H.2", "listing-create",        "Listing 생성"),
            ("H.3", "listing-audience",      "Audience 제한"),
            ("H.4", "provider-stats",        "Provider 통계"),
        ],
    },
    {
        "num": "I",
        "slug": "I-account-api-automation",
        "title": "Appendix I. Account API 자동화",
        "subtitle": "Account API + Terraform mws_*",
        "labs": [
            ("I.1", "account-api-token",     "Account API OAuth Token 발급"),
            ("I.2", "account-api-curl",      "curl로 Account API 호출"),
            ("I.3", "account-api-workspace-create", "Workspace 자동 생성 (API)"),
            ("I.4", "scim-api-automation",   "SCIM API 자동화"),
            ("I.5", "audit-log-delivery-api", "Audit Log Delivery 자동 설정"),
            ("I.6", "terraform-mws",         "Terraform databricks_mws_* 리소스"),
        ],
    },
]


LAB_TEMPLATE = """---
title: "Lab {num} — {title}"
---

<Info>
**소요 시간**: TBD | **난이도**: TBD
**선행**: TBD
</Info>

> 🚧 이 Lab은 작성 예정입니다. 곧 내용이 채워집니다.

## 🧭 이 기능은 무엇이고 언제 쓰나

(작성 예정)

## ⚙️ 핵심 옵션

(작성 예정)

## 💻 샘플 코드

```text
TBD
```

## 🖥 UI 등가 작업

(작성 예정)

## ✅ Validation

(작성 예정)

## 🚧 자주 만나는 오류

| 에러 | 원인 | 해결 |
|------|------|------|
| TBD  | TBD  | TBD  |

## 🧹 Cleanup

(작성 예정)
"""

MODULE_OVERVIEW_TEMPLATE = """---
title: "{title}"
---

> 🚧 이 모듈은 작성 예정입니다.

**{subtitle}**

## 이 모듈의 Lab

{lab_list}

## 학습 목표

(작성 예정)

## 사전 조건

(작성 예정)
"""

WORKSHOP_OVERVIEW = """---
title: "Databricks Hands-On Workshop"
---

> 🚧 본 Workshop은 단계적으로 작성 중입니다. Module별 진행 상황은 아래 표에서 확인하세요.

## 🎯 Workshop 목적

Databricks의 모든 주요 기능을 **직접 클릭하고 코드를 실행하면서** 체감하기 위한 핸즈온 가이드입니다.
AWS Workshop 스타일로, 기능 하나하나가 단일 Lab으로 분해되어 있습니다.

## 📚 구성

- **41개 Module**, **약 400개 Lab**
- 각 Lab은 5–20분 분량
- 풀 코스 약 2주 (실습 시간 35시간+)

### Tier 1 — Foundation
- M0. Workspace Tour & Account Console
- M1. Identity — User / Group / Service Principal
- M2. Compute — Cluster / Warehouse / Serverless

### Tier 2 — Notebook & Workspace
- M3. Notebook, Workspace Files, Git

### Tier 3 — Unity Catalog Deep Dive ★ 권한 집중
- M4. UC 객체 (Catalog/Schema/Table/View/Volume/Function/Model/Connection)
- M5. UC RBAC
- M6. UC ABAC
- M7. UC Fine-grained Security
- M8. UC External Resources
- M9. UC Audit & Lineage
- M10. UC Governance Boundary

### Tier 4 — Data Engineering
- M11. Delta Lake
- M12. Data Ingestion
- M13. Lakeflow Declarative Pipelines
- M14. Jobs & Workflow

### Tier 5 — Analytics & BI
- M15. DBSQL
- M16. AI/BI Dashboard
- M17. Genie Spaces
- M18. Genie Permissions
- M19. Databricks One

### Tier 6 — AI / ML
- M20. AI Functions
- M21. Vector Search
- M22. Agent Bricks
- M23. Agent Bricks Permissions
- M24. Genie Code
- M25. MLflow
- M26. Model Serving

### Tier 7 — Applications & Sharing
- M27. Databricks Apps
- M28. Apps Permissions
- M29. Lakebase
- M30. Marketplace + Delta Sharing

### Tier 8 — Developer Tooling ★
- M31. Databricks CLI
- M32. Databricks SDK
- M33. Databricks Connect
- M34. IDE Integration
- M35. **DAB Deep Dive** (15 Lab)
- M36. Terraform Provider
- M37. REST API + Webhook
- M38. CI/CD
- M39. Secret Management
- M40. Testing & Quality

### Appendix — Account Console 관리 (Admin 트랙)
- A. Account Console 개요
- B. Identity Management
- C. Workspace 관리
- D. UC Metastore Admin
- E. Cloud Resources (AWS)
- F. Logs & Audit
- G. Budget & Cost
- H. Marketplace Provider
- I. Account API 자동화

## 🚀 시작하기

1. [Prerequisites](./prerequisites) — 사전 준비 확인
2. M0 부터 순서대로 진행
3. 권한 Lab은 두 번째 사용자/SP가 필요 (M1.3, M1.5에서 생성)
"""

PREREQUISITES = """---
title: "Prerequisites — 사전 준비"
---

> 🚧 작성 예정.

## 필요한 것

(작성 예정)

## 환경 체크리스트

- [ ] Databricks Account (Free Trial 또는 회사 계정)
- [ ] Workspace 접근 가능
- [ ] Account Admin 또는 Workspace Admin (일부 Lab만)
- [ ] 두 번째 테스트 사용자 또는 Service Principal (권한 Lab용)
- [ ] Modern Browser (Chrome / Edge / Safari 최신)
- [ ] (선택) Databricks CLI 설치
"""

APPENDIX_OVERVIEW = """---
title: "Appendix — Account Console 관리"
---

> 🚧 작성 예정.

본 Appendix는 **Account Admin / Cloud Admin** 관점의 관리 작업을 다룹니다.
Workspace 외부 (`accounts.cloud.databricks.com`) 에서 수행하는 작업.

## 구성

- A. Account Console 개요
- B. Identity Management — User / Group / SP / SSO / SCIM
- C. Workspace 관리
- D. UC Metastore Admin
- E. Cloud Resources (AWS 중심)
- F. Logs & Audit
- G. Budget & Cost
- H. Marketplace Provider
- I. Account API 자동화
"""


def write_if_new(path: Path, content: str):
    """파일이 없을 때만 생성. 기존 파일은 덮어쓰지 않음."""
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def make_lab(num: str, title: str) -> str:
    return LAB_TEMPLATE.format(num=num, title=title)


def make_module_overview(title: str, subtitle: str, labs) -> str:
    lab_list = "\n".join(f"- Lab {num} — {t}" for num, _, t in labs)
    return MODULE_OVERVIEW_TEMPLATE.format(title=title, subtitle=subtitle, lab_list=lab_list)


def build_skeleton():
    WORKSHOP_DIR.mkdir(parents=True, exist_ok=True)

    # Root pages
    write_if_new(WORKSHOP_DIR / "overview.mdx", WORKSHOP_OVERVIEW)
    write_if_new(WORKSHOP_DIR / "prerequisites.mdx", PREREQUISITES)

    # Main modules
    for mod in MODULES:
        d = WORKSHOP_DIR / f"{mod['num']}-{mod['slug']}"
        d.mkdir(parents=True, exist_ok=True)
        write_if_new(d / "overview.mdx",
                     make_module_overview(mod["title"], mod["subtitle"], mod["labs"]))
        for num, slug, title in mod["labs"]:
            write_if_new(d / f"{slug}.mdx", make_lab(num, title))

    # Appendix
    app_dir = WORKSHOP_DIR / "appendix"
    app_dir.mkdir(parents=True, exist_ok=True)
    write_if_new(app_dir / "overview.mdx", APPENDIX_OVERVIEW)

    for mod in APPENDIX:
        d = app_dir / mod["slug"]
        d.mkdir(parents=True, exist_ok=True)
        write_if_new(d / "overview.mdx",
                     make_module_overview(mod["title"], mod["subtitle"], mod["labs"]))
        for num, slug, title in mod["labs"]:
            write_if_new(d / f"{slug}.mdx", make_lab(num, title))

    print(f"✅ 디렉토리/파일 생성 완료: {WORKSHOP_DIR}")


def docs_json_path(mod_num: str, mod_slug: str, lab_slug: str | None = None) -> str:
    if lab_slug is None:
        return f"blog/dbx-workshop/{mod_num}-{mod_slug}/overview"
    return f"blog/dbx-workshop/{mod_num}-{mod_slug}/{lab_slug}"


def appendix_path(mod_slug: str, lab_slug: str | None = None) -> str:
    if lab_slug is None:
        return f"blog/dbx-workshop/appendix/{mod_slug}/overview"
    return f"blog/dbx-workshop/appendix/{mod_slug}/{lab_slug}"


def build_tab():
    """docs.json 의 navigation.tabs 에 'Databricks Workshop' 탭 추가 (없을 때만)."""
    with DOCS_JSON.open() as f:
        docs = json.load(f)

    tabs = docs["navigation"]["tabs"]
    for t in tabs:
        if t.get("tab") == "Databricks Workshop":
            print("ℹ️  'Databricks Workshop' 탭이 이미 존재. 새로 추가하지 않음.")
            return

    groups = []

    # Intro group
    groups.append({
        "group": "시작하기",
        "pages": [
            "blog/dbx-workshop/overview",
            "blog/dbx-workshop/prerequisites",
        ],
    })

    # Tier groups
    tier_groups = [
        ("Tier 1 — Foundation",                ["00", "01", "02"]),
        ("Tier 2 — Notebook",                  ["03"]),
        ("Tier 3 — Unity Catalog Deep Dive",   ["04", "05", "06", "07", "08", "09", "10"]),
        ("Tier 4 — Data Engineering",          ["11", "12", "13", "14"]),
        ("Tier 5 — Analytics & BI",            ["15", "16", "17", "18", "19"]),
        ("Tier 6 — AI / ML",                   ["20", "21", "22", "23", "24", "25", "26"]),
        ("Tier 7 — Applications & Sharing",    ["27", "28", "29", "30"]),
        ("Tier 8 — Developer Tooling",         ["31", "32", "33", "34", "35", "36", "37", "38", "39", "40"]),
        ("Cleanup",                            ["99"]),
    ]

    mod_by_num = {m["num"]: m for m in MODULES}

    for tier_name, mod_nums in tier_groups:
        tier_pages = []
        for num in mod_nums:
            mod = mod_by_num[num]
            mod_pages = [docs_json_path(mod["num"], mod["slug"])]  # overview
            for _, lab_slug, _ in mod["labs"]:
                mod_pages.append(docs_json_path(mod["num"], mod["slug"], lab_slug))
            tier_pages.append({
                "group": mod["title"],
                "pages": mod_pages,
            })
        groups.append({"group": tier_name, "pages": tier_pages})

    # Appendix group
    appendix_pages = ["blog/dbx-workshop/appendix/overview"]
    appendix_subgroups = []
    for mod in APPENDIX:
        mod_pages = [appendix_path(mod["slug"])]  # overview
        for _, lab_slug, _ in mod["labs"]:
            mod_pages.append(appendix_path(mod["slug"], lab_slug))
        appendix_subgroups.append({
            "group": mod["title"],
            "pages": mod_pages,
        })

    groups.append({
        "group": "Appendix — Account Console 관리",
        "pages": appendix_pages + appendix_subgroups,
    })

    new_tab = {"tab": "Databricks Workshop", "groups": groups}
    tabs.append(new_tab)

    with DOCS_JSON.open("w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("✅ docs.json 에 'Databricks Workshop' 탭 추가 완료")


if __name__ == "__main__":
    build_skeleton()
    build_tab()
    print("\n🎉 Workshop 껍데기 생성 완료")
