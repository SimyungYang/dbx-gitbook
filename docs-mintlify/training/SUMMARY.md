---
title: "Table of contents"
---


## Databricks 플랫폼

* [Databricks란?](02-databricks-overview/what-is-databricks)
  * [경쟁사 비교](02-databricks-overview/databricks-competitive)
  * [가격 모델](02-databricks-overview/databricks-pricing)
* [Databricks 아키텍처](02-databricks-overview/databricks-architecture)
* [Workspace UI 둘러보기](02-databricks-overview/workspace-ui-tour)
* [Notebook 사용법](02-databricks-overview/notebooks-basics)
  * [Notebook 고급 기능](02-databricks-overview/notebooks-advanced)
* [무료 체험 시작하기](02-databricks-overview/getting-started-trial)

## 레이크하우스 아키텍처

* [레이크하우스란?](03-lakehouse-architecture/what-is-lakehouse)
* [Delta Lake 핵심](03-lakehouse-architecture/delta-lake-fundamentals)
  * [관리형·외부·외래 테이블](03-lakehouse-architecture/managed-vs-external-tables)
  * [타임 트래블](03-lakehouse-architecture/time-travel)
  * [스키마 진화](03-lakehouse-architecture/schema-evolution)
* [Medallion 아키텍처](03-lakehouse-architecture/medallion-architecture)
* [Delta Lake 실전 운영](03-lakehouse-architecture/delta-lake-operations)
  * [Liquid Clustering](03-lakehouse-architecture/liquid-clustering)
  * [VACUUM과 OPTIMIZE](03-lakehouse-architecture/vacuum-and-optimize)
  * [Deletion Vectors](03-lakehouse-architecture/deletion-vectors)
  * [Predictive Optimization](03-lakehouse-architecture/predictive-optimization)
* [Delta Lake & Iceberg](03-lakehouse-architecture/delta-and-iceberg)
  * [UniForm (External Iceberg Reads)](03-lakehouse-architecture/uniform)

## 컴퓨트

* [Apache Spark 기초](04-compute-and-workspace/spark-basics)
* [클러스터 종류](04-compute-and-workspace/cluster-types)
* [클러스터 설정](04-compute-and-workspace/cluster-configuration)
  * [클러스터 정책](04-compute-and-workspace/cluster-policies/README)
    * [기초와 패턴](04-compute-and-workspace/cluster-policies/basics-and-patterns)
    * [권한과 설계](04-compute-and-workspace/cluster-policies/permissions-and-design)
    * [템플릿과 모니터링](04-compute-and-workspace/cluster-policies/templates-and-monitoring)
  * [Instance Pools](04-compute-and-workspace/instance-pools)
  * [Photon 엔진](04-compute-and-workspace/photon-engine)
  * [Spot 인스턴스](04-compute-and-workspace/spot-instances)
* [SQL Warehouse](04-compute-and-workspace/sql-warehouse)
* [Serverless 컴퓨트](04-compute-and-workspace/serverless-compute)

## 데이터 엔지니어링

* [데이터 엔지니어링 개요](05-data-engineering/data-engineering-overview)
  * [파이프라인 오케스트레이션 패턴](05-data-engineering/pipeline-orchestration-patterns)
* [수집 방법 선택 가이드](05-data-engineering/choosing-ingestion-method)
* [Auto Loader](05-data-engineering/auto-loader/README)
  * [Auto Loader란?](05-data-engineering/auto-loader/what-is-auto-loader)
  * [File Notification vs Directory Listing](05-data-engineering/auto-loader/file-notification-vs-directory-listing)
  * [스키마 추론과 진화](05-data-engineering/auto-loader/schema-inference)
  * [주요 옵션](05-data-engineering/auto-loader/auto-loader-options)
  * [Auto Loader 실습](05-data-engineering/auto-loader/auto-loader-hands-on/README)
    * [사전 준비와 CSV 수집 실습](05-data-engineering/auto-loader/auto-loader-hands-on/setup-and-csv)
    * [JSON 수집과 스키마 진화](05-data-engineering/auto-loader/auto-loader-hands-on/json-and-schema-evolution)
    * [SDP와 Auto Loader 통합](05-data-engineering/auto-loader/auto-loader-hands-on/sdp-integration)
    * [데이터 검증과 트러블슈팅](05-data-engineering/auto-loader/auto-loader-hands-on/validation-and-troubleshooting)
* [Structured Streaming](05-data-engineering/structured-streaming)
  * [Streaming 심화](05-data-engineering/streaming-advanced)
* [Spark Declarative Pipelines (SDP)](05-data-engineering/spark-declarative-pipelines/README)
  * [SDP란?](05-data-engineering/spark-declarative-pipelines/what-is-sdp)
  * [Streaming Tables & Materialized Views](05-data-engineering/spark-declarative-pipelines/streaming-tables-and-mvs)
  * [Expectations (데이터 품질)](05-data-engineering/spark-declarative-pipelines/expectations)
  * [파이프라인 설정](05-data-engineering/spark-declarative-pipelines/pipeline-configuration)
  * [이벤트 로그](05-data-engineering/spark-declarative-pipelines/event-log)
  * [CDC와 SCD 처리](05-data-engineering/spark-declarative-pipelines/cdc-and-scd)
  * [SDP 실습](05-data-engineering/spark-declarative-pipelines/sdp-hands-on)
* [Lakeflow Connect](05-data-engineering/lakeflow-connect/README)
  * [Lakeflow Connect란?](05-data-engineering/lakeflow-connect/what-is-lakeflow-connect)
  * [수집 파이프라인 구성](05-data-engineering/lakeflow-connect/ingestion-pipeline-setup)
  * [Lakeflow Connect 실습](05-data-engineering/lakeflow-connect/lakeflow-connect-hands-on)
* [Lakeflow Jobs](05-data-engineering/lakeflow-jobs/README)
  * [Lakeflow Jobs란?](05-data-engineering/lakeflow-jobs/what-is-lakeflow-jobs)
  * [작업 구성](05-data-engineering/lakeflow-jobs/job-configuration/README)
    * [태스크 유형과 의존성](05-data-engineering/lakeflow-jobs/job-configuration/tasks-and-dependencies)
    * [재시도, 타임아웃, 알림](05-data-engineering/lakeflow-jobs/job-configuration/retry-and-alerts)
    * [클러스터 설정과 파라미터](05-data-engineering/lakeflow-jobs/job-configuration/cluster-and-parameters)
    * [실습과 비용 최적화](05-data-engineering/lakeflow-jobs/job-configuration/hands-on-and-optimization)
  * [태스크 유형](05-data-engineering/lakeflow-jobs/task-types)
  * [조건부 태스크와 흐름 제어](05-data-engineering/lakeflow-jobs/conditional-tasks)
  * [스케줄링과 트리거](05-data-engineering/lakeflow-jobs/scheduling-and-triggers)
  * [모니터링과 알림](05-data-engineering/lakeflow-jobs/monitoring-and-alerting)

## 데이터 웨어하우징

* [Databricks SQL 개요](06-data-warehousing/databricks-sql-overview)
* [SQL 주요 기능](06-data-warehousing/sql-language-features)
  * [윈도우 함수](06-data-warehousing/window-functions)
  * [SQL 스크립팅](06-data-warehousing/sql-scripting)
  * [PIVOT과 UNPIVOT](06-data-warehousing/pivot-unpivot/README)
    * [PIVOT 기본과 UNPIVOT](06-data-warehousing/pivot-unpivot/pivot-basics)
    * [고급 패턴과 성능 최적화](06-data-warehousing/pivot-unpivot/advanced-patterns)
    * [실전 활용 사례](06-data-warehousing/pivot-unpivot/practical-examples)
* [테이블과 뷰](06-data-warehousing/tables-and-views)
  * [구체화된 뷰 (Materialized View)](06-data-warehousing/materialized-views)
* [AI 함수](06-data-warehousing/ai-functions)
* [쿼리 최적화](06-data-warehousing/query-optimization)

## Unity Catalog

* [Unity Catalog란?](07-unity-catalog/what-is-unity-catalog)
* [네임스페이스와 객체](07-unity-catalog/namespace-and-objects)
  * [외부 로케이션](07-unity-catalog/external-locations)
  * [스토리지 자격 증명](07-unity-catalog/storage-credentials)
  * [UC 함수](07-unity-catalog/functions)
* [권한 관리](07-unity-catalog/access-control)
  * [행 필터 (Row Filter)](07-unity-catalog/row-filters)
  * [컬럼 마스킹 (Column Mask)](07-unity-catalog/column-masks)
  * [태그와 ABAC](07-unity-catalog/tags)
* [데이터 리니지](07-unity-catalog/data-lineage/README)
  * [리니지 기본 개념과 시각화](07-unity-catalog/data-lineage/basics-and-visualization)
  * [활용 시나리오와 내부 동작](07-unity-catalog/data-lineage/use-cases-and-internals)
  * [영향도 분석과 거버넌스](07-unity-catalog/data-lineage/impact-analysis-and-governance)
* [Delta Sharing](07-unity-catalog/delta-sharing)
  * [Databricks Marketplace](07-unity-catalog/marketplace)
  * [Clean Rooms](07-unity-catalog/clean-rooms)
* [Volumes](07-unity-catalog/volumes/README)
  * [기본 개념과 Volume 유형](07-unity-catalog/volumes/basics-and-types)
  * [Managed vs External Volume 심화](07-unity-catalog/volumes/managed-vs-external)
  * [대용량 처리와 AI/ML 활용](07-unity-catalog/volumes/advanced-usage)
* [Metric Views (비즈니스 시맨틱)](08-ai-bi/metric-views)

## AI/BI

* [AI/BI 개요](08-ai-bi/aibi-overview)
* [AI/BI 대시보드](08-ai-bi/lakeview-dashboards)
* [Genie](08-ai-bi/genie)
* [알림과 스케줄링](08-ai-bi/alerts-and-scheduling)
* [AI/BI 아키텍처 심화](08-ai-bi/aibi-architecture)
* [하이브리드 BI 전략](08-ai-bi/hybrid-bi-strategy)

## 머신러닝

* [Databricks ML 개요](09-machine-learning/ml-on-databricks-overview)
* [ML Runtime](09-machine-learning/ml-runtime)
  * [AutoML](09-machine-learning/automl)
  * [분산 학습](09-machine-learning/distributed-training)
  * [하이퍼파라미터 튜닝](09-machine-learning/hyperparameter-tuning/README)
    * [Hyperopt와 SparkTrials](09-machine-learning/hyperparameter-tuning/hyperopt-basics)
    * [TPE 알고리즘과 SparkTrials 심화](09-machine-learning/hyperparameter-tuning/tpe-and-sparktrials)
    * [Optuna 연동과 MLflow 로깅](09-machine-learning/hyperparameter-tuning/optuna-and-mlflow)
    * [Early Stopping과 대규모 탐색 전략](09-machine-learning/hyperparameter-tuning/early-stopping-and-strategies)
* [MLflow](09-machine-learning/mlflow/README)
  * [MLflow란?](09-machine-learning/mlflow/what-is-mlflow)
  * [실험 추적](09-machine-learning/mlflow/experiment-tracking)
  * [모델 레지스트리](09-machine-learning/mlflow/model-registry/README)
    * [기본 개념과 모델 등록](09-machine-learning/mlflow/model-registry/basics-and-registration)
    * [권한 관리와 Model Serving 연동](09-machine-learning/mlflow/model-registry/permissions-and-serving)
    * [CI/CD 패턴과 거버넌스](09-machine-learning/mlflow/model-registry/cicd-and-governance)
  * [MLflow Tracing](09-machine-learning/mlflow/mlflow-tracing/README)
    * [기본 개념과 자동 트레이싱](09-machine-learning/mlflow/mlflow-tracing/basics-and-autolog)
    * [계측 방식과 프레임워크 통합](09-machine-learning/mlflow/mlflow-tracing/instrumentation-and-integration)
    * [Trace 조회와 프로덕션 모니터링](09-machine-learning/mlflow/mlflow-tracing/query-and-monitoring)
    * [프로덕션 분석과 평가 데이터 수집](09-machine-learning/mlflow/mlflow-tracing/analysis-and-evaluation)
  * [모델 평가](09-machine-learning/mlflow/mlflow-evaluation)
* [Model Serving](09-machine-learning/model-serving/README)
  * [Model Serving 개요](09-machine-learning/model-serving/model-serving-overview)
  * [Foundation Model API](09-machine-learning/model-serving/foundation-model-api)
  * [커스텀 모델 배포](09-machine-learning/model-serving/custom-model-deployment)
  * [AI Gateway](09-machine-learning/model-serving/ai-gateway)
  * [엔드포인트 모니터링](09-machine-learning/model-serving/endpoint-monitoring)
* [Feature Engineering](09-machine-learning/feature-engineering/README)
  * [Feature Engineering 개요](09-machine-learning/feature-engineering/feature-engineering-overview)
  * [피처 테이블 관리](09-machine-learning/feature-engineering/feature-table-management)
  * [실시간 피처 서빙](09-machine-learning/feature-engineering/online-serving)
* [Lakehouse Monitoring](09-machine-learning/lakehouse-monitoring)

## AI 에이전트

* [AI 에이전트란?](10-agent-development/what-is-ai-agent)
* [Vector Search](10-agent-development/vector-search)
* [RAG 파이프라인](10-agent-development/rag-pipeline)
* [에이전트 구축](10-agent-development/building-agents)
  * [도구와 UC 함수](10-agent-development/tools-and-functions)
* [에이전트 평가](10-agent-development/agent-evaluation)
* [에이전트 배포](10-agent-development/agent-deployment/README)
  * [모델 로깅과 등록](10-agent-development/agent-deployment/logging-and-registration)
  * [엔드포인트 생성과 Review App](10-agent-development/agent-deployment/endpoint-and-review)
  * [버전 관리와 모니터링](10-agent-development/agent-deployment/versioning-and-monitoring)
  * [Guardrails와 트러블슈팅](10-agent-development/agent-deployment/guardrails-and-troubleshooting)
* [Agent Bricks](10-agent-development/agent-bricks)

## Lakebase

* [Lakebase란?](11-lakebase/what-is-lakebase)
* [Lakebase 설정](11-lakebase/lakebase-setup)
* [Data Sync](11-lakebase/data-sync)
* [Apps 연동](11-lakebase/lakebase-with-apps/README)
  * [OAuth 인증과 커넥션 풀링](11-lakebase/lakebase-with-apps/auth-and-connection)
  * [프레임워크별 연결 예제](11-lakebase/lakebase-with-apps/framework-examples)
  * [성능 최적화와 CRUD 앱 예제](11-lakebase/lakebase-with-apps/optimization-and-crud)
  * [배포 및 운영](11-lakebase/lakebase-with-apps/deployment)

## 보안과 거버넌스

* [보안 개요](12-security-and-governance/security-overview)
  * [CMK 암호화](12-security-and-governance/cmk-encryption)
  * [시크릿 관리](12-security-and-governance/secret-management)
  * [감사 로그](12-security-and-governance/audit-logs)
* [인증과 접근 제어](12-security-and-governance/identity-and-access)
  * [SSO 설정](12-security-and-governance/sso-setup)
  * [SCIM 프로비저닝](12-security-and-governance/scim-provisioning)
  * [서비스 프린시펄](12-security-and-governance/service-principals)
* [네트워크 보안](12-security-and-governance/network-security)
* [시스템 테이블](12-security-and-governance/system-tables/README)
  * [개요와 주요 시스템 테이블](12-security-and-governance/system-tables/overview-and-tables)
  * [실무 활용 쿼리 모음](12-security-and-governance/system-tables/practical-queries)
  * [운영 대시보드와 활성화 방법](12-security-and-governance/system-tables/dashboard-and-setup)
* [워크스페이스 관리](12-security-and-governance/workspace-admin)

## 모범 사례

* [비용 최적화](14-best-practices/cost-optimization/README)
  * [비용 구조 이해](14-best-practices/cost-optimization/cost-structure)
  * [컴퓨트 최적화](14-best-practices/cost-optimization/compute-optimization)
  * [스토리지와 SQL Warehouse 최적화](14-best-practices/cost-optimization/storage-and-warehouse)
  * [비용 모니터링과 체크리스트](14-best-practices/cost-optimization/monitoring-and-checklist)
* [성능 최적화](14-best-practices/performance-tuning/README)
  * [Spark 쿼리 튜닝](14-best-practices/performance-tuning/spark-query-tuning)
  * [Delta Lake 성능 최적화](14-best-practices/performance-tuning/delta-lake-optimization)
  * [SQL Warehouse와 파이프라인 최적화](14-best-practices/performance-tuning/sql-warehouse-and-pipeline)
  * [ML/AI 최적화와 성능 진단](14-best-practices/performance-tuning/ml-and-diagnostics)
* [엔터프라이즈 거버넌스](14-best-practices/enterprise-governance/README)
  * [플랫폼 설계](14-best-practices/enterprise-governance/platform-design)
  * [접근 제어 설계](14-best-practices/enterprise-governance/access-control)
  * [데이터 분류 및 태깅](14-best-practices/enterprise-governance/data-classification)
  * [데이터 품질 관리와 CI/CD](14-best-practices/enterprise-governance/data-quality-cicd)

## 개발 도구

* [Databricks CLI](13-appendix/databricks-cli)
* [Declarative Automation Bundles](13-appendix/databricks-asset-bundles)
* [Databricks Apps](13-appendix/databricks-apps)
* [Databricks SDK](13-appendix/databricks-sdk)
* [Databricks Connect](13-appendix/databricks-connect)
* [REST API 활용](13-appendix/rest-api)
* [AI Dev Kit](13-appendix/ai-dev-kit)
* [Genie Code](13-appendix/genie-code)

## 부록 — 선행 지식

* [관계형 데이터베이스 기초](00-prerequisites/rdb-fundamentals)
* [데이터 모델링 — Star/Snowflake 스키마](00-prerequisites/schema-design-patterns)
* [빅데이터의 역사](00-prerequisites/bigdata-history)
* [빅데이터 생태계](00-prerequisites/bigdata-ecosystem)
* [실시간 처리 기술](00-prerequisites/realtime-processing)

## 부록 — 데이터 기초

* [데이터 엔지니어링이란?](01-data-fundamentals/what-is-data-engineering)
* [데이터 웨어하우스 vs 데이터 레이크](01-data-fundamentals/data-warehouse-vs-data-lake)
* [ETL과 ELT](01-data-fundamentals/etl-elt-basics)
* [배치 처리 vs 스트리밍 처리](01-data-fundamentals/batch-vs-streaming)
* [정형·반정형·비정형 데이터](01-data-fundamentals/structured-semi-unstructured)

## 부록 — 참고

* [용어 사전](13-appendix/glossary)
* [학습 로드맵](13-appendix/learning-path)
