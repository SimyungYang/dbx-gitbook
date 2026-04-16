-- Databricks notebook source

-- MAGIC %md
-- MAGIC # LGE Smart TV SDP Pipeline — Silver Layer
-- MAGIC
-- MAGIC Bronze → Silver 변환 로직을 Spark Declarative Pipeline(SDP)으로 구현.
-- MAGIC
-- MAGIC | 유형 | 테이블 수 |
-- MAGIC |------|----------|
-- MAGIC | Streaming Table | 6 |
-- MAGIC | Materialized View | 9 |
-- MAGIC | Quarantine (quarantine_ prefix) | 5 |
-- MAGIC | **합계** | **20** |
-- MAGIC
-- MAGIC **파이프라인:** `lge_smart_tv_pipeline_claude`
-- MAGIC **카탈로그:** `byungjun_lee_smarttv_training_catalog`
-- MAGIC **타겟 스키마:** `silver`

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver Layer — Streaming Tables (Core 3 + Additional 3)
-- MAGIC
-- MAGIC Streaming Table은 `STREAM()` 으로 Bronze를 증분 처리.
-- MAGIC 윈도우 함수(ROW_NUMBER, LEAD, LAG) 불가 → 단순 변환만 포함.

-- COMMAND ----------

-- ============================================================
-- [Temp View] viewing_sessions — 모든 레코드 (품질 필터 미적용)
-- Quarantine 분리를 위해 temp view → main + quarantine 패턴 사용
-- ============================================================
CREATE TEMPORARY STREAMING LIVE VIEW _viewing_sessions_all
AS
SELECT
  v.event_id, v.device_id, v.session_start, v.session_end, v.duration_sec,
  ROUND(v.duration_sec / 60.0, 1) AS duration_min,
  v.content_source, v.app_id, v.channel_number, v.channel_name, v.broadcast_type,
  COALESCE(NULLIF(TRIM(v.program_title), ''),
    CASE WHEN v.app_id IS NOT NULL THEN CONCAT('App:', v.app_id) ELSE 'Unknown' END
  ) AS program_title,
  v.genre, v.signal_strength_dbm, v.signal_quality_pct, v.tune_latency_ms, v.resolution,
  COALESCE(NULLIF(TRIM(v.hdr_type), ''), 'SDR') AS hdr_type,
  HOUR(v.session_start) AS viewing_hour,
  CASE WHEN HOUR(v.session_start) BETWEEN 19 AND 23 THEN true ELSE false END AS is_primetime,
  CASE
    WHEN v.duration_sec < 60 THEN 'zap'
    WHEN v.duration_sec < 600 THEN 'short'
    WHEN v.duration_sec < 3600 THEN 'medium'
    ELSE 'long'
  END AS viewing_category,
  CAST(v.session_start AS DATE) AS event_date
FROM STREAM(byungjun_lee_smarttv_training_catalog.bronze.viewing_logs) v
INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev
  ON v.device_id = dev.device_id;

-- COMMAND ----------

-- ============================================================
-- Silver 1: viewing_sessions (Streaming Table)
-- 소스: bronze.viewing_logs
-- Expectation: duration_sec > 0 AND duration_sec <= 86400
-- ============================================================
CREATE OR REFRESH STREAMING TABLE viewing_sessions (
  CONSTRAINT valid_duration EXPECT (duration_sec > 0 AND duration_sec <= 86400) ON VIOLATION DROP ROW,
  CONSTRAINT valid_session EXPECT (session_end >= session_start) ON VIOLATION DROP ROW
)
COMMENT 'Viewing sessions — streaming ingestion, duration validated, primetime/hour enriched'
AS SELECT * FROM STREAM(LIVE._viewing_sessions_all);

-- COMMAND ----------

-- ============================================================
-- Quarantine: viewing_sessions — duration 위반 레코드
-- ============================================================
CREATE OR REFRESH STREAMING TABLE quarantine_viewing_sessions
COMMENT 'Quarantine — viewing_sessions: duration 또는 session 시간 위반 레코드'
AS
SELECT *, 'valid_duration OR valid_session' AS violated_rule, current_timestamp() AS quarantined_at
FROM STREAM(LIVE._viewing_sessions_all)
WHERE NOT (duration_sec > 0 AND duration_sec <= 86400)
   OR NOT (session_end >= session_start);

-- COMMAND ----------

-- ============================================================
-- [Temp View] streaming_quality — 모든 레코드
-- ============================================================
CREATE TEMPORARY STREAMING LIVE VIEW _streaming_quality_all
AS
SELECT
  v.event_id, v.device_id, v.timestamp, v.event_type, v.app_id,
  v.buffer_level_pct, v.buffer_duration_ms, v.stall_count, v.stall_duration_total_ms,
  v.current_bitrate_kbps, v.target_bitrate_kbps,
  COALESCE(NULLIF(TRIM(v.cdn_host), ''), 'local_playback') AS cdn_host,
  v.latency_ms, v.dns_resolve_ms,
  CASE
    WHEN v.current_bitrate_kbps >= 15000 THEN '4K'
    WHEN v.current_bitrate_kbps >= 5000  THEN 'FHD'
    WHEN v.current_bitrate_kbps >= 2500  THEN 'HD'
    ELSE 'SD'
  END AS quality_tier,
  CASE WHEN v.latency_ms > 10000 THEN true ELSE false END AS is_outlier,
  CASE WHEN UPPER(v.event_type) LIKE '%BUFFER%' OR v.stall_count > 0 THEN true ELSE false END AS is_buffering,
  CASE
    WHEN v.target_bitrate_kbps > 0 AND v.current_bitrate_kbps < v.target_bitrate_kbps * 0.5 THEN true
    ELSE false
  END AS is_quality_degraded,
  CASE
    WHEN v.buffer_duration_ms > 0 AND v.stall_duration_total_ms IS NOT NULL THEN
      ROUND(v.stall_duration_total_ms * 100.0 / v.buffer_duration_ms, 2)
    ELSE 0.0
  END AS stall_ratio_pct,
  CAST(v.timestamp AS DATE) AS event_date
FROM STREAM(byungjun_lee_smarttv_training_catalog.bronze.streaming_buffer_events) v
INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev
  ON v.device_id = dev.device_id;

-- COMMAND ----------

-- ============================================================
-- Silver 4: streaming_quality (Streaming Table)
-- Expectation: latency_ms > 0
-- ============================================================
CREATE OR REFRESH STREAMING TABLE streaming_quality (
  CONSTRAINT valid_latency EXPECT (latency_ms > 0) ON VIOLATION DROP ROW
)
COMMENT 'Streaming quality — latency validated, quality tiered, buffering ratio calculated'
AS SELECT * FROM STREAM(LIVE._streaming_quality_all);

-- COMMAND ----------

-- ============================================================
-- Quarantine: streaming_quality — latency 위반 레코드
-- ============================================================
CREATE OR REFRESH STREAMING TABLE quarantine_streaming_quality
COMMENT 'Quarantine — streaming_quality: latency_ms <= 0 위반 레코드'
AS
SELECT *, 'valid_latency: latency_ms > 0' AS violated_rule, current_timestamp() AS quarantined_at
FROM STREAM(LIVE._streaming_quality_all)
WHERE NOT (latency_ms > 0);

-- COMMAND ----------

-- ============================================================
-- [Temp View] error_events — 모든 레코드 (devices 조인 포함)
-- ============================================================
CREATE TEMPORARY STREAMING LIVE VIEW _error_events_all
AS
SELECT
  v.event_id, v.device_id, v.timestamp, v.event_type,
  CASE
    WHEN UPPER(TRIM(v.severity)) IN ('CRITICAL', 'FATAL') THEN 'CRITICAL'
    WHEN UPPER(TRIM(v.severity)) IN ('ERROR', 'ERR') THEN 'ERROR'
    WHEN UPPER(TRIM(v.severity)) IN ('WARNING', 'WARN') THEN 'WARNING'
    WHEN UPPER(TRIM(v.severity)) IN ('INFO', 'NOTICE') THEN 'INFO'
    ELSE 'UNKNOWN'
  END AS severity,
  v.process_name, v.app_id, v.crash_signal, v.exit_code, v.error_code, v.error_detail,
  v.cpu_usage_at_event, v.mem_used_pct_at_event, v.uptime_sec, v.webos_version, v.coredump_available,
  dev.product_line, dev.model_name, dev.manufacturing_date,
  CASE WHEN UPPER(v.error_detail) LIKE '%OUT OF MEMORY%' OR UPPER(v.error_detail) LIKE '%OOM%'
       OR UPPER(v.crash_signal) LIKE '%OOM%' THEN true ELSE false END AS is_oom,
  CASE WHEN UPPER(v.event_type) LIKE '%CRASH%' OR v.crash_signal IS NOT NULL THEN true ELSE false END AS is_crash,
  CASE WHEN UPPER(v.process_name) LIKE '%MEDIA%' OR UPPER(v.process_name) LIKE '%VIDEO%'
       OR UPPER(v.process_name) LIKE '%AUDIO%' OR UPPER(v.error_code) LIKE '%MEDIA%' THEN true ELSE false END AS is_media_error,
  CASE
    WHEN UPPER(v.process_name) LIKE '%WEB%' OR UPPER(v.process_name) LIKE '%BROWSER%' OR UPPER(v.process_name) LIKE '%JS%' THEN 'web_runtime'
    WHEN UPPER(v.process_name) LIKE '%MEDIA%' OR UPPER(v.process_name) LIKE '%VIDEO%' OR UPPER(v.process_name) LIKE '%AUDIO%' THEN 'media'
    WHEN UPPER(v.process_name) LIKE '%KERNEL%' OR UPPER(v.process_name) LIKE '%SYSTEM%' OR UPPER(v.process_name) LIKE '%INIT%' THEN 'system'
    WHEN UPPER(v.process_name) LIKE '%APP%' OR UPPER(v.process_name) LIKE '%LUNA%' THEN 'app'
    WHEN UPPER(v.process_name) LIKE '%NETWORK%' OR UPPER(v.process_name) LIKE '%WIFI%' OR UPPER(v.process_name) LIKE '%NET%' THEN 'network'
    ELSE 'other'
  END AS error_category,
  DATEDIFF(CAST(v.timestamp AS DATE), dev.manufacturing_date) AS device_age_days,
  CAST(v.timestamp AS DATE) AS event_date
FROM STREAM(byungjun_lee_smarttv_training_catalog.bronze.error_crash_events) v
INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev
  ON v.device_id = dev.device_id;

-- COMMAND ----------

-- ============================================================
-- Silver 5: error_events (Streaming Table)
-- Expectation: severity IN ('CRITICAL','ERROR','WARNING')
-- 참고: INFO, UNKNOWN은 quarantine으로 분리됨
-- ============================================================
CREATE OR REFRESH STREAMING TABLE error_events (
  CONSTRAINT valid_severity EXPECT (severity IN ('CRITICAL', 'ERROR', 'WARNING')) ON VIOLATION DROP ROW
)
COMMENT 'Error/crash events — severity normalized, device-enriched, error categorized'
AS SELECT * FROM STREAM(LIVE._error_events_all);

-- COMMAND ----------

-- ============================================================
-- Quarantine: error_events — severity 위반 (INFO, UNKNOWN)
-- ============================================================
CREATE OR REFRESH STREAMING TABLE quarantine_error_events
COMMENT 'Quarantine — error_events: severity가 CRITICAL/ERROR/WARNING이 아닌 레코드'
AS
SELECT *, 'valid_severity: severity IN (CRITICAL, ERROR, WARNING)' AS violated_rule, current_timestamp() AS quarantined_at
FROM STREAM(LIVE._error_events_all)
WHERE NOT (severity IN ('CRITICAL', 'ERROR', 'WARNING'));

-- COMMAND ----------

-- ============================================================
-- Silver 7: app_sessions (Streaming Table) — 추가 10 중 1
-- 소스: bronze.app_launch_events
-- ROW_NUMBER 제거, JOIN + filter + CASE 유지
-- ============================================================
CREATE OR REFRESH STREAMING TABLE app_sessions
COMMENT 'App sessions — streaming ingestion, orphan events filtered, session metrics enriched'
AS
SELECT
  v.event_id, v.device_id,
  v.timestamp AS session_start,
  TIMESTAMPADD(SECOND, v.session_duration_sec, v.timestamp) AS session_end,
  v.app_id, v.app_name, v.app_version, v.caller_id, v.launch_mode,
  v.launch_time_ms, v.close_reason, v.session_duration_sec,
  ROUND(v.session_duration_sec / 60.0, 1) AS session_duration_min,
  v.memory_at_launch_kb,
  ROUND(v.memory_at_launch_kb / 1024.0, 1) AS memory_at_launch_mb,
  CASE
    WHEN v.session_duration_sec < 10 THEN 'bounce'
    WHEN v.session_duration_sec < 300 THEN 'short'
    WHEN v.session_duration_sec < 1800 THEN 'medium'
    ELSE 'long'
  END AS session_category,
  CAST(v.timestamp AS DATE) AS event_date
FROM STREAM(byungjun_lee_smarttv_training_catalog.bronze.app_launch_events) v
INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev
  ON v.device_id = dev.device_id
WHERE v.session_duration_sec IS NOT NULL
  AND v.session_duration_sec BETWEEN 0 AND 86400
  AND v.launch_time_ms >= 0;

-- COMMAND ----------

-- ============================================================
-- Silver 11: acr_content (Streaming Table) — 추가 10 중 5
-- 소스: bronze.acr_events
-- 이중 ROW_NUMBER 제거, confidence >= 0.5 필터 유지
-- ============================================================
CREATE OR REFRESH STREAMING TABLE acr_content
COMMENT 'ACR content recognition — low confidence filtered, streaming ingestion'
AS
SELECT
  v.event_id, v.device_id, v.timestamp, v.event_type,
  v.fingerprint_hash, v.match_confidence,
  CASE
    WHEN v.match_confidence >= 0.9 THEN 'high'
    WHEN v.match_confidence >= 0.7 THEN 'medium'
    ELSE 'low'
  END AS confidence_tier,
  v.content_id, v.program_title, v.network_name, v.genre, v.content_type,
  v.is_ad_break, v.ad_brand, v.dma_code,
  CAST(v.timestamp AS DATE) AS event_date
FROM STREAM(byungjun_lee_smarttv_training_catalog.bronze.acr_events) v
INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev
  ON v.device_id = dev.device_id
WHERE v.match_confidence >= 0.5;

-- COMMAND ----------

-- ============================================================
-- Silver 12: voice_interactions (Streaming Table) — 추가 10 중 6
-- 소스: bronze.voice_command_events
-- ROW_NUMBER 제거, transcript 정규화 + 빈 transcript 필터 유지
-- ============================================================
CREATE OR REFRESH STREAMING TABLE voice_interactions
COMMENT 'Voice commands — transcript normalized, empty transcripts filtered, streaming ingestion'
AS
SELECT
  v.event_id, v.device_id, v.timestamp, v.event_type,
  v.assistant_type, v.wake_word,
  LOWER(TRIM(v.transcript)) AS transcript,
  v.intent, v.confidence_score,
  CASE
    WHEN v.confidence_score >= 0.9 THEN 'high'
    WHEN v.confidence_score >= 0.7 THEN 'medium'
    WHEN v.confidence_score >= 0.5 THEN 'low'
    ELSE 'very_low'
  END AS confidence_tier,
  v.result_status,
  CASE WHEN v.result_status IN ('SUCCESS', 'COMPLETED') THEN true ELSE false END AS is_successful,
  v.audio_duration_ms, v.processing_latency_ms, v.microphone_source, v.language,
  CAST(v.timestamp AS DATE) AS event_date
FROM STREAM(byungjun_lee_smarttv_training_catalog.bronze.voice_command_events) v
INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev
  ON v.device_id = dev.device_id
WHERE v.transcript IS NOT NULL AND TRIM(v.transcript) != '';

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Silver Layer — Materialized Views (Core 2 + Additional 7)
-- MAGIC
-- MAGIC Materialized View는 윈도우 함수(ROW_NUMBER, LEAD, LAG), GROUP BY 집계가 필요한 테이블에 사용.
-- MAGIC 전체 데이터 리프레시 방식으로 동작.

-- COMMAND ----------

-- ============================================================
-- [Temp View] system_metrics — 5분 집계 전 전체 레코드
-- GROUP BY 필수 → Materialized View
-- ============================================================
CREATE TEMPORARY LIVE VIEW _system_metrics_all
AS
WITH valid AS (
  SELECT r.*
  FROM byungjun_lee_smarttv_training_catalog.bronze.resource_utilization r
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON r.device_id = dev.device_id
),
deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id, timestamp ORDER BY timestamp) AS rn
  FROM valid
),
clipped AS (
  SELECT
    device_id, timestamp,
    GREATEST(0, LEAST(100, cpu_usage_pct)) AS cpu_usage_pct,
    mem_total_kb,
    GREATEST(0, LEAST(100, mem_used_pct)) AS mem_used_pct,
    mem_available_kb, swap_used_kb,
    GREATEST(0, LEAST(100, gpu_usage_pct)) AS gpu_usage_pct,
    CASE WHEN thermal_zone_0_c BETWEEN 0 AND 100 THEN thermal_zone_0_c ELSE NULL END AS thermal_zone_0_c,
    CASE WHEN thermal_zone_1_c BETWEEN 0 AND 100 THEN thermal_zone_1_c ELSE NULL END AS thermal_zone_1_c,
    thermal_throttle_active, storage_available_mb, active_app_id, process_count,
    network_rx_bytes, network_tx_bytes,
    CAST(FROM_UNIXTIME(UNIX_TIMESTAMP(timestamp) - (UNIX_TIMESTAMP(timestamp) % 300)) AS TIMESTAMP) AS window_5min
  FROM deduped WHERE rn = 1
)
SELECT
  device_id,
  window_5min AS timestamp,
  ROUND(AVG(cpu_usage_pct), 1) AS avg_cpu_pct,
  ROUND(MAX(cpu_usage_pct), 1) AS max_cpu_pct,
  ROUND(AVG(mem_used_pct), 1) AS avg_mem_used_pct,
  ROUND(MAX(mem_used_pct), 1) AS max_mem_used_pct,
  MAX(mem_total_kb) AS mem_total_kb,
  MIN(mem_available_kb) AS min_mem_available_kb,
  MAX(swap_used_kb) AS max_swap_used_kb,
  ROUND(AVG(gpu_usage_pct), 1) AS avg_gpu_pct,
  ROUND(MAX(gpu_usage_pct), 1) AS max_gpu_pct,
  ROUND(MAX(thermal_zone_0_c), 1) AS peak_thermal_0_c,
  ROUND(MAX(thermal_zone_1_c), 1) AS peak_thermal_1_c,
  BOOL_OR(thermal_throttle_active) AS any_thermal_throttle,
  MIN(storage_available_mb) AS min_storage_available_mb,
  MAX(process_count) AS max_process_count,
  SUM(network_rx_bytes) AS total_rx_bytes,
  SUM(network_tx_bytes) AS total_tx_bytes,
  COUNT(*) AS sample_count,
  CASE
    WHEN MAX(cpu_usage_pct) > 80 AND MAX(mem_used_pct) > 85 THEN 'critical'
    WHEN MAX(cpu_usage_pct) > 70 OR MAX(mem_used_pct) > 80
      OR MAX(COALESCE(thermal_zone_0_c, 0)) > 70 THEN 'warning'
    ELSE 'normal'
  END AS health_status,
  CAST(window_5min AS DATE) AS event_date
FROM clipped
GROUP BY device_id, window_5min;

-- COMMAND ----------

-- ============================================================
-- Silver 2: system_metrics (Materialized View)
-- Expectation: avg_cpu_pct >= 0 AND avg_cpu_pct <= 100
-- 참고: GREATEST/LEAST 클리핑으로 이론상 항상 통과하나 안전장치로 추가
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW system_metrics (
  CONSTRAINT valid_cpu EXPECT (avg_cpu_pct >= 0 AND avg_cpu_pct <= 100) ON VIOLATION DROP ROW
)
COMMENT 'System metrics — 5-min aggregated, outliers clipped, health status classified'
AS SELECT * FROM LIVE._system_metrics_all;

-- COMMAND ----------

-- ============================================================
-- Quarantine: system_metrics — CPU 범위 위반 (이론상 비어 있음)
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW quarantine_system_metrics
COMMENT 'Quarantine — system_metrics: avg_cpu_pct 범위 위반 레코드'
AS
SELECT *, 'valid_cpu: avg_cpu_pct >= 0 AND avg_cpu_pct <= 100' AS violated_rule, current_timestamp() AS quarantined_at
FROM LIVE._system_metrics_all
WHERE NOT (avg_cpu_pct >= 0 AND avg_cpu_pct <= 100);

-- COMMAND ----------

-- ============================================================
-- [Temp View] ad_funnel — VAST 시퀀스 포함 전체 레코드
-- LAG() 필수 → Materialized View
-- ============================================================
CREATE TEMPORARY LIVE VIEW _ad_funnel_all
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.ad_impressions
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
),
sequenced AS (
  SELECT *,
    CASE UPPER(event_type)
      WHEN 'AD_REQUEST'      THEN 1
      WHEN 'AD_IMPRESSION'   THEN 2
      WHEN 'AD_START'        THEN 3
      WHEN 'FIRST_QUARTILE'  THEN 4
      WHEN 'MIDPOINT'        THEN 5
      WHEN 'THIRD_QUARTILE'  THEN 6
      WHEN 'AD_COMPLETE'     THEN 7
      WHEN 'AD_CLICK'        THEN 8
      WHEN 'AD_SKIP'         THEN 9
      ELSE 0
    END AS vast_order,
    LAG(CASE UPPER(event_type)
      WHEN 'AD_REQUEST'      THEN 1
      WHEN 'AD_IMPRESSION'   THEN 2
      WHEN 'AD_START'        THEN 3
      WHEN 'FIRST_QUARTILE'  THEN 4
      WHEN 'MIDPOINT'        THEN 5
      WHEN 'THIRD_QUARTILE'  THEN 6
      WHEN 'AD_COMPLETE'     THEN 7
      WHEN 'AD_CLICK'        THEN 8
      WHEN 'AD_SKIP'         THEN 9
      ELSE 0
    END) OVER (PARTITION BY device_id, campaign_id, ad_unit_id ORDER BY timestamp) AS prev_vast_order
  FROM valid
)
SELECT
  event_id, device_id, timestamp, event_type,
  ad_unit_id, creative_id, campaign_id, advertiser_name,
  ad_format, ad_duration_sec,
  COALESCE(completion_pct,
    CASE UPPER(event_type)
      WHEN 'AD_START'        THEN 0.0
      WHEN 'FIRST_QUARTILE'  THEN 25.0
      WHEN 'MIDPOINT'        THEN 50.0
      WHEN 'THIRD_QUARTILE'  THEN 75.0
      WHEN 'AD_COMPLETE'     THEN 100.0
      ELSE NULL
    END
  ) AS completion_pct,
  placement, revenue_model, bid_price_usd, viewability_pct,
  vast_order,
  CASE
    WHEN prev_vast_order IS NULL THEN true
    WHEN vast_order >= prev_vast_order THEN true
    ELSE false
  END AS is_sequence_valid,
  CASE WHEN UPPER(event_type) = 'AD_COMPLETE' THEN true ELSE false END AS is_completed,
  CASE WHEN UPPER(event_type) = 'AD_CLICK' THEN true ELSE false END AS is_clicked,
  CASE WHEN UPPER(event_type) = 'AD_SKIP' THEN true ELSE false END AS is_skipped,
  CAST(timestamp AS DATE) AS event_date
FROM sequenced;

-- COMMAND ----------

-- ============================================================
-- Silver 3: ad_funnel (Materialized View)
-- Expectation: is_sequence_valid = true
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW ad_funnel (
  CONSTRAINT valid_sequence EXPECT (is_sequence_valid = true) ON VIOLATION DROP ROW
)
COMMENT 'Ad funnel — VAST sequence validated, completion derived, click/skip flags'
AS SELECT * FROM LIVE._ad_funnel_all;

-- COMMAND ----------

-- ============================================================
-- Quarantine: ad_funnel — VAST 시퀀스 위반
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW quarantine_ad_funnel
COMMENT 'Quarantine — ad_funnel: VAST 시퀀스 순서가 깨진 레코드'
AS
SELECT *, 'valid_sequence: is_sequence_valid = true' AS violated_rule, current_timestamp() AS quarantined_at
FROM LIVE._ad_funnel_all
WHERE NOT (is_sequence_valid = true);

-- COMMAND ----------

-- ============================================================
-- Silver 9: devices_cleaned (Materialized View) — 디멘전 테이블
-- ROW_NUMBER 중복 제거, 스트리밍 불필요
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW devices_cleaned
COMMENT 'Cleansed device master — deduplicated, region/country standardized'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY manufacturing_date DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.devices
)
SELECT
  device_id, model_name, product_line, panel_type, screen_size_inch, webos_version,
  UPPER(TRIM(region)) AS region,
  CASE UPPER(TRIM(region))
    WHEN 'US' THEN 'United States'  WHEN 'KR' THEN 'South Korea'
    WHEN 'EU' THEN 'Europe'         WHEN 'JP' THEN 'Japan'
    WHEN 'CN' THEN 'China'          WHEN 'IN' THEN 'India'
    WHEN 'BR' THEN 'Brazil'         WHEN 'UK' THEN 'United Kingdom'
    ELSE TRIM(region)
  END AS country,
  manufacturing_date, soc_chipset, thinq_connected, voice_assistant, network_type
FROM deduped WHERE rn = 1;

-- COMMAND ----------

-- ============================================================
-- Silver 8: boot_events (Materialized View)
-- LEAD() 쌍 매칭 필수 → MV
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW boot_events
COMMENT 'System boot events — deduplicated, ON/OFF paired, boot performance tiered'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.system_boot_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
),
paired AS (
  SELECT *,
    LEAD(event_type) OVER (PARTITION BY device_id ORDER BY timestamp) AS next_event_type,
    LEAD(timestamp) OVER (PARTITION BY device_id ORDER BY timestamp) AS next_timestamp
  FROM valid
)
SELECT
  event_id, device_id, timestamp, monotonic_ms, event_type,
  boot_reason, boot_time_ms, previous_shutdown, webos_version, firmware_version, kernel_version,
  uptime_before_event_sec,
  ROUND(uptime_before_event_sec / 3600.0, 1) AS uptime_before_event_hr,
  CASE
    WHEN boot_time_ms < 5000 THEN 'fast'
    WHEN boot_time_ms < 15000 THEN 'normal'
    WHEN boot_time_ms < 30000 THEN 'slow'
    ELSE 'very_slow'
  END AS boot_speed_tier,
  CASE
    WHEN event_type IN ('POWER_ON', 'COLD_BOOT', 'WARM_BOOT')
     AND next_event_type IN ('POWER_OFF', 'STANDBY', 'SHUTDOWN') THEN true
    ELSE false
  END AS has_matching_off,
  CAST(timestamp AS DATE) AS event_date
FROM paired;

-- COMMAND ----------

-- ============================================================
-- Silver 9: media_sessions (Materialized View)
-- LEAD() START/STOP 쌍 매칭 필수 → MV
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW media_sessions
COMMENT 'Media playback sessions — START/STOP paired, quality tiered'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.media_playback_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
),
enriched AS (
  SELECT *,
    LEAD(event_type) OVER (PARTITION BY device_id ORDER BY timestamp) AS next_event_type,
    LEAD(timestamp) OVER (PARTITION BY device_id ORDER BY timestamp) AS next_timestamp
  FROM valid
)
SELECT
  event_id, device_id, timestamp, event_type,
  video_codec, video_profile, resolution, frame_rate, bit_depth, color_space,
  COALESCE(NULLIF(TRIM(hdr_type), ''), 'SDR') AS hdr_type,
  dolby_vision_profile, max_cll_nits, max_fall_nits,
  audio_codec, audio_channels, audio_passthrough, content_source, drm_type,
  CASE
    WHEN resolution LIKE '%2160%' OR resolution LIKE '%3840%' THEN '4K'
    WHEN resolution LIKE '%1080%' OR resolution LIKE '%1920%' THEN 'FHD'
    WHEN resolution LIKE '%720%' OR resolution LIKE '%1280%' THEN 'HD'
    ELSE 'SD'
  END AS quality_tier,
  CASE
    WHEN event_type IN ('START', 'PLAY') AND next_event_type IN ('STOP', 'PAUSE', 'END') THEN
      BIGINT(UNIX_TIMESTAMP(next_timestamp) - UNIX_TIMESTAMP(timestamp))
    ELSE NULL
  END AS session_duration_sec,
  CASE
    WHEN event_type IN ('START', 'PLAY') AND next_event_type IN ('STOP', 'PAUSE', 'END') THEN true
    ELSE false
  END AS has_matching_stop,
  CAST(timestamp AS DATE) AS event_date
FROM enriched;

-- COMMAND ----------

-- ============================================================
-- Silver 10: network_events (Materialized View)
-- LEAD() CONNECTED/DISCONNECTED 쌍 매칭 필수 → MV
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW network_events
COMMENT 'WiFi connection events — signal corrected, CONNECTED/DISCONNECTED paired'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.wifi_connection_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
),
corrected AS (
  SELECT *,
    CASE WHEN signal_strength_dbm > 0 THEN -signal_strength_dbm ELSE signal_strength_dbm END AS signal_corrected,
    LEAD(event_type) OVER (PARTITION BY device_id ORDER BY timestamp) AS next_event_type,
    LEAD(timestamp) OVER (PARTITION BY device_id ORDER BY timestamp) AS next_timestamp
  FROM valid
)
SELECT
  event_id, device_id, timestamp, event_type, state, ssid, security_type,
  frequency_mhz, channel,
  signal_corrected AS signal_strength_dbm,
  CASE
    WHEN signal_corrected >= -50 THEN 'excellent'
    WHEN signal_corrected >= -60 THEN 'good'
    WHEN signal_corrected >= -70 THEN 'fair'
    WHEN signal_corrected >= -80 THEN 'weak'
    ELSE 'very_weak'
  END AS signal_quality,
  link_speed_mbps, ip_address, gateway, dns_servers,
  CASE WHEN frequency_mhz >= 5000 THEN '5GHz' WHEN frequency_mhz >= 2400 THEN '2.4GHz' ELSE 'unknown' END AS frequency_band,
  CASE
    WHEN event_type = 'CONNECTED' AND next_event_type = 'DISCONNECTED' THEN
      BIGINT(UNIX_TIMESTAMP(next_timestamp) - UNIX_TIMESTAMP(timestamp))
    ELSE NULL
  END AS connection_duration_sec,
  CASE
    WHEN event_type = 'CONNECTED' AND next_event_type = 'DISCONNECTED' THEN true
    ELSE false
  END AS has_matching_disconnect,
  CAST(timestamp AS DATE) AS event_date
FROM corrected;

-- COMMAND ----------

-- ============================================================
-- Silver 13: iot_interactions (Materialized View)
-- LEAD() COMMAND/ACK 쌍 매칭 필수 → MV
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW iot_interactions
COMMENT 'ThinQ IoT interactions — command/ack paired, response time outliers filtered'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.thinq_device_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1 AND (d.response_time_ms <= 30000 OR d.response_time_ms IS NULL)
),
paired AS (
  SELECT *,
    LEAD(event_type) OVER (PARTITION BY device_id, iot_device_id ORDER BY timestamp) AS next_event_type,
    LEAD(timestamp) OVER (PARTITION BY device_id, iot_device_id ORDER BY timestamp) AS next_timestamp
  FROM valid
)
SELECT
  event_id, device_id, timestamp, event_type,
  iot_device_id, iot_device_type, iot_device_model, protocol, connection_status,
  command, command_result, response_time_ms,
  CASE WHEN response_time_ms > 10000 THEN true ELSE false END AS is_response_outlier,
  CASE
    WHEN event_type IN ('COMMAND', 'REQUEST') AND next_event_type IN ('ACK', 'RESPONSE', 'RESULT') THEN true
    ELSE false
  END AS has_matching_ack,
  CASE
    WHEN event_type IN ('COMMAND', 'REQUEST') AND next_event_type IN ('ACK', 'RESPONSE', 'RESULT') THEN
      BIGINT(UNIX_TIMESTAMP(next_timestamp) - UNIX_TIMESTAMP(timestamp))
    ELSE NULL
  END AS round_trip_sec,
  CAST(timestamp AS DATE) AS event_date
FROM paired;

-- COMMAND ----------

-- ============================================================
-- Silver 14: panel_health (Materialized View)
-- ROW_NUMBER() 시퀀스 번호 부여 → MV
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW panel_health
COMMENT 'Panel diagnostics — categorized, thermal status, panel age tiered, time-ordered'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.panel_diagnostics
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
)
SELECT
  event_id, device_id, timestamp, event_type, panel_type,
  CASE
    WHEN UPPER(panel_type) LIKE '%OLED%' THEN 'OLED'
    WHEN UPPER(panel_type) LIKE '%LCD%' OR UPPER(panel_type) LIKE '%LED%' THEN 'LCD'
    WHEN UPPER(panel_type) LIKE '%QNED%' THEN 'QNED'
    ELSE 'OTHER'
  END AS panel_category,
  panel_total_hours, panel_on_count, compensation_type, trigger_reason, duration_min, result,
  backlight_level, abl_current_pct, peak_luminance_nits, panel_temperature_c,
  CASE
    WHEN panel_temperature_c > 60 THEN 'critical'
    WHEN panel_temperature_c > 50 THEN 'warning'
    ELSE 'normal'
  END AS thermal_status,
  ambient_light_lux, picture_mode, energy_saving_mode,
  CASE
    WHEN panel_total_hours > 30000 THEN 'end_of_life'
    WHEN panel_total_hours > 20000 THEN 'aging'
    WHEN panel_total_hours > 10000 THEN 'mature'
    ELSE 'new'
  END AS panel_age_tier,
  ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp) AS diag_sequence_num,
  CAST(timestamp AS DATE) AS event_date
FROM valid;

-- COMMAND ----------

-- ============================================================
-- Silver 15: firmware_history (Materialized View)
-- LAG() 시퀀스 일관성 검증 → MV
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW firmware_history
COMMENT 'Firmware update history — OTA sequence validated, failures flagged, download speed calculated'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.firmware_updates
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
),
sequenced AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp) AS update_sequence,
    LAG(target_version) OVER (PARTITION BY device_id ORDER BY timestamp) AS prev_target_version,
    LAG(install_result) OVER (PARTITION BY device_id ORDER BY timestamp) AS prev_install_result
  FROM valid
)
SELECT
  event_id, device_id, timestamp, event_type,
  current_version, target_version,
  download_size_bytes,
  ROUND(download_size_bytes / (1024.0 * 1024.0), 1) AS download_size_mb,
  download_duration_ms,
  CASE
    WHEN download_size_bytes > 0 AND download_duration_ms > 0 THEN
      ROUND((download_size_bytes * 8.0) / (download_duration_ms / 1000.0) / 1000000.0, 2)
    ELSE NULL
  END AS download_speed_mbps,
  install_result, update_channel,
  CASE WHEN UPPER(install_result) IN ('FAILED', 'ERROR', 'TIMEOUT', 'ABORTED') THEN true ELSE false END AS is_failed,
  CASE
    WHEN update_sequence = 1 THEN true
    WHEN prev_target_version IS NOT NULL AND current_version = prev_target_version
     AND UPPER(prev_install_result) IN ('SUCCESS', 'COMPLETED') THEN true
    ELSE false
  END AS is_sequence_consistent,
  update_sequence,
  CAST(timestamp AS DATE) AS event_date
FROM sequenced;

