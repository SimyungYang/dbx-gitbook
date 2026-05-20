"""
Lab별 콘텐츠 데이터 — 각 Lab의 핵심 코드 / UI 단계 / 옵션 등.

키: Lab 번호 (예: "5.4")
값:
  code_lang: sql / python / bash / yaml / hcl / text
  code:      샘플 코드 (작동하는 완성품)
  ui_steps:  UI 단계 리스트 [(설명, 스크린샷 파일명) ...]
  options:   [(옵션, 타입, 기본, 설명), ...]
  what:      "이 기능은 무엇이고 언제 쓰나" — 2-4문장
  validation: 체크리스트
  errors:    [(에러, 원인, 해결), ...]
  cleanup:   Cleanup 코드/설명
  duration:  소요 시간
  difficulty: ⭐ ~ ⭐⭐⭐
  prereq:    선행 Lab 리스트

데이터에 없는 키는 빌더가 기본값으로 채움.
"""

LAB_DATA = {

    # ====================================================================
    # M0 — Workspace Tour
    # ====================================================================
    "0.1": {
        "duration": "5분", "difficulty": "⭐",
        "what": "Databricks Workspace에 처음 접속하는 방법과 URL 패턴을 익힙니다. Workspace URL은 `https://<workspace-id>.cloud.databricks.com` (AWS) / `adb-<id>.<n>.azuredatabricks.net` (Azure) / `<region>.gcp.databricks.com` (GCP) 형식입니다.",
        "code_lang": "text",
        "code": "https://dbc-abcd1234-ef56.cloud.databricks.com    # AWS 예시\nhttps://adb-1234567890123456.7.azuredatabricks.net  # Azure 예시",
        "ui_steps": [
            ("Workspace URL을 브라우저에 입력", "step1-url-input.png"),
            ("SSO 로그인 (Google / Microsoft / Okta)", "step2-sso-login.png"),
            ("Welcome 화면에서 좌측 사이드바 확인", "step3-welcome.png"),
        ],
        "validation": ["좌측 사이드바에 Workspace / Catalog / Compute 메뉴가 보임", "우상단에 본인 이메일 표시"],
        "errors": [
            ("403 Forbidden", "Workspace에 사용자가 할당되지 않음", "Account Admin에게 Workspace 할당 요청 — Appendix C.4"),
            ("SSO 로그인 무한 루프", "브라우저 쿠키 / 시크릿 모드 충돌", "쿠키 삭제 후 재시도"),
        ],
        "cleanup": "별도 정리 불필요.",
    },
    "0.2": {
        "duration": "5분", "difficulty": "⭐",
        "what": "Workspace 좌측 사이드바의 모든 메뉴를 한 번씩 클릭해 위치를 익힙니다. 각 메뉴는 다음 모듈에서 상세 다룹니다.",
        "code_lang": "text",
        "code": "Workspace      — Notebook, 폴더, Git Folder\nCatalog        — Unity Catalog Explorer\nCompute        — Cluster, SQL Warehouse, Serverless\nJobs & Pipelines — Job, Lakeflow Pipeline\nSQL            — SQL Editor, Query, Alert, Dashboard\nMachine Learning — MLflow Experiment, Models, Serving\nApps           — Databricks Apps\nGenie          — Genie Spaces",
        "ui_steps": [
            ("좌측 사이드바 펼치기 (≡ 아이콘)", "step1-sidebar-expand.png"),
            ("각 메뉴 클릭하며 첫 화면 확인", "step2-menu-tour.png"),
            ("우상단 사용자 아이콘 → Settings 확인", "step3-user-menu.png"),
        ],
        "validation": ["8개 이상의 메뉴를 모두 한 번씩 열어봄"],
        "errors": [("일부 메뉴가 회색 처리됨", "Workspace 권한 부족", "Workspace Admin에게 권한 요청")],
        "cleanup": "별도 정리 불필요.",
    },
    "0.3": {
        "duration": "8분", "difficulty": "⭐",
        "what": "Personal Access Token, Git Provider, SSH Public Key 등 사용자 개인 설정을 확인합니다. 후속 Lab에서 CLI/SDK/Git 통합에 사용합니다.",
        "code_lang": "text",
        "code": "Settings 메뉴에서 확인:\n- Personal Access Tokens (PAT)\n- Linked Accounts (GitHub / GitLab / Azure DevOps)\n- SSH Public Keys (Cluster SSH 디버깅용)\n- Notebook Editor preferences",
        "ui_steps": [
            ("우상단 사용자 아이콘 → Settings", "step1-settings.png"),
            ("Developer 탭 → Access Tokens", "step2-pat-tab.png"),
            ("Linked Accounts → Git Provider 연결 (선택)", "step3-git-link.png"),
        ],
        "validation": ["Settings 페이지 진입 성공", "Developer 탭이 보임"],
        "errors": [("Access Tokens 탭이 없음", "Workspace Admin이 PAT 비활성화함", "Admin에게 PAT 정책 확인 요청 (Appendix B.10)")],
        "cleanup": "별도 정리 불필요.",
    },
    "0.4": {
        "duration": "3분", "difficulty": "⭐",
        "what": "Account ID와 Workspace Region을 확인합니다. 모든 API/CLI 호출에서 자주 사용됩니다.",
        "code_lang": "bash",
        "code": "# Workspace URL에서 자동 추출\necho $DATABRICKS_HOST | sed 's|https://||'\n# Account ID는 Account Console (accounts.cloud.databricks.com)에서 확인",
        "ui_steps": [
            ("우상단 본인 이메일 클릭 → 워크스페이스 이름 확인", "step1-workspace-name.png"),
            ("URL bar에서 Workspace ID 추출 (예: dbc-xxx)", "step2-url-id.png"),
            ("Account Console (별창)에서 Account ID 복사", "step3-account-id.png"),
        ],
        "validation": ["Workspace ID 메모", "Account ID 메모", "Region 메모 (예: ap-northeast-2)"],
        "errors": [("Account Console 진입 불가", "Account Admin 권한 없음", "Account Admin에게 문의 — Appendix A 참조")],
        "cleanup": "별도 정리 불필요.",
    },
    "0.5": {
        "duration": "10분", "difficulty": "⭐⭐",
        "what": "Databricks의 3-tier Admin 모델을 이해합니다. **Account Admin** > **Metastore Admin** > **Workspace Admin** 순으로 권한 범위가 다릅니다.",
        "code_lang": "text",
        "code": "Account Admin   : Account-level (모든 Workspace, Metastore, Cloud Resource)\n                  - Workspace 생성/삭제\n                  - User/SP/Group 생성\n                  - Audit Log Delivery\n                  - Compliance Profile\n\nMetastore Admin : UC Metastore (한 Region 내 모든 Catalog)\n                  - Catalog/Schema/Table 등 모든 UC 객체 SUPER USER\n                  - Storage Credential / External Location 생성\n                  - System Tables 권한 부여\n\nWorkspace Admin : 단일 Workspace 내 모든 권한\n                  - Cluster Policy / SQL Warehouse 관리\n                  - 모든 사용자 노트북 접근\n                  - 그러나 UC 객체 권한은 별도",
        "ui_steps": [
            ("본인이 어떤 Admin 권한을 가졌는지 확인", "step1-my-admin-tier.png"),
            ("Account Admin: accounts.cloud.databricks.com 접근 가능", "step2-account-console.png"),
            ("Workspace Admin: Admin Settings (워크스페이스 내) 접근", "step3-workspace-admin.png"),
        ],
        "validation": ["3-tier Admin 모델 이해", "본인의 권한 tier 확인"],
        "errors": [],
        "cleanup": "별도 정리 불필요.",
    },
    "0.6": {
        "duration": "5분", "difficulty": "⭐",
        "what": "Identity Federation은 Account-level User/Group을 Workspace에 자동 할당하는 기능입니다. 비활성화면 Workspace마다 수동 할당이 필요합니다.",
        "code_lang": "text",
        "code": "Identity Federation 활성 (권장)\n  → User/Group을 Account Console에서 만들면 자동으로 모든 Workspace에 노출됨\n  → Workspace Admin은 \"할당\" 만 (생성 X)\n\nIdentity Federation 비활성 (legacy)\n  → User/Group을 각 Workspace에서 별도 생성\n  → 동일 User가 Workspace마다 다른 ID",
        "ui_steps": [
            ("Account Console → Settings → User Management Settings", "step1-account-settings.png"),
            ("\"Identity Federation\" 상태 확인 — Enabled / Disabled", "step2-federation-status.png"),
        ],
        "validation": ["Federation 상태 메모"],
        "errors": [],
        "cleanup": "별도 정리 불필요.",
    },

    # ====================================================================
    # M1 — Identity
    # ====================================================================
    "1.1": {
        "duration": "5분", "difficulty": "⭐", "prereq": ["0.5"],
        "what": "Account Console에서 새 User를 추가합니다. Workshop 권한 검증에 사용할 두 번째 사용자를 만듭니다.",
        "code_lang": "text",
        "code": "Account Console → User management → Users → \"Add user\"\n  - First name: Workshop\n  - Last name: TestUser\n  - Email: workshop-test@<your-domain>.com",
        "ui_steps": [
            ("accounts.cloud.databricks.com 접속", "step1-account-console.png"),
            ("User management → Users 탭", "step2-users-tab.png"),
            ("Add user → 이메일 입력 → Send invite", "step3-invite-user.png"),
        ],
        "validation": ["사용자에게 초대 메일이 전송됨", "Users 목록에 새 사용자 표시"],
        "errors": [
            ("이메일이 이미 존재", "다른 Account에 등록됨 또는 동명 이인 존재", "다른 이메일 사용"),
            ("도메인 정책 위반", "Allowed Email Domain 제약", "Account Admin에게 도메인 추가 요청"),
        ],
        "cleanup": "Workshop 종료 시 User → 메뉴 → Deactivate (Appendix B.2)",
    },
    "1.2": {
        "duration": "5분", "difficulty": "⭐", "prereq": ["1.1"],
        "what": "Account-level Group을 만들어 권한을 그룹 단위로 관리합니다. Workshop 동안 사용할 `workshop-users` Group을 생성합니다.",
        "code_lang": "text",
        "code": "Account Console → User management → Groups → Add group\n  Name: workshop-users\n  Members:\n    - workshop-test@<your-domain>.com (Lab 1.1에서 만든 User)\n    - 본인 (Owner)",
        "ui_steps": [
            ("User management → Groups 탭", "step1-groups-tab.png"),
            ("Add group → Name: workshop-users", "step2-add-group.png"),
            ("Members 탭에서 User 추가", "step3-add-members.png"),
        ],
        "validation": ["Group이 생성됨", "Group 멤버에 본인과 테스트 User가 보임"],
        "errors": [("Group name already exists", "동명 Group 존재", "다른 이름 사용 (예: workshop-users-2026)")],
        "cleanup": "Account Console → Groups → workshop-users → Delete",
    },
    "1.3": {
        "duration": "8분", "difficulty": "⭐⭐",
        "what": "Service Principal (SP)은 사람이 아닌 자동화/앱이 사용하는 ID입니다. CI/CD, Job 실행, SDK 자동화에 필수입니다.",
        "code_lang": "bash",
        "code": "# CLI로 SP 생성\ndatabricks account service-principals create --json '{\n  \"display_name\": \"workshop-sp\",\n  \"active\": true\n}'\n\n# 또는 Account Console UI에서 생성",
        "ui_steps": [
            ("Account Console → User management → Service principals", "step1-sp-tab.png"),
            ("Add service principal → Name: workshop-sp", "step2-add-sp.png"),
            ("SP의 Application ID 복사 (이후 Lab에서 사용)", "step3-app-id.png"),
        ],
        "validation": ["SP가 목록에 표시", "Application ID (UUID) 메모"],
        "errors": [("권한 거부", "Account Admin 권한 필요", "Account Admin에게 요청")],
        "cleanup": "Service principals → workshop-sp → Delete",
    },
    "1.4": {
        "duration": "5분", "difficulty": "⭐⭐", "prereq": ["1.3"],
        "what": "SP의 OAuth Secret을 발급해 M2M (Machine-to-Machine) 인증에 사용합니다. CLI/SDK가 PAT 대신 OAuth로 인증할 때 필요합니다.",
        "code_lang": "bash",
        "code": "# CLI로 OAuth Secret 발급\ndatabricks account service-principal-secrets create --service-principal-id <APP-ID>\n\n# 응답에 secret 포함 — 한 번만 표시되므로 즉시 저장\n# {\n#   \"client_id\": \"...\",\n#   \"secret\": \"dose-...\",\n#   \"create_time\": \"...\"\n# }",
        "ui_steps": [
            ("Service principal 상세 → Secrets 탭", "step1-sp-secrets.png"),
            ("Generate secret → Lifetime 설정", "step2-generate.png"),
            ("Secret 값 복사 (한 번만 표시!)", "step3-secret-shown.png"),
        ],
        "validation": ["Secret 값을 안전한 곳에 저장 (Secret Manager 권장)"],
        "errors": [("Secret을 잃어버림", "다시 표시되지 않음", "새 Secret 발급 (기존은 폐기)")],
        "cleanup": "사용 후 Secret revoke (Secret 옆 ⋯ → Revoke)",
    },
    "1.5": {
        "duration": "5분", "difficulty": "⭐", "prereq": ["1.1"],
        "what": "Identity Federation이 비활성화된 경우, Lab 1.1에서 만든 User를 Workspace에 수동 할당합니다. 활성화 상태면 자동 할당되므로 이 단계는 skip 가능.",
        "code_lang": "text",
        "code": "Account Console → Workspaces → <your-workspace> → Permissions → Add user\n  User: workshop-test@<your-domain>.com\n  Role: User (또는 Workspace Admin)",
        "ui_steps": [
            ("Account Console → Workspaces 메뉴", "step1-workspaces.png"),
            ("본인의 Workspace 클릭 → Permissions 탭", "step2-ws-permissions.png"),
            ("Add user → 테스트 User 검색 → 추가", "step3-add-user.png"),
        ],
        "validation": ["테스트 User가 Workspace에 접속 가능"],
        "errors": [("User not found", "User가 Account에 추가되지 않음", "Lab 1.1 재실행")],
        "cleanup": "Workspace Permissions → 테스트 User → Remove",
    },
    "1.6": {
        "duration": "5분", "difficulty": "⭐",
        "what": "Personal Access Token (PAT)은 본인 ID로 API를 호출할 때 사용하는 토큰입니다. CLI/SDK 기본 인증 수단.",
        "code_lang": "bash",
        "code": "# Workspace UI에서 PAT 발급 후 CLI 설정\nexport DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com\nexport DATABRICKS_TOKEN=dapi...........\n\ndatabricks workspace list /",
        "ui_steps": [
            ("우상단 사용자 → Settings → Developer 탭", "step1-developer-tab.png"),
            ("Access tokens → Generate new token", "step2-new-token.png"),
            ("Comment / Lifetime 입력 → Generate → Token 복사", "step3-token-copy.png"),
        ],
        "validation": ["CLI에서 `databricks workspace list /` 성공"],
        "errors": [("PAT 발급 버튼 없음", "Workspace Admin이 PAT 비활성화", "Admin에게 활성화 요청")],
        "cleanup": "Developer 탭 → Token Revoke",
    },
    "1.7": {
        "duration": "5분", "difficulty": "⭐⭐",
        "what": "SAML 2.0 기반 SSO는 Account Admin이 Account Console에서 설정합니다. 본 Lab은 UI 위치만 확인 (실제 설정은 Appendix B.6).",
        "code_lang": "text",
        "code": "Account Console → Settings → Security and compliance → Single sign-on (SAML)\n  - SSO URL\n  - Identity Provider Entity ID\n  - x.509 Certificate",
        "ui_steps": [
            ("Account Console → Settings → Security", "step1-security-settings.png"),
            ("Single sign-on 섹션 확인", "step2-sso-section.png"),
            ("현재 설정 (Enabled / Disabled) 확인", "step3-sso-status.png"),
        ],
        "validation": ["SSO 설정 페이지 확인"],
        "errors": [],
        "cleanup": "변경 사항 없음 (조회만).",
    },
    "1.8": {
        "duration": "5분", "difficulty": "⭐⭐",
        "what": "SCIM (System for Cross-domain Identity Management)은 IdP (Okta/Azure Entra)에서 User/Group을 자동 프로비저닝합니다. 본 Lab은 UI만 확인.",
        "code_lang": "text",
        "code": "Account Console → Settings → User Provisioning (SCIM)\n  - SCIM endpoint URL\n  - SCIM token (Bearer)\n  - Mapping rules (User attribute → Databricks)",
        "ui_steps": [
            ("Account Console → Settings → User Provisioning", "step1-scim-tab.png"),
            ("SCIM endpoint URL과 토큰 확인", "step2-scim-endpoint.png"),
        ],
        "validation": ["SCIM 설정 페이지 확인"],
        "errors": [],
        "cleanup": "변경 사항 없음 (조회만).",
    },

    # ====================================================================
    # M2 — Compute
    # ====================================================================
    "2.1": {
        "duration": "5분", "difficulty": "⭐",
        "what": "Serverless Compute는 Databricks가 관리하는 컴퓨트로, 클러스터를 직접 만들 필요 없이 노트북에 즉시 attach 가능합니다.",
        "code_lang": "python",
        "code": "# 노트북 우상단 \"Connect\" → \"Serverless\" 선택\n# 코드 셀에서 즉시 실행 가능\n\nspark.sql(\"SELECT current_user(), current_timestamp()\").show()",
        "ui_steps": [
            ("새 노트북 만들기 (Workspace → Create → Notebook)", "step1-new-notebook.png"),
            ("우상단 Connect → Serverless 선택", "step2-connect-serverless.png"),
            ("첫 셀에 코드 입력 후 Shift+Enter 실행", "step3-first-cell.png"),
        ],
        "validation": ["코드 실행 성공", "결과 1 row 반환"],
        "errors": [
            ("Serverless not available", "Region에서 Serverless 미지원 또는 미활성", "Workspace Admin에게 활성화 요청"),
            ("Cluster start timeout", "Serverless 콜드 스타트 (드물게 30초+)", "재시도"),
        ],
        "cleanup": "Serverless는 idle 시 자동 종료 (별도 정리 불필요).",
    },
    "2.2": {
        "duration": "10분", "difficulty": "⭐⭐",
        "what": "Classic All-Purpose Cluster는 고객 VPC 내 EC2에서 실행되는 전통적인 클러스터입니다. Spark 디버깅, GPU 워크로드, 특수 라이브러리 필요 시 사용.",
        "code_lang": "text",
        "code": "Compute → Create compute → All-purpose compute\n  Name:                 workshop-cluster\n  Policy:               Unrestricted\n  Access mode:          Single user (또는 Shared)\n  Databricks runtime:   15.4 LTS (Photon)\n  Node type:            i3.xlarge\n  Autoscale:            min 2, max 4\n  Auto termination:     60 minutes",
        "ui_steps": [
            ("좌측 사이드바 → Compute → Create compute", "step1-create-compute.png"),
            ("All-purpose compute 선택", "step2-all-purpose.png"),
            ("설정 입력 후 Create cluster", "step3-cluster-config.png"),
            ("클러스터 상태 RUNNING 확인", "step4-running.png"),
        ],
        "validation": ["Cluster State = RUNNING", "Driver/Worker 노드 IP 확인 가능"],
        "errors": [
            ("Cluster failed: INSTANCE_POOL_EXHAUSTED", "EC2 quota 초과", "다른 instance type 시도 또는 AWS quota 증액"),
            ("DBR version not available", "Region에서 미지원", "다른 LTS 버전 선택"),
        ],
        "cleanup": "Compute → workshop-cluster → ⋯ → Delete",
    },
    "2.3": {
        "duration": "10분", "difficulty": "⭐⭐",
        "what": "클러스터 생성 시 사용 가능한 모든 옵션을 살펴봅니다. Photon, Autoscale, Access mode가 성능과 비용에 가장 큰 영향.",
        "code_lang": "text",
        "code": "주요 옵션:\n  Databricks Runtime  — LTS 권장 (15.4 LTS / 14.3 LTS)\n  Photon              — 분석 워크로드 2-3x 빠름 (ETL/SQL에 강력 권장)\n  Access Mode\n    - Single user      : 한 사용자 전용, UC 모든 기능, Python/Scala\n    - Shared           : 다중 사용자, UC 지원, Python/SQL만\n    - No isolation     : Legacy (UC 미지원)\n  Autoscaling          — 부하에 따라 worker 자동 조정\n  Auto termination     — Idle 시 자동 종료 (비용 절감 필수)\n  Cluster tags         — 비용 추적용 (env, team, project)",
        "ui_steps": [
            ("Create compute 화면에서 각 옵션 hover", "step1-options-hover.png"),
            ("Advanced options 펼치기 (Tags, Spark config, Init scripts)", "step2-advanced.png"),
            ("Custom tags 추가 (예: env=workshop)", "step3-tags.png"),
        ],
        "validation": ["모든 옵션 의미 이해"],
        "errors": [],
        "cleanup": "Lab 2.2의 cluster와 동일.",
    },
    "2.4": {
        "duration": "10분", "difficulty": "⭐⭐⭐",
        "what": "Cluster Policy는 사용자가 클러스터를 만들 때 강제할 규칙입니다. 비용 제한, 보안 강제, 표준화에 사용.",
        "code_lang": "text",
        "code": "{\n  \"spark_version\": {\n    \"type\": \"allowlist\",\n    \"values\": [\"15.4.x-scala2.12\", \"14.3.x-scala2.12\"]\n  },\n  \"node_type_id\": {\n    \"type\": \"allowlist\",\n    \"values\": [\"i3.xlarge\", \"i3.2xlarge\"]\n  },\n  \"autotermination_minutes\": {\n    \"type\": \"range\",\n    \"maxValue\": 60,\n    \"defaultValue\": 30\n  },\n  \"num_workers\": {\n    \"type\": \"range\",\n    \"maxValue\": 8\n  }\n}",
        "ui_steps": [
            ("Compute → Policies 탭", "step1-policies-tab.png"),
            ("Create policy → Name: workshop-policy", "step2-create-policy.png"),
            ("Definition에 JSON 붙여넣기 → Create", "step3-paste-json.png"),
            ("정책에 사용자/그룹 권한 부여", "step4-policy-permission.png"),
        ],
        "validation": ["사용자가 클러스터 생성 시 정책 제약 적용됨"],
        "errors": [("Invalid policy JSON", "JSON 구문 오류", "JSON validator로 확인")],
        "cleanup": "Policy → ⋯ → Delete",
    },
    "2.5": {
        "duration": "10분", "difficulty": "⭐⭐",
        "what": "SQL Warehouse는 BI / 분석가용 전용 컴퓨트입니다. Serverless / Pro / Classic 3종류가 있고 Photon이 항상 활성화.",
        "code_lang": "text",
        "code": "SQL → SQL Warehouses → Create SQL warehouse\n  Name:        workshop-warehouse\n  Cluster size: 2X-Small (DBU/h: 4)\n  Type:        Serverless (권장) / Pro / Classic\n  Auto stop:   10 min\n  Scaling:     min 1, max 4",
        "ui_steps": [
            ("SQL → SQL Warehouses 메뉴", "step1-sql-menu.png"),
            ("Create SQL warehouse → 옵션 설정", "step2-create-warehouse.png"),
            ("Start → 상태 Running 확인", "step3-warehouse-running.png"),
        ],
        "validation": ["Warehouse 상태 = Running", "SQL Editor에서 사용 가능"],
        "errors": [("Quota exceeded", "Serverless quota 초과", "더 작은 size 또는 Account Admin 문의")],
        "cleanup": "Warehouse → Stop → Delete",
    },
    "2.6": {
        "duration": "5분", "difficulty": "⭐",
        "what": "SQL Warehouse 3종 비교: Serverless (Databricks 관리, 가장 빠른 시작), Pro (고객 VPC, Photon 기본), Classic (legacy, Photon 옵션).",
        "code_lang": "text",
        "code": "| 항목           | Serverless           | Pro              | Classic         |\n|----------------|----------------------|------------------|-----------------|\n| 위치           | Databricks VPC       | 고객 VPC         | 고객 VPC        |\n| 시작 시간      | 수초                 | 2-5분            | 4-8분           |\n| Photon         | 항상                 | 항상             | 옵션            |\n| Predictive IO  | 항상                 | 옵션             | X               |\n| 가격           | 가장 비쌈            | 중간             | 가장 쌈         |\n| 권장 용도      | BI 대시보드, Genie   | 정기 ETL/SQL     | Legacy 호환     |",
        "ui_steps": [
            ("Create warehouse 화면에서 Type 옵션 비교", "step1-warehouse-types.png"),
            ("각 type별 가격 도구 확인 (calculator.databricks.com)", "step2-calc.png"),
        ],
        "validation": ["3종 비교 이해"],
        "errors": [],
        "cleanup": "별도 정리 불필요.",
    },
    "2.7": {
        "duration": "5분", "difficulty": "⭐",
        "what": "Job Cluster는 Job 실행 시 자동 생성/삭제되는 임시 클러스터로, All-Purpose보다 DBU 단가가 절반입니다. 운영 Job은 99% Job Cluster 사용.",
        "code_lang": "text",
        "code": "| 항목         | All-Purpose            | Job Cluster                 |\n|--------------|------------------------|-----------------------------|\n| 수명         | 사용자가 종료할 때까지 | Job 시작~종료까지           |\n| DBU 단가     | 비쌈                   | 절반                        |\n| 다중 사용자  | 가능 (Shared mode)     | 불가 (Job 전용)             |\n| 디버깅       | 좋음 (인터랙티브)      | 한정 (Run 종료 후 확인)     |\n| 비용 최적화  | Auto termination       | 자동 종료 (Job 단위)        |\n| 권장 용도    | 개발/탐색              | 운영 / 스케줄 Job           |",
        "ui_steps": [
            ("Jobs & Pipelines → 임의 Job 생성", "step1-create-job.png"),
            ("Cluster: Job cluster vs Existing cluster 옵션", "step2-cluster-choice.png"),
        ],
        "validation": ["Job Cluster 개념 이해"],
        "errors": [],
        "cleanup": "별도 정리 불필요.",
    },
    "2.8": {
        "duration": "10분", "difficulty": "⭐⭐",
        "what": "Auto-scaling이 실제로 작동하는 것을 관찰합니다. 부하를 주고 worker 수 변화를 모니터링.",
        "code_lang": "python",
        "code": "# 부하 생성 — 큰 데이터 처리\ndf = spark.range(0, 10_000_000_000).repartition(200)\ndf.groupBy((df.id % 1000).alias(\"bucket\")).count().count()\n\n# 실행 중 Compute → Cluster → Metrics 탭에서 worker 수 확인\n# 부하 종료 후 5분 이내 worker가 다시 줄어듦 (downscale)",
        "ui_steps": [
            ("위 코드를 실행 중 상태로 둠", "step1-run-load.png"),
            ("Compute → Cluster → Metrics 탭", "step2-metrics-tab.png"),
            ("Workers 수가 증가하는 그래프 확인", "step3-scale-out.png"),
            ("실행 종료 후 5분 후 다시 확인 (scale-in)", "step4-scale-in.png"),
        ],
        "validation": ["worker 수가 동적으로 변동하는 것 확인"],
        "errors": [("worker 수 변동 없음", "min == max 또는 부하가 작음", "min/max 차이 확대 + 더 큰 데이터")],
        "cleanup": "별도 정리 불필요.",
    },
    "2.9": {
        "duration": "8분", "difficulty": "⭐⭐",
        "what": "Cluster 권한 (Can Attach To / Can Restart / Can Manage)을 사용자/그룹에 부여합니다.",
        "code_lang": "text",
        "code": "Cluster 권한 종류:\n  - Can Attach To: 노트북을 cluster에 attach (실행) 가능\n  - Can Restart:   cluster 재시작 / 종료 가능\n  - Can Manage:    설정 변경, 권한 부여 가능 (Admin)",
        "ui_steps": [
            ("Cluster 페이지 → ⋯ → Permissions", "step1-cluster-permissions.png"),
            ("Add → workshop-users group → Can Attach To 선택", "step2-grant.png"),
            ("Save", "step3-save.png"),
        ],
        "validation": ["테스트 User가 cluster에 attach 가능"],
        "errors": [("Workspace Admin 권한 필요", "본인이 Workspace Admin이 아님", "Workspace Admin에게 요청")],
        "cleanup": "Permissions → 권한 Remove",
    },
    "2.10": {
        "duration": "3분", "difficulty": "⭐",
        "what": "Module 2에서 만든 모든 Compute 리소스를 정리합니다.",
        "code_lang": "bash",
        "code": "# CLI로 일괄 정리\ndatabricks clusters delete --cluster-id <CLUSTER-ID>\ndatabricks warehouses delete <WAREHOUSE-ID>\ndatabricks cluster-policies delete --policy-id <POLICY-ID>",
        "ui_steps": [
            ("Compute → 모든 클러스터 ⋯ → Delete", "step1-delete-clusters.png"),
            ("SQL Warehouses → Stop → Delete", "step2-delete-warehouse.png"),
            ("Policies → Delete", "step3-delete-policy.png"),
        ],
        "validation": ["Compute / SQL Warehouses / Policies 목록이 비어있음 (또는 Module 외 리소스만)"],
        "errors": [],
        "cleanup": "본 Lab 자체가 Cleanup입니다.",
    },
}

# 데이터가 너무 커서 일부 모듈만 명시적으로 정의했습니다.
# 나머지 Lab은 빌더가 module 카테고리 기반 자동 콘텐츠로 채웁니다.
