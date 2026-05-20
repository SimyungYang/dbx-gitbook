# Databricks Hands-On Workshop — 마스터 플랜

> **저장일**: 2026-05-20
> **목적**: AWS Workshop 스타일의 Databricks 전체 기능 핸즈온 가이드. 기능 하나하나를 단일 Lab으로 분해해, 사용자가 직접 클릭/코드 실행하며 체감하도록 구성.
> **위치**: `docs-mintlify/blog/dbx-workshop/`
> **탭 이름**: `Databricks Workshop`

---

## 1. 컨셉

- **AWS Workshop 형식**: Module → Lab → Step-by-step
- **단일 기능 = 단일 Lab** (5–20분 분량)
- **5블록 페이지 구조**:
  1. 🧭 이 기능은 무엇이고 언제 쓰나
  2. ⚙️ 핵심 옵션 표
  3. 💻 샘플 코드 (작동하는 완성품)
  4. 🖥 UI 등가 작업 (스크린샷 포함)
  5. ✅ Validation + 🚧 자주 만나는 오류 + 🧹 Cleanup
- **권한 관리 집중**: UC RBAC/ABAC/Fine-grained, Genie 권한, Databricks One 권한, Apps OBO/SP 권한 별도 모듈
- **개발 도구**: CLI, SDK, Connect, IDE, **DAB 15 Lab**, Terraform, REST API, CI/CD, Secret, Testing
- **Account Console 관리**는 별도 Appendix (A–I)
- **고객사명 등장 금지** (일반화)

---

## 2. 전체 구조 — 7 Tier + 1 Appendix

### Tier 1 — Foundation
- **M0** Workspace Tour & Account Console (6 Lab)
- **M1** Identity 기초 — User / Group / Service Principal (8 Lab)
- **M2** Compute — Cluster / Warehouse / Serverless (10 Lab)

### Tier 2 — Notebook & Workspace
- **M3** Notebook, Workspace Files, Git (12 Lab)

### Tier 3 — Unity Catalog Deep Dive ★ 권한 집중
- **M4** UC 객체 — Catalog / Schema / Table / View / Volume / Function / Model / Connection (18 Lab)
- **M5** UC RBAC — GRANT/REVOKE, Privilege Hierarchy, Ownership (20 Lab)
- **M6** UC ABAC — Tag 기반 Policy (12 Lab)
- **M7** UC Fine-grained — Row Filter, Column Mask, Dynamic View (8 Lab)
- **M8** UC External Resources — Storage Credential, External Location, Connection (8 Lab)
- **M9** UC Audit & Lineage — System Tables, Audit Log, Column Lineage (8 Lab)
- **M10** UC Governance Boundary — Catalog Binding, Network Binding (6 Lab)

### Tier 4 — Data Engineering
- **M11** Delta Lake — CRUD, Time Travel, OPTIMIZE, CDF, Liquid Clustering, CLONE (14 Lab)
- **M12** Data Ingestion — Upload / COPY INTO / Auto Loader / Lakeflow Connect (8 Lab)
- **M13** Lakeflow Declarative Pipelines (8 Lab)
- **M14** Jobs & Workflow + Run-As / Job Permissions (10 Lab)

### Tier 5 — Analytics & BI + 권한
- **M15** DBSQL — Editor / Query / Visualization (10 Lab)
- **M16** AI/BI Dashboard + Dashboard 권한 (8 Lab)
- **M17** Genie Spaces (10 Lab)
- **M18** Genie Permissions — Space 권한 + Underlying Data 권한 (6 Lab)
- **M19** Databricks One — Persona, Default Space, Consumer 모드 (8 Lab)

### Tier 6 — AI / ML + 권한
- **M20** AI Functions (8 Lab)
- **M21** Vector Search + Endpoint/Index Permissions (8 Lab)
- **M22** Agent Bricks — KA / MAS / IE (10 Lab)
- **M23** Agent Bricks Permissions (5 Lab)
- **M24** Genie Code (6 Lab)
- **M25** MLflow Tracking / Tracing / Evaluation (12 Lab)
- **M26** Model Serving + Endpoint Permissions (8 Lab)

### Tier 7 — Applications & Sharing
- **M27** Databricks Apps (8 Lab)
- **M28** Apps Permissions — OBO 인증, App SP (6 Lab)
- **M29** Lakebase + DB 권한 (8 Lab)
- **M30** Marketplace + Delta Sharing (8 Lab)

### Tier 8 — Developer Tooling ★
- **M31** Databricks CLI (10 Lab)
- **M32** Databricks SDK (8 Lab)
- **M33** Databricks Connect (6 Lab)
- **M34** IDE Integration — VS Code / Cursor / JetBrains (6 Lab)
- **M35** **DAB Deep Dive** — Bundle, Variables, Targets, State (15 Lab)
- **M36** Terraform Provider (6 Lab)
- **M37** REST API + Webhook (6 Lab)
- **M38** CI/CD — DAB + GitHub Actions (5 Lab)
- **M39** Secret Management (4 Lab)
- **M40** Testing & Quality (5 Lab)

### Cleanup
- **M99** Final Cleanup (1 Lab)

### Appendix — Account Console 관리 (Admin 트랙)
- **A** Account Console 개요 (5 Lab)
- **B** Identity Management — SSO / SCIM / Federation (10 Lab)
- **C** Workspace 관리 (6 Lab)
- **D** UC Metastore Admin (5 Lab)
- **E** Cloud Resources (AWS) (8 Lab)
- **F** Logs & Audit Delivery (6 Lab)
- **G** Budget & Cost (5 Lab)
- **H** Marketplace Provider (4 Lab)
- **I** Account API + Terraform `mws_*` 자동화 (6 Lab)

---

## 3. 전체 규모

| 구분 | Module | Lab |
|------|--------|-----|
| Tier 1–8 (Main Track) | 41 | ~340 |
| Cleanup | 1 | 1 |
| Appendix A–I | 9 | 55 |
| **합계** | **51** | **~396** |

- Module Overview 페이지 추가: ~51개
- Workshop Overview / Prerequisites / Appendix Overview: 3개
- **총 mdx 파일 수**: ~450

---

## 4. 페이지 표준 구조 (모든 Lab 공통)

```markdown
---
title: "Lab X.Y — {제목}"
---

<Info>
**소요 시간**: ?분 | **난이도**: ⭐
**선행**: [...]
**기능 분류**: ...
</Info>

## 🧭 이 기능은 무엇이고 언제 쓰나
...

## ⚙️ 핵심 옵션
| 옵션 | 타입 | 기본 | 설명 |

## 💻 샘플 코드
```sql/python/yaml
...
```

## 🖥 UI 등가 작업
...

## ✅ Validation
...

## 🚧 자주 만나는 오류
...

## 🧹 Cleanup
...

## ➡️ 다음
[Lab X.Y+1 →]
```

---

## 5. 작성 Phase

| Phase | 범위 | Lab 수 |
|-------|------|-------|
| **A** | M0–M3 (Foundation + Notebook) | ~36 |
| **B** | M4–M10 (UC + 권한 전체) ★ 핵심 | ~80 |
| **C** | M11–M14 (Delta + Ingest + Pipeline + Jobs) | ~40 |
| **D** | M15–M19 (BI + Genie + Databricks One) | ~42 |
| **E** | M20–M26 (AI/ML) | ~57 |
| **F** | M27–M30 (Apps + Lakebase + Sharing) | ~30 |
| **G** | M31–M40 (Developer Tooling) ★ | ~71 |
| **H** | Appendix A–I | ~55 |

---

## 6. 확정 사항

1. ✅ Workshop 탭 이름: **"Databricks Workshop"**
2. ✅ 스크린샷: 텍스트 + 코드 먼저 완성, 스크린샷은 placeholder → 나중 일괄 캡처
3. ✅ 두 번째 사용자/SP: M1.3 (Service Principal) + M1.5 (Test User Workspace 할당)에서 1세트 만들어 모든 권한 Lab에서 재사용
4. ✅ Appendix E (Cloud Resources)는 Account Console UI 단계만 + 기존 AWS 가이드(`/blog/platform-setup/aws/`)로 cross-link
5. ✅ 작성 순서: Phase A → B → ... → H 순차
6. ✅ 1단계: 전체 껍데기 (디렉토리 + 빈 mdx + docs.json 등록) 일괄 생성 → 내용은 Phase별로 채움

---

## 7. 디렉토리 구조 (껍데기 생성 후)

```
docs-mintlify/blog/dbx-workshop/
├── overview.mdx
├── prerequisites.mdx
├── 00-workspace-tour/
│   ├── overview.mdx
│   ├── workspace-login.mdx
│   └── ... (6 Lab)
├── 01-identity/
├── 02-compute/
├── 03-notebook/
├── 04-uc-objects/
├── 05-uc-rbac/
├── 06-uc-abac/
├── 07-uc-fine-grained/
├── 08-uc-external-resources/
├── 09-uc-audit-lineage/
├── 10-uc-governance-boundary/
├── 11-delta-lake/
├── 12-data-ingestion/
├── 13-lakeflow-pipelines/
├── 14-jobs-workflow/
├── 15-dbsql/
├── 16-aibi-dashboard/
├── 17-genie-spaces/
├── 18-genie-permissions/
├── 19-databricks-one/
├── 20-ai-functions/
├── 21-vector-search/
├── 22-agent-bricks/
├── 23-agent-bricks-permissions/
├── 24-genie-code/
├── 25-mlflow/
├── 26-model-serving/
├── 27-databricks-apps/
├── 28-apps-permissions/
├── 29-lakebase/
├── 30-marketplace-sharing/
├── 31-databricks-cli/
├── 32-databricks-sdk/
├── 33-databricks-connect/
├── 34-ide-integration/
├── 35-dab-deep-dive/
├── 36-terraform/
├── 37-rest-api/
├── 38-cicd/
├── 39-secret-management/
├── 40-testing-quality/
├── 99-cleanup/
└── appendix/
    ├── overview.mdx
    ├── A-account-console-tour/
    ├── B-identity-management/
    ├── C-workspace-management/
    ├── D-uc-metastore-admin/
    ├── E-cloud-resources/
    ├── F-logs-audit/
    ├── G-budget-cost/
    ├── H-marketplace-provider/
    └── I-account-api-automation/
```
