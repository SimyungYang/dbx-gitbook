-- ============================================================
-- Smart TV PoC: Silver & Gold 전체 SQL
-- Catalog: byungjun_lee_smarttv_training_catalog
-- 생성일: 2026-04-15
-- ============================================================
-- Silver 15개 테이블 (Core 5 + 추가 10)
-- Gold 6개 테이블
-- ============================================================


-- ************************************************************
--  SILVER LAYER
-- ************************************************************

CREATE SCHEMA IF NOT EXISTS byungjun_lee_smarttv_training_catalog.silver
COMMENT 'Silver layer — cleansed and enriched Smart TV data';


-- ============================================================
-- Silver 1: viewing_sessions ← bronze.viewing_logs
-- 핵심: event_id 중복 제거, duration 검증, primetime/viewing_hour 파생
-- 주의: viewing_logs에는 timestamp 컬럼이 없음 → session_start 사용
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.viewing_sessions
COMMENT 'Viewing sessions — deduplicated, duration validated, primetime/hour enriched'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY session_start DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.viewing_logs
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
    AND d.duration_sec BETWEEN 0 AND 86400
    AND d.session_end >= d.session_start
)
SELECT
  event_id,
  device_id,
  session_start,
  session_end,
  duration_sec,
  ROUND(duration_sec / 60.0, 1) AS duration_min,
  content_source,
  app_id,
  channel_number,
  channel_name,
  broadcast_type,
  COALESCE(
    NULLIF(TRIM(program_title), ''),
    CASE
      WHEN app_id IS NOT NULL THEN CONCAT('App:', app_id)
      ELSE 'Unknown'
    END
  ) AS program_title,
  genre,
  signal_strength_dbm,
  signal_quality_pct,
  tune_latency_ms,
  resolution,
  COALESCE(NULLIF(TRIM(hdr_type), ''), 'SDR') AS hdr_type,
  HOUR(session_start) AS viewing_hour,
  CASE
    WHEN HOUR(session_start) BETWEEN 19 AND 23 THEN true
    ELSE false
  END AS is_primetime,
  CASE
    WHEN duration_sec < 60 THEN 'zap'
    WHEN duration_sec < 600 THEN 'short'
    WHEN duration_sec < 3600 THEN 'medium'
    ELSE 'long'
  END AS viewing_category,
  CAST(session_start AS DATE) AS event_date
FROM valid;


-- ============================================================
-- Silver 2: system_metrics ← bronze.resource_utilization
-- 핵심: 5분 집계, CPU/GPU/mem 클립, health_status 분류
-- 주의: resource_utilization에는 event_id 없음 → (device_id, timestamp) 중복 제거
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.system_metrics
COMMENT 'System metrics — 5-min aggregated, outliers clipped, health status classified'
PARTITIONED BY (event_date)
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
    device_id,
    timestamp,
    GREATEST(0, LEAST(100, cpu_usage_pct)) AS cpu_usage_pct,
    mem_total_kb,
    GREATEST(0, LEAST(100, mem_used_pct)) AS mem_used_pct,
    mem_available_kb,
    swap_used_kb,
    GREATEST(0, LEAST(100, gpu_usage_pct)) AS gpu_usage_pct,
    CASE WHEN thermal_zone_0_c BETWEEN 0 AND 100 THEN thermal_zone_0_c ELSE NULL END AS thermal_zone_0_c,
    CASE WHEN thermal_zone_1_c BETWEEN 0 AND 100 THEN thermal_zone_1_c ELSE NULL END AS thermal_zone_1_c,
    thermal_throttle_active,
    storage_available_mb,
    active_app_id,
    process_count,
    network_rx_bytes,
    network_tx_bytes,
    CAST(FROM_UNIXTIME(UNIX_TIMESTAMP(timestamp) - (UNIX_TIMESTAMP(timestamp) % 300)) AS TIMESTAMP) AS window_5min
  FROM deduped
  WHERE rn = 1
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


-- ============================================================
-- Silver 3: ad_funnel ← bronze.ad_impressions
-- 핵심: VAST 시퀀스 검증, completion_pct 파생, click/skip 플래그
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.ad_funnel
COMMENT 'Ad funnel — VAST sequence validated, completion derived, click/skip flags'
PARTITIONED BY (event_date)
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
  event_id,
  device_id,
  timestamp,
  event_type,
  ad_unit_id,
  creative_id,
  campaign_id,
  advertiser_name,
  ad_format,
  ad_duration_sec,
  COALESCE(
    completion_pct,
    CASE UPPER(event_type)
      WHEN 'AD_START'        THEN 0.0
      WHEN 'FIRST_QUARTILE'  THEN 25.0
      WHEN 'MIDPOINT'        THEN 50.0
      WHEN 'THIRD_QUARTILE'  THEN 75.0
      WHEN 'AD_COMPLETE'     THEN 100.0
      ELSE NULL
    END
  ) AS completion_pct,
  placement,
  revenue_model,
  bid_price_usd,
  viewability_pct,
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


-- ============================================================
-- Silver 4: streaming_quality ← bronze.streaming_buffer_events
-- 핵심: latency 이상치 플래그, quality_tier, buffering ratio
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.streaming_quality
COMMENT 'Streaming quality — latency outliers flagged, quality tiered, buffering ratio calculated'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.streaming_buffer_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
)
SELECT
  event_id,
  device_id,
  timestamp,
  event_type,
  app_id,
  buffer_level_pct,
  buffer_duration_ms,
  stall_count,
  stall_duration_total_ms,
  current_bitrate_kbps,
  target_bitrate_kbps,
  COALESCE(NULLIF(TRIM(cdn_host), ''), 'local_playback') AS cdn_host,
  latency_ms,
  dns_resolve_ms,
  CASE
    WHEN current_bitrate_kbps >= 15000 THEN '4K'
    WHEN current_bitrate_kbps >= 5000  THEN 'FHD'
    WHEN current_bitrate_kbps >= 2500  THEN 'HD'
    ELSE 'SD'
  END AS quality_tier,
  CASE WHEN latency_ms > 10000 THEN true ELSE false END AS is_outlier,
  CASE WHEN UPPER(event_type) LIKE '%BUFFER%' OR stall_count > 0 THEN true ELSE false END AS is_buffering,
  CASE
    WHEN target_bitrate_kbps > 0
     AND current_bitrate_kbps < target_bitrate_kbps * 0.5 THEN true
    ELSE false
  END AS is_quality_degraded,
  CASE
    WHEN buffer_duration_ms > 0 AND stall_duration_total_ms IS NOT NULL THEN
      ROUND(stall_duration_total_ms * 100.0 / buffer_duration_ms, 2)
    ELSE 0.0
  END AS stall_ratio_pct,
  CAST(timestamp AS DATE) AS event_date
FROM valid;


-- ============================================================
-- Silver 5: error_events ← bronze.error_crash_events
-- 핵심: severity 표준화, devices 조인(product_line), error_category 분류
-- 주의: error_crash_events에 이미 webos_version 있음 → 이벤트 값 사용
-- 주의: devices에 firmware_version 없음 → device_age_days로 대체
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.error_events
COMMENT 'Error/crash events — severity normalized, device-enriched, error categorized'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.error_crash_events
),
valid AS (
  SELECT
    d.*,
    dev.product_line,
    dev.model_name,
    dev.manufacturing_date
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
)
SELECT
  event_id,
  device_id,
  timestamp,
  event_type,
  CASE
    WHEN UPPER(TRIM(severity)) IN ('CRITICAL', 'FATAL') THEN 'CRITICAL'
    WHEN UPPER(TRIM(severity)) IN ('ERROR', 'ERR') THEN 'ERROR'
    WHEN UPPER(TRIM(severity)) IN ('WARNING', 'WARN') THEN 'WARNING'
    WHEN UPPER(TRIM(severity)) IN ('INFO', 'NOTICE') THEN 'INFO'
    ELSE 'UNKNOWN'
  END AS severity,
  process_name,
  app_id,
  crash_signal,
  exit_code,
  error_code,
  error_detail,
  cpu_usage_at_event,
  mem_used_pct_at_event,
  uptime_sec,
  webos_version,
  coredump_available,
  product_line,
  model_name,
  CASE WHEN UPPER(error_detail) LIKE '%OUT OF MEMORY%' OR UPPER(error_detail) LIKE '%OOM%'
       OR UPPER(crash_signal) LIKE '%OOM%' THEN true ELSE false END AS is_oom,
  CASE WHEN UPPER(event_type) LIKE '%CRASH%' OR crash_signal IS NOT NULL THEN true ELSE false END AS is_crash,
  CASE WHEN UPPER(process_name) LIKE '%MEDIA%' OR UPPER(process_name) LIKE '%VIDEO%'
       OR UPPER(process_name) LIKE '%AUDIO%' OR UPPER(error_code) LIKE '%MEDIA%' THEN true ELSE false END AS is_media_error,
  CASE
    WHEN UPPER(process_name) LIKE '%WEB%' OR UPPER(process_name) LIKE '%BROWSER%' OR UPPER(process_name) LIKE '%JS%' THEN 'web_runtime'
    WHEN UPPER(process_name) LIKE '%MEDIA%' OR UPPER(process_name) LIKE '%VIDEO%' OR UPPER(process_name) LIKE '%AUDIO%' THEN 'media'
    WHEN UPPER(process_name) LIKE '%KERNEL%' OR UPPER(process_name) LIKE '%SYSTEM%' OR UPPER(process_name) LIKE '%INIT%' THEN 'system'
    WHEN UPPER(process_name) LIKE '%APP%' OR UPPER(process_name) LIKE '%LUNA%' THEN 'app'
    WHEN UPPER(process_name) LIKE '%NETWORK%' OR UPPER(process_name) LIKE '%WIFI%' OR UPPER(process_name) LIKE '%NET%' THEN 'network'
    ELSE 'other'
  END AS error_category,
  DATEDIFF(CAST(timestamp AS DATE), manufacturing_date) AS device_age_days,
  CAST(timestamp AS DATE) AS event_date
FROM valid;


-- ============================================================
-- Silver 6: devices_cleaned ← bronze.devices
-- 핵심: device_id 중복 제거, region/country 표준화
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.devices_cleaned
COMMENT 'Cleansed device master — deduplicated, region/country standardized'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY manufacturing_date DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.devices
)
SELECT
  device_id,
  model_name,
  product_line,
  panel_type,
  screen_size_inch,
  webos_version,
  UPPER(TRIM(region)) AS region,
  CASE UPPER(TRIM(region))
    WHEN 'US' THEN 'United States'
    WHEN 'KR' THEN 'South Korea'
    WHEN 'EU' THEN 'Europe'
    WHEN 'JP' THEN 'Japan'
    WHEN 'CN' THEN 'China'
    WHEN 'IN' THEN 'India'
    WHEN 'BR' THEN 'Brazil'
    WHEN 'UK' THEN 'United Kingdom'
    ELSE TRIM(region)
  END AS country,
  manufacturing_date,
  soc_chipset,
  thinq_connected,
  voice_assistant,
  network_type
FROM deduped
WHERE rn = 1;


-- ============================================================
-- Silver 7: app_sessions ← bronze.app_launch_events
-- 핵심: 고아 이벤트 필터, session_category 분류
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.app_sessions
COMMENT 'App sessions — deduplicated, orphan events filtered, session metrics enriched'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.app_launch_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
    AND d.session_duration_sec IS NOT NULL
    AND d.session_duration_sec BETWEEN 0 AND 86400
    AND d.launch_time_ms >= 0
)
SELECT
  event_id,
  device_id,
  timestamp AS session_start,
  TIMESTAMPADD(SECOND, session_duration_sec, timestamp) AS session_end,
  app_id,
  app_name,
  app_version,
  caller_id,
  launch_mode,
  launch_time_ms,
  close_reason,
  session_duration_sec,
  ROUND(session_duration_sec / 60.0, 1) AS session_duration_min,
  memory_at_launch_kb,
  ROUND(memory_at_launch_kb / 1024.0, 1) AS memory_at_launch_mb,
  CASE
    WHEN session_duration_sec < 10 THEN 'bounce'
    WHEN session_duration_sec < 300 THEN 'short'
    WHEN session_duration_sec < 1800 THEN 'medium'
    ELSE 'long'
  END AS session_category,
  CAST(timestamp AS DATE) AS event_date
FROM valid;


-- ============================================================
-- Silver 8: boot_events ← bronze.system_boot_events
-- 핵심: ON/OFF 쌍 매칭, boot_speed_tier 분류
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.boot_events
COMMENT 'System boot events — deduplicated, ON/OFF paired, boot performance tiered'
PARTITIONED BY (event_date)
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
  event_id,
  device_id,
  timestamp,
  monotonic_ms,
  event_type,
  boot_reason,
  boot_time_ms,
  previous_shutdown,
  webos_version,
  firmware_version,
  kernel_version,
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


-- ============================================================
-- Silver 9: media_sessions ← bronze.media_playback_events
-- 핵심: START/STOP 쌍 매칭, NULL hdr_type → SDR, quality_tier
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.media_sessions
COMMENT 'Media playback sessions — START/STOP paired, NULL hdr_type → SDR, quality tiered'
PARTITIONED BY (event_date)
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
  event_id,
  device_id,
  timestamp,
  event_type,
  video_codec,
  video_profile,
  resolution,
  frame_rate,
  bit_depth,
  color_space,
  COALESCE(NULLIF(TRIM(hdr_type), ''), 'SDR') AS hdr_type,
  dolby_vision_profile,
  max_cll_nits,
  max_fall_nits,
  audio_codec,
  audio_channels,
  audio_passthrough,
  content_source,
  drm_type,
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


-- ============================================================
-- Silver 10: network_events ← bronze.wifi_connection_events
-- 핵심: signal_strength 부호 보정(양수→음수), CONNECTED/DISCONNECTED 쌍 매칭
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.network_events
COMMENT 'WiFi connection events — signal strength corrected, CONNECTED/DISCONNECTED paired'
PARTITIONED BY (event_date)
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
  event_id,
  device_id,
  timestamp,
  event_type,
  state,
  ssid,
  security_type,
  frequency_mhz,
  channel,
  signal_corrected AS signal_strength_dbm,
  CASE
    WHEN signal_corrected >= -50 THEN 'excellent'
    WHEN signal_corrected >= -60 THEN 'good'
    WHEN signal_corrected >= -70 THEN 'fair'
    WHEN signal_corrected >= -80 THEN 'weak'
    ELSE 'very_weak'
  END AS signal_quality,
  link_speed_mbps,
  ip_address,
  gateway,
  dns_servers,
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


-- ============================================================
-- Silver 11: acr_content ← bronze.acr_events
-- 핵심: match_confidence < 0.5 필터, 동일 일자 fingerprint 중복 제거
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.acr_content
COMMENT 'ACR content recognition — low confidence (<0.5) filtered, duplicate fingerprints removed'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.acr_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
    AND d.match_confidence >= 0.5
),
fp_deduped AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY device_id, fingerprint_hash, CAST(timestamp AS DATE)
      ORDER BY match_confidence DESC, timestamp DESC
    ) AS fp_rn
  FROM valid
)
SELECT
  event_id,
  device_id,
  timestamp,
  event_type,
  fingerprint_hash,
  match_confidence,
  CASE
    WHEN match_confidence >= 0.9 THEN 'high'
    WHEN match_confidence >= 0.7 THEN 'medium'
    ELSE 'low'
  END AS confidence_tier,
  content_id,
  program_title,
  network_name,
  genre,
  content_type,
  is_ad_break,
  ad_brand,
  dma_code,
  CAST(timestamp AS DATE) AS event_date
FROM fp_deduped
WHERE fp_rn = 1;


-- ============================================================
-- Silver 12: voice_interactions ← bronze.voice_command_events
-- 핵심: transcript LOWER/TRIM 정규화, 빈 transcript 필터
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.voice_interactions
COMMENT 'Voice commands — transcript normalized (LOWER/TRIM), empty transcripts filtered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.voice_command_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
    AND d.transcript IS NOT NULL
    AND TRIM(d.transcript) != ''
)
SELECT
  event_id,
  device_id,
  timestamp,
  event_type,
  assistant_type,
  wake_word,
  LOWER(TRIM(transcript)) AS transcript,
  intent,
  confidence_score,
  CASE
    WHEN confidence_score >= 0.9 THEN 'high'
    WHEN confidence_score >= 0.7 THEN 'medium'
    WHEN confidence_score >= 0.5 THEN 'low'
    ELSE 'very_low'
  END AS confidence_tier,
  result_status,
  CASE WHEN result_status IN ('SUCCESS', 'COMPLETED') THEN true ELSE false END AS is_successful,
  audio_duration_ms,
  processing_latency_ms,
  microphone_source,
  language,
  CAST(timestamp AS DATE) AS event_date
FROM valid;


-- ============================================================
-- Silver 13: iot_interactions ← bronze.thinq_device_events
-- 핵심: command/ack 쌍 매칭, response_time > 30s 필터
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.iot_interactions
COMMENT 'ThinQ IoT interactions — command/ack paired, response time outliers (>30s) filtered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM byungjun_lee_smarttv_training_catalog.bronze.thinq_device_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN byungjun_lee_smarttv_training_catalog.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
    AND (d.response_time_ms <= 30000 OR d.response_time_ms IS NULL)
),
paired AS (
  SELECT *,
    LEAD(event_type) OVER (PARTITION BY device_id, iot_device_id ORDER BY timestamp) AS next_event_type,
    LEAD(timestamp) OVER (PARTITION BY device_id, iot_device_id ORDER BY timestamp) AS next_timestamp
  FROM valid
)
SELECT
  event_id,
  device_id,
  timestamp,
  event_type,
  iot_device_id,
  iot_device_type,
  iot_device_model,
  protocol,
  connection_status,
  command,
  command_result,
  response_time_ms,
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


-- ============================================================
-- Silver 14: panel_health ← bronze.panel_diagnostics
-- 핵심: OLED/LCD 분류, thermal_status, panel_age_tier, 시간순 정렬
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.panel_health
COMMENT 'Panel diagnostics — OLED/LCD categorized, thermal status, panel age tiered, time-ordered'
PARTITIONED BY (event_date)
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
  event_id,
  device_id,
  timestamp,
  event_type,
  panel_type,
  CASE
    WHEN UPPER(panel_type) LIKE '%OLED%' THEN 'OLED'
    WHEN UPPER(panel_type) LIKE '%LCD%' OR UPPER(panel_type) LIKE '%LED%' THEN 'LCD'
    WHEN UPPER(panel_type) LIKE '%QNED%' THEN 'QNED'
    ELSE 'OTHER'
  END AS panel_category,
  panel_total_hours,
  panel_on_count,
  compensation_type,
  trigger_reason,
  duration_min,
  result,
  backlight_level,
  abl_current_pct,
  peak_luminance_nits,
  panel_temperature_c,
  CASE
    WHEN panel_temperature_c > 60 THEN 'critical'
    WHEN panel_temperature_c > 50 THEN 'warning'
    ELSE 'normal'
  END AS thermal_status,
  ambient_light_lux,
  picture_mode,
  energy_saving_mode,
  CASE
    WHEN panel_total_hours > 30000 THEN 'end_of_life'
    WHEN panel_total_hours > 20000 THEN 'aging'
    WHEN panel_total_hours > 10000 THEN 'mature'
    ELSE 'new'
  END AS panel_age_tier,
  ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY timestamp) AS diag_sequence_num,
  CAST(timestamp AS DATE) AS event_date
FROM valid;


-- ============================================================
-- Silver 15: firmware_history ← bronze.firmware_updates
-- 핵심: OTA 시퀀스 검증, 실패 flag, 다운로드 속도 계산
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.silver.firmware_history
COMMENT 'Firmware update history — OTA sequence validated, failures flagged, download speed calculated'
PARTITIONED BY (event_date)
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
  event_id,
  device_id,
  timestamp,
  event_type,
  current_version,
  target_version,
  download_size_bytes,
  ROUND(download_size_bytes / (1024.0 * 1024.0), 1) AS download_size_mb,
  download_duration_ms,
  CASE
    WHEN download_size_bytes > 0 AND download_duration_ms > 0 THEN
      ROUND((download_size_bytes * 8.0) / (download_duration_ms / 1000.0) / 1000000.0, 2)
    ELSE NULL
  END AS download_speed_mbps,
  install_result,
  update_channel,
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


-- ************************************************************
--  GOLD LAYER
-- ************************************************************

CREATE SCHEMA IF NOT EXISTS byungjun_lee_smarttv_training_catalog.gold
COMMENT 'Gold layer — business-ready aggregations and KPIs';


-- ============================================================
-- Gold 1: daily_viewing_summary
-- 그레인: device_id × event_date
-- 핵심: 시청 시간, 콘텐츠 믹스, top app/genre, HDR/4K 비율
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.gold.daily_viewing_summary
COMMENT 'Daily viewing summary per device — viewing time, content mix, top app/genre'
PARTITIONED BY (event_date)
AS
WITH viewing AS (
  SELECT
    v.*,
    d.region,
    d.product_line,
    d.panel_type
  FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions v
  INNER JOIN byungjun_lee_smarttv_training_catalog.silver.devices_cleaned d ON v.device_id = d.device_id
),
top_app AS (
  SELECT device_id, event_date, app_id AS top_app,
    ROW_NUMBER() OVER (PARTITION BY device_id, event_date ORDER BY SUM(duration_min) DESC) AS rn
  FROM viewing
  WHERE app_id IS NOT NULL
  GROUP BY device_id, event_date, app_id
),
top_genre AS (
  SELECT device_id, event_date, genre AS top_genre,
    ROW_NUMBER() OVER (PARTITION BY device_id, event_date ORDER BY SUM(duration_min) DESC) AS rn
  FROM viewing
  WHERE genre IS NOT NULL
  GROUP BY device_id, event_date, genre
)
SELECT
  v.device_id,
  v.event_date,
  v.region,
  v.product_line,
  v.panel_type,
  ROUND(SUM(v.duration_min), 1) AS total_viewing_min,
  COUNT(*) AS session_count,
  ROUND(AVG(v.duration_min), 1) AS avg_session_min,
  ROUND(MAX(v.duration_min), 1) AS max_session_min,
  ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%LIVE%' OR UPPER(v.content_source) LIKE '%TV%' OR UPPER(v.broadcast_type) LIKE '%LIVE%' THEN v.duration_min ELSE 0 END), 1) AS live_tv_min,
  ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%OTT%' OR UPPER(v.content_source) LIKE '%STREAM%' OR UPPER(v.content_source) LIKE '%APP%' THEN v.duration_min ELSE 0 END), 1) AS ott_min,
  ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%HDMI%' OR UPPER(v.content_source) LIKE '%EXTERNAL%' THEN v.duration_min ELSE 0 END), 1) AS hdmi_min,
  ta.top_app,
  tg.top_genre,
  COUNT(DISTINCT v.channel_name) AS unique_channels,
  ROUND(SUM(CASE WHEN v.is_primetime THEN v.duration_min ELSE 0 END), 1) AS primetime_min,
  ROUND(SUM(CASE WHEN v.hdr_type != 'SDR' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS hdr_viewing_pct,
  ROUND(SUM(CASE WHEN v.resolution LIKE '%2160%' OR v.resolution LIKE '%3840%' OR v.resolution LIKE '%4K%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS `4k_viewing_pct`
FROM viewing v
LEFT JOIN top_app ta ON v.device_id = ta.device_id AND v.event_date = ta.event_date AND ta.rn = 1
LEFT JOIN top_genre tg ON v.device_id = tg.device_id AND v.event_date = tg.event_date AND tg.rn = 1
GROUP BY v.device_id, v.event_date, v.region, v.product_line, v.panel_type, ta.top_app, tg.top_genre;


-- ============================================================
-- Gold 2: content_popularity
-- 그레인: program_title × genre × content_source × event_date
-- 핵심: 시청자 수, reach_pct, completion_rate
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.gold.content_popularity
COMMENT 'Content popularity — audience reach, viewing time, regional distribution per program'
PARTITIONED BY (event_date)
AS
WITH total_devices AS (
  SELECT COUNT(DISTINCT device_id) AS total_active
  FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions
),
viewing_with_device AS (
  SELECT v.*, d.region, d.product_line
  FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions v
  INNER JOIN byungjun_lee_smarttv_training_catalog.silver.devices_cleaned d ON v.device_id = d.device_id
),
base AS (
  SELECT
    program_title,
    genre,
    content_source,
    event_date,
    COUNT(DISTINCT device_id) AS total_viewers,
    ROUND(SUM(duration_min), 1) AS total_viewing_min,
    ROUND(AVG(duration_min), 1) AS avg_viewing_min,
    ROUND(AVG(LEAST(duration_sec * 100.0 / GREATEST(1800, 1), 100)), 1) AS completion_rate
  FROM viewing_with_device
  GROUP BY program_title, genre, content_source, event_date
)
SELECT
  b.program_title,
  b.genre,
  b.content_source,
  b.event_date,
  b.total_viewers,
  b.total_viewing_min,
  b.avg_viewing_min,
  b.completion_rate,
  ROUND(b.total_viewers * 100.0 / GREATEST(td.total_active, 1), 2) AS reach_pct
FROM base b
CROSS JOIN total_devices td;


-- ============================================================
-- Gold 3: ad_campaign_kpi
-- 그레인: campaign_id × advertiser_name × ad_format × placement × event_date
-- 핵심: CTR, VCR, eCPM, revenue, frequency
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.gold.ad_campaign_kpi
COMMENT 'Ad campaign KPIs — impressions, CTR, VCR, revenue, frequency per campaign'
PARTITIONED BY (event_date)
AS
SELECT
  campaign_id,
  advertiser_name,
  ad_format,
  placement,
  event_date,
  COUNT(*) AS impressions,
  SUM(CASE WHEN is_clicked THEN 1 ELSE 0 END) AS clicks,
  SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) AS completions,
  SUM(CASE WHEN is_skipped THEN 1 ELSE 0 END) AS skips,
  SUM(CASE WHEN UPPER(event_type) LIKE '%ERROR%' THEN 1 ELSE 0 END) AS errors,
  ROUND(SUM(CASE WHEN is_clicked THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1), 2) AS ctr,
  ROUND(SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1), 2) AS vcr,
  ROUND(AVG(completion_pct), 1) AS avg_completion_pct,
  ROUND(SUM(COALESCE(bid_price_usd, 0)), 2) AS total_revenue_usd,
  ROUND(SUM(COALESCE(bid_price_usd, 0)) / GREATEST(COUNT(*), 1) * 1000, 2) AS ecpm,
  COUNT(DISTINCT device_id) AS unique_devices,
  ROUND(COUNT(*) * 1.0 / GREATEST(COUNT(DISTINCT device_id), 1), 1) AS frequency
FROM byungjun_lee_smarttv_training_catalog.silver.ad_funnel
GROUP BY campaign_id, advertiser_name, ad_format, placement, event_date;


-- ============================================================
-- Gold 4: device_health_score
-- 그레인: device_id × event_date
-- 핵심: health_score (0~100), health_grade (A~F), risk_factors 배열
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.gold.device_health_score
COMMENT 'Device health score — CPU/mem/temp metrics, crash/OOM counts, 0-100 health scoring'
PARTITIONED BY (event_date)
AS
WITH metrics AS (
  SELECT
    device_id, event_date,
    ROUND(AVG(avg_cpu_pct), 1) AS avg_cpu_pct,
    ROUND(AVG(avg_mem_used_pct), 1) AS avg_mem_pct,
    ROUND(MAX(peak_thermal_0_c), 1) AS peak_soc_temp,
    ROUND(MAX(peak_thermal_1_c), 1) AS peak_panel_temp,
    SUM(CASE WHEN any_thermal_throttle THEN 1 ELSE 0 END) AS throttle_count
  FROM byungjun_lee_smarttv_training_catalog.silver.system_metrics
  GROUP BY device_id, event_date
),
errors AS (
  SELECT
    device_id, event_date,
    SUM(CASE WHEN is_crash THEN 1 ELSE 0 END) AS crash_count,
    SUM(CASE WHEN is_oom THEN 1 ELSE 0 END) AS oom_count,
    SUM(CASE WHEN is_media_error THEN 1 ELSE 0 END) AS media_error_count
  FROM byungjun_lee_smarttv_training_catalog.silver.error_events
  GROUP BY device_id, event_date
),
boots AS (
  SELECT
    device_id, event_date,
    SUM(CASE WHEN event_type IN ('POWER_ON', 'COLD_BOOT', 'WARM_BOOT', 'REBOOT') THEN 1 ELSE 0 END) AS reboot_count,
    SUM(CASE WHEN previous_shutdown IN ('DIRTY', 'ABNORMAL', 'CRASH', 'WATCHDOG') THEN 1 ELSE 0 END) AS dirty_shutdown_count
  FROM byungjun_lee_smarttv_training_catalog.silver.boot_events
  GROUP BY device_id, event_date
),
combined AS (
  SELECT
    COALESCE(m.device_id, e.device_id, b.device_id) AS device_id,
    COALESCE(m.event_date, e.event_date, b.event_date) AS event_date,
    COALESCE(m.avg_cpu_pct, 0) AS avg_cpu_pct,
    COALESCE(m.avg_mem_pct, 0) AS avg_mem_pct,
    m.peak_soc_temp,
    m.peak_panel_temp,
    COALESCE(m.throttle_count, 0) AS throttle_count,
    COALESCE(e.crash_count, 0) AS crash_count,
    COALESCE(e.oom_count, 0) AS oom_count,
    COALESCE(e.media_error_count, 0) AS media_error_count,
    COALESCE(b.reboot_count, 0) AS reboot_count,
    COALESCE(b.dirty_shutdown_count, 0) AS dirty_shutdown_count
  FROM metrics m
  FULL OUTER JOIN errors e ON m.device_id = e.device_id AND m.event_date = e.event_date
  FULL OUTER JOIN boots b ON COALESCE(m.device_id, e.device_id) = b.device_id
                          AND COALESCE(m.event_date, e.event_date) = b.event_date
)
SELECT
  c.device_id,
  c.event_date,
  d.product_line,
  d.webos_version,
  c.avg_cpu_pct,
  c.avg_mem_pct,
  c.peak_soc_temp,
  c.peak_panel_temp,
  c.throttle_count,
  c.crash_count,
  c.oom_count,
  c.media_error_count,
  c.reboot_count,
  c.dirty_shutdown_count,
  GREATEST(0, LEAST(100,
    100
    - (c.crash_count * 10)
    - (c.oom_count * 8)
    - (c.throttle_count * 5)
    - (c.dirty_shutdown_count * 15)
    - (c.media_error_count * 3)
    - (CASE WHEN c.avg_cpu_pct > 80 THEN 5 ELSE 0 END)
    - (CASE WHEN COALESCE(c.peak_soc_temp, 0) > 75 THEN 5 ELSE 0 END)
  )) AS health_score,
  CASE
    WHEN GREATEST(0, LEAST(100, 100 - (c.crash_count*10) - (c.oom_count*8) - (c.throttle_count*5) - (c.dirty_shutdown_count*15) - (c.media_error_count*3) - (CASE WHEN c.avg_cpu_pct > 80 THEN 5 ELSE 0 END) - (CASE WHEN COALESCE(c.peak_soc_temp,0) > 75 THEN 5 ELSE 0 END))) >= 90 THEN 'A'
    WHEN GREATEST(0, LEAST(100, 100 - (c.crash_count*10) - (c.oom_count*8) - (c.throttle_count*5) - (c.dirty_shutdown_count*15) - (c.media_error_count*3) - (CASE WHEN c.avg_cpu_pct > 80 THEN 5 ELSE 0 END) - (CASE WHEN COALESCE(c.peak_soc_temp,0) > 75 THEN 5 ELSE 0 END))) >= 70 THEN 'B'
    WHEN GREATEST(0, LEAST(100, 100 - (c.crash_count*10) - (c.oom_count*8) - (c.throttle_count*5) - (c.dirty_shutdown_count*15) - (c.media_error_count*3) - (CASE WHEN c.avg_cpu_pct > 80 THEN 5 ELSE 0 END) - (CASE WHEN COALESCE(c.peak_soc_temp,0) > 75 THEN 5 ELSE 0 END))) >= 50 THEN 'C'
    WHEN GREATEST(0, LEAST(100, 100 - (c.crash_count*10) - (c.oom_count*8) - (c.throttle_count*5) - (c.dirty_shutdown_count*15) - (c.media_error_count*3) - (CASE WHEN c.avg_cpu_pct > 80 THEN 5 ELSE 0 END) - (CASE WHEN COALESCE(c.peak_soc_temp,0) > 75 THEN 5 ELSE 0 END))) >= 30 THEN 'D'
    ELSE 'F'
  END AS health_grade,
  ARRAY_COMPACT(ARRAY(
    CASE WHEN c.crash_count >= 3 THEN 'high_crash_rate' END,
    CASE WHEN c.oom_count >= 2 THEN 'oom_frequent' END,
    CASE WHEN c.throttle_count >= 3 THEN 'thermal_throttle' END,
    CASE WHEN c.dirty_shutdown_count >= 1 THEN 'dirty_shutdown' END,
    CASE WHEN c.avg_cpu_pct > 80 THEN 'high_cpu' END,
    CASE WHEN COALESCE(c.peak_soc_temp, 0) > 75 THEN 'high_temperature' END,
    CASE WHEN c.media_error_count >= 3 THEN 'media_errors' END
  )) AS risk_factors
FROM combined c
LEFT JOIN byungjun_lee_smarttv_training_catalog.silver.devices_cleaned d ON c.device_id = d.device_id;


-- ============================================================
-- Gold 5: streaming_qoe
-- 그레인: app_id × region × quality_tier × event_date
-- 핵심: P95 latency, buffering_rate, QoE score (0~100)
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.gold.streaming_qoe
COMMENT 'Streaming QoE — bitrate, latency, buffering, stall metrics and QoE score per app/region'
PARTITIONED BY (event_date)
AS
SELECT
  sq.app_id,
  d.region,
  sq.quality_tier,
  sq.event_date,
  COUNT(*) AS total_streams,
  COUNT(DISTINCT sq.device_id) AS unique_devices,
  ROUND(AVG(sq.current_bitrate_kbps), 0) AS avg_bitrate_kbps,
  ROUND(AVG(sq.latency_ms), 1) AS avg_latency_ms,
  ROUND(PERCENTILE_APPROX(sq.latency_ms, 0.95), 1) AS p95_latency_ms,
  ROUND(SUM(CASE WHEN sq.is_buffering THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1), 2) AS buffering_rate,
  ROUND(AVG(sq.stall_count), 1) AS avg_stall_count,
  ROUND(AVG(sq.stall_duration_total_ms / 1000.0), 2) AS avg_stall_duration_sec,
  ROUND(SUM(CASE WHEN sq.is_quality_degraded THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1), 2) AS bitrate_downgrade_rate,
  ROUND(SUM(CASE WHEN sq.is_outlier THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1), 2) AS error_rate,
  ROUND(GREATEST(0, LEAST(100,
    100
    - (SUM(CASE WHEN sq.is_buffering THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1)) * 0.5
    - AVG(sq.stall_count) * 5
    - (SUM(CASE WHEN sq.is_outlier THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1)) * 0.3
    - (CASE WHEN PERCENTILE_APPROX(sq.latency_ms, 0.95) > 200 THEN 10 ELSE 0 END)
  )), 1) AS qoe_score
FROM byungjun_lee_smarttv_training_catalog.silver.streaming_quality sq
INNER JOIN byungjun_lee_smarttv_training_catalog.silver.devices_cleaned d ON sq.device_id = d.device_id
GROUP BY sq.app_id, d.region, sq.quality_tier, sq.event_date;


-- ============================================================
-- Gold 6: user_engagement_360
-- 그레인: device_id (30일 스냅샷)
-- 핵심: 시청 행동, 디바이스 사용, 품질, 광고, 사용자 세그먼트
-- ============================================================
CREATE OR REPLACE TABLE byungjun_lee_smarttv_training_catalog.gold.user_engagement_360
COMMENT 'User engagement 360 — 30-day device profile with viewing, quality, ad, and segment data'
AS
WITH date_range AS (
  SELECT MAX(event_date) AS max_date, DATE_SUB(MAX(event_date), 30) AS min_date
  FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions
),
viewing_agg AS (
  SELECT v.device_id,
    ROUND(SUM(v.duration_min) / GREATEST(DATEDIFF(dr.max_date, dr.min_date), 1), 1) AS avg_daily_viewing_min,
    ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%LIVE%' OR UPPER(v.content_source) LIKE '%TV%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS live_tv_pct,
    ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%OTT%' OR UPPER(v.content_source) LIKE '%STREAM%' OR UPPER(v.content_source) LIKE '%APP%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS ott_pct,
    ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%HDMI%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS hdmi_pct,
    ROUND(SUM(CASE WHEN v.is_primetime THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS primetime_ratio,
    ROUND(SUM(CASE WHEN DAYOFWEEK(v.session_start) IN (1, 7) THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS weekend_ratio,
    COUNT(DISTINCT v.channel_name) AS unique_channels,
    ROUND(COUNT(*) * 1.0 / GREATEST(DATEDIFF(dr.max_date, dr.min_date), 1), 1) AS avg_sessions_per_day,
    ROUND(AVG(v.duration_min), 1) AS avg_session_duration_min
  FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions v
  CROSS JOIN date_range dr
  WHERE v.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY v.device_id, dr.max_date, dr.min_date
),
top_apps_agg AS (
  SELECT device_id, COLLECT_LIST(app_id) AS top_3_apps
  FROM (
    SELECT device_id, app_id,
      ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY SUM(duration_min) DESC) AS rn
    FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions v
    CROSS JOIN date_range dr
    WHERE v.event_date BETWEEN dr.min_date AND dr.max_date AND app_id IS NOT NULL
    GROUP BY device_id, app_id
  ) WHERE rn <= 3
  GROUP BY device_id
),
top_genres_agg AS (
  SELECT device_id, COLLECT_LIST(genre) AS top_3_genres
  FROM (
    SELECT device_id, genre,
      ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY SUM(duration_min) DESC) AS rn
    FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions v
    CROSS JOIN date_range dr
    WHERE v.event_date BETWEEN dr.min_date AND dr.max_date AND genre IS NOT NULL
    GROUP BY device_id, genre
  ) WHERE rn <= 3
  GROUP BY device_id
),
voice_agg AS (
  SELECT vc.device_id,
    ROUND(COUNT(*) * 1.0 / GREATEST(DATEDIFF(dr.max_date, dr.min_date), 1), 2) AS voice_usage_rate
  FROM byungjun_lee_smarttv_training_catalog.silver.voice_interactions vc
  CROSS JOIN date_range dr
  WHERE vc.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY vc.device_id, dr.max_date, dr.min_date
),
iot_agg AS (
  SELECT io.device_id, COUNT(DISTINCT io.iot_device_id) AS iot_device_count
  FROM byungjun_lee_smarttv_training_catalog.silver.iot_interactions io
  CROSS JOIN date_range dr
  WHERE io.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY io.device_id
),
hdmi_agg AS (
  SELECT h.device_id, COUNT(DISTINCT h.cec_device_name) AS hdmi_device_count
  FROM byungjun_lee_smarttv_training_catalog.bronze.input_switch_events h
  CROSS JOIN date_range dr
  WHERE CAST(h.timestamp AS DATE) BETWEEN dr.min_date AND dr.max_date
    AND h.cec_device_name IS NOT NULL AND TRIM(h.cec_device_name) != ''
  GROUP BY h.device_id
),
strm_agg AS (
  SELECT sq.device_id,
    ROUND(AVG(100 - (CASE WHEN sq.is_buffering THEN 20 ELSE 0 END) - (sq.stall_count * 5) - (CASE WHEN sq.is_outlier THEN 10 ELSE 0 END)), 1) AS avg_streaming_qoe
  FROM byungjun_lee_smarttv_training_catalog.silver.streaming_quality sq
  CROSS JOIN date_range dr
  WHERE sq.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY sq.device_id
),
crash_agg AS (
  SELECT er.device_id, COUNT(*) AS crash_frequency
  FROM byungjun_lee_smarttv_training_catalog.silver.error_events er
  CROSS JOIN date_range dr
  WHERE er.event_date BETWEEN dr.min_date AND dr.max_date AND er.is_crash
  GROUP BY er.device_id
),
ads_agg AS (
  SELECT af.device_id,
    ROUND((SUM(CASE WHEN af.is_clicked OR af.is_completed THEN 1 ELSE 0 END)) * 100.0 / GREATEST(COUNT(*), 1), 1) AS ad_engagement_rate,
    ROUND(AVG(af.completion_pct), 1) AS avg_ad_completion_pct
  FROM byungjun_lee_smarttv_training_catalog.silver.ad_funnel af
  CROSS JOIN date_range dr
  WHERE af.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY af.device_id
)
SELECT
  d.device_id, d.model_name, d.product_line, d.region, d.panel_type, d.webos_version,
  COALESCE(vw.avg_daily_viewing_min, 0) AS avg_daily_viewing_min,
  CASE
    WHEN COALESCE(vw.live_tv_pct, 0) >= COALESCE(vw.ott_pct, 0) AND COALESCE(vw.live_tv_pct, 0) >= COALESCE(vw.hdmi_pct, 0) THEN 'live_tv'
    WHEN COALESCE(vw.ott_pct, 0) >= COALESCE(vw.hdmi_pct, 0) THEN 'ott'
    ELSE 'hdmi'
  END AS preferred_content_source,
  ta.top_3_apps, tg.top_3_genres,
  COALESCE(vw.primetime_ratio, 0) AS primetime_ratio,
  COALESCE(vw.weekend_ratio, 0) AS weekend_ratio,
  COALESCE(vw.unique_channels, 0) AS channel_diversity,
  COALESCE(vw.avg_sessions_per_day, 0) AS avg_sessions_per_day,
  COALESCE(vw.avg_session_duration_min, 0) AS avg_session_duration_min,
  COALESCE(vc.voice_usage_rate, 0) AS voice_usage_rate,
  COALESCE(io.iot_device_count, 0) AS iot_device_count,
  COALESCE(hd.hdmi_device_count, 0) AS hdmi_device_count,
  COALESCE(sa.avg_streaming_qoe, 100) AS avg_streaming_qoe,
  COALESCE(cr.crash_frequency, 0) AS crash_frequency,
  COALESCE(ad.ad_engagement_rate, 0) AS ad_engagement_rate,
  COALESCE(ad.avg_ad_completion_pct, 0) AS avg_ad_completion_pct,
  CASE
    WHEN COALESCE(vw.avg_daily_viewing_min, 0) > 240 AND COALESCE(vw.avg_sessions_per_day, 0) > 5 THEN 'power_user'
    WHEN COALESCE(vw.ott_pct, 0) > 70 THEN 'ott_native'
    WHEN COALESCE(vw.live_tv_pct, 0) > 60 THEN 'linear_loyalist'
    WHEN COALESCE(vw.hdmi_pct, 0) > 40 THEN 'gamer'
    WHEN COALESCE(io.iot_device_count, 0) >= 5 THEN 'smart_home_enthusiast'
    ELSE 'casual'
  END AS user_segment
FROM byungjun_lee_smarttv_training_catalog.silver.devices_cleaned d
LEFT JOIN viewing_agg vw ON d.device_id = vw.device_id
LEFT JOIN top_apps_agg ta ON d.device_id = ta.device_id
LEFT JOIN top_genres_agg tg ON d.device_id = tg.device_id
LEFT JOIN voice_agg vc ON d.device_id = vc.device_id
LEFT JOIN iot_agg io ON d.device_id = io.device_id
LEFT JOIN hdmi_agg hd ON d.device_id = hd.device_id
LEFT JOIN strm_agg sa ON d.device_id = sa.device_id
LEFT JOIN crash_agg cr ON d.device_id = cr.device_id
LEFT JOIN ads_agg ad ON d.device_id = ad.device_id;
