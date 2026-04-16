#!/usr/bin/env python3
"""Generate the core 5 Silver tables (workshop Section 4-03).

Tables: viewing_sessions, system_metrics, ad_funnel, streaming_quality, error_events
Pattern: DROP existing → CREATE OR REPLACE with full transformation logic.
"""

import json
import time
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PROFILE = "fevm-smarttv"
WAREHOUSE_ID = "cc6084f1d2fff960"
HOST = "https://fevm-byungjun-lee-smarttv-training.cloud.databricks.com"
C = "byungjun_lee_smarttv_training_catalog"


def get_token():
    r = subprocess.run(
        ["databricks", "auth", "token", "--profile", PROFILE],
        capture_output=True, text=True,
    )
    return json.loads(r.stdout)["access_token"]


TOKEN = get_token()


def execute_sql(sql, label=""):
    body = json.dumps({
        "warehouse_id": WAREHOUSE_ID,
        "statement": sql,
        "wait_timeout": "0s",
    }).encode()
    req = urllib.request.Request(
        f"{HOST}/api/2.0/sql/statements",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    stmt_id = result["statement_id"]
    state = result["status"]["state"]

    while state in ("PENDING", "RUNNING"):
        time.sleep(3)
        req2 = urllib.request.Request(
            f"{HOST}/api/2.0/sql/statements/{stmt_id}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        with urllib.request.urlopen(req2) as resp2:
            result = json.loads(resp2.read())
        state = result["status"]["state"]

    if state == "SUCCEEDED":
        return f"✅ {label}: SUCCESS"
    else:
        error = result.get("status", {}).get("error", {}).get("message", "Unknown")
        return f"❌ {label}: {state} — {error}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SQL Definitions — Core 5 Silver Tables
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TABLES = {}

# ── 1. viewing_sessions ← bronze.viewing_logs ──
# - event_id dedup (latest timestamp)
# - NULL program_title → conditional fill
# - duration_sec 0~86400 filter, session_end >= session_start
# - Enrichment: event_date, viewing_hour, is_primetime, duration_min
# - Partition: event_date, Z-ORDER: device_id
TABLES["viewing_sessions"] = f"""
CREATE OR REPLACE TABLE {C}.silver.viewing_sessions
COMMENT 'Viewing sessions — deduplicated, duration validated, primetime/hour enriched'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY session_start DESC) AS rn
  FROM {C}.bronze.viewing_logs
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM valid
"""

# ── 2. system_metrics ← bronze.resource_utilization ──
# - Outlier clip: CPU/GPU/mem 0-100%, temp 0-100°C
# - 5-minute aggregation: AVG, MAX, SUM, BOOL_OR
# - Health status: critical (CPU>80 AND mem>85), warning, normal
# - Note: resource_utilization has NO event_id → dedup by (device_id, timestamp)
TABLES["system_metrics"] = f"""
CREATE OR REPLACE TABLE {C}.silver.system_metrics
COMMENT 'System metrics — 5-min aggregated, outliers clipped, health status classified'
PARTITIONED BY (event_date)
AS
WITH valid AS (
  SELECT r.*
  FROM {C}.bronze.resource_utilization r
  INNER JOIN {C}.bronze.devices dev ON r.device_id = dev.device_id
),
deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id, timestamp ORDER BY timestamp) AS rn
  FROM valid
),
clipped AS (
  SELECT
    device_id,
    timestamp,
    -- Clip to valid ranges
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
    -- 5-minute window key
    DATE_TRUNC('MINUTE', timestamp) - INTERVAL (MINUTE(timestamp) % 5) MINUTES AS window_5min
  FROM deduped
  WHERE rn = 1
)
SELECT
  device_id,
  window_5min AS timestamp,
  -- CPU
  ROUND(AVG(cpu_usage_pct), 1) AS avg_cpu_pct,
  ROUND(MAX(cpu_usage_pct), 1) AS max_cpu_pct,
  -- Memory
  ROUND(AVG(mem_used_pct), 1) AS avg_mem_used_pct,
  ROUND(MAX(mem_used_pct), 1) AS max_mem_used_pct,
  MAX(mem_total_kb) AS mem_total_kb,
  MIN(mem_available_kb) AS min_mem_available_kb,
  MAX(swap_used_kb) AS max_swap_used_kb,
  -- GPU
  ROUND(AVG(gpu_usage_pct), 1) AS avg_gpu_pct,
  ROUND(MAX(gpu_usage_pct), 1) AS max_gpu_pct,
  -- Thermal
  ROUND(MAX(thermal_zone_0_c), 1) AS peak_thermal_0_c,
  ROUND(MAX(thermal_zone_1_c), 1) AS peak_thermal_1_c,
  BOOL_OR(thermal_throttle_active) AS any_thermal_throttle,
  -- Storage & Network
  MIN(storage_available_mb) AS min_storage_available_mb,
  MAX(process_count) AS max_process_count,
  SUM(network_rx_bytes) AS total_rx_bytes,
  SUM(network_tx_bytes) AS total_tx_bytes,
  COUNT(*) AS sample_count,
  -- Health status
  CASE
    WHEN MAX(cpu_usage_pct) > 80 AND MAX(mem_used_pct) > 85 THEN 'critical'
    WHEN MAX(cpu_usage_pct) > 70 OR MAX(mem_used_pct) > 80
      OR MAX(COALESCE(thermal_zone_0_c, 0)) > 70 THEN 'warning'
    ELSE 'normal'
  END AS health_status,
  CAST(window_5min AS DATE) AS event_date
FROM clipped
GROUP BY device_id, window_5min
"""

# ── 3. ad_funnel ← bronze.ad_impressions ──
# - event_id dedup
# - VAST sequence validation (AD_REQUEST→AD_IMPRESSION→AD_START→Q1→MID→Q3→AD_COMPLETE)
# - NULL completion_pct → derive from event_type
# - Flags: is_completed, is_clicked, is_skipped
# - Time-to-action calculation
TABLES["ad_funnel"] = f"""
CREATE OR REPLACE TABLE {C}.silver.ad_funnel
COMMENT 'Ad funnel — VAST sequence validated, completion derived, click/skip flags'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.ad_impressions
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
),
sequenced AS (
  SELECT *,
    -- VAST event ordering
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
FROM sequenced
"""

# ── 4. streaming_quality ← bronze.streaming_buffer_events ──
# - event_id dedup
# - Outlier flagging: latency_ms > 10000 → is_outlier (retain, don't drop)
# - Quality tier: bitrate-based (4K/FHD/HD/SD)
# - NULL cdn_host → 'local_playback'
# - Flags: is_buffering, is_quality_degraded
TABLES["streaming_quality"] = f"""
CREATE OR REPLACE TABLE {C}.silver.streaming_quality
COMMENT 'Streaming quality — latency outliers flagged, quality tiered, buffering ratio calculated'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.streaming_buffer_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
  -- Quality tier by bitrate
  CASE
    WHEN current_bitrate_kbps >= 15000 THEN '4K'
    WHEN current_bitrate_kbps >= 5000  THEN 'FHD'
    WHEN current_bitrate_kbps >= 2500  THEN 'HD'
    ELSE 'SD'
  END AS quality_tier,
  -- Outlier flag
  CASE WHEN latency_ms > 10000 THEN true ELSE false END AS is_outlier,
  -- Buffering flag
  CASE WHEN UPPER(event_type) LIKE '%BUFFER%' OR stall_count > 0 THEN true ELSE false END AS is_buffering,
  -- Quality degradation flag
  CASE
    WHEN target_bitrate_kbps > 0
     AND current_bitrate_kbps < target_bitrate_kbps * 0.5 THEN true
    ELSE false
  END AS is_quality_degraded,
  -- Buffering ratio
  CASE
    WHEN buffer_duration_ms > 0 AND stall_duration_total_ms IS NOT NULL THEN
      ROUND(stall_duration_total_ms * 100.0 / buffer_duration_ms, 2)
    ELSE 0.0
  END AS stall_ratio_pct,
  CAST(timestamp AS DATE) AS event_date
FROM valid
"""

# ── 5. error_events ← bronze.error_crash_events ──
# - event_id dedup
# - Severity standardization (case normalize, invalid → UNKNOWN)
# - JOIN enrichment: devices adds product_line
# - Flags: is_oom, is_crash, is_media_error
# - error_category classification
TABLES["error_events"] = f"""
CREATE OR REPLACE TABLE {C}.silver.error_events
COMMENT 'Error/crash events — severity normalized, device-enriched, error categorized'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.error_crash_events
),
valid AS (
  SELECT
    d.*,
    dev.product_line,
    dev.model_name,
    dev.manufacturing_date
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
  WHERE d.rn = 1
)
SELECT
  event_id,
  device_id,
  timestamp,
  event_type,
  -- Severity standardization
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
  -- Device enrichment
  product_line,
  model_name,
  -- Derived flags
  CASE WHEN UPPER(error_detail) LIKE '%OUT OF MEMORY%' OR UPPER(error_detail) LIKE '%OOM%'
       OR UPPER(crash_signal) LIKE '%OOM%' THEN true ELSE false END AS is_oom,
  CASE WHEN UPPER(event_type) LIKE '%CRASH%' OR crash_signal IS NOT NULL THEN true ELSE false END AS is_crash,
  CASE WHEN UPPER(process_name) LIKE '%MEDIA%' OR UPPER(process_name) LIKE '%VIDEO%'
       OR UPPER(process_name) LIKE '%AUDIO%' OR UPPER(error_code) LIKE '%MEDIA%' THEN true ELSE false END AS is_media_error,
  -- Error category
  CASE
    WHEN UPPER(process_name) LIKE '%WEB%' OR UPPER(process_name) LIKE '%BROWSER%' OR UPPER(process_name) LIKE '%JS%' THEN 'web_runtime'
    WHEN UPPER(process_name) LIKE '%MEDIA%' OR UPPER(process_name) LIKE '%VIDEO%' OR UPPER(process_name) LIKE '%AUDIO%' THEN 'media'
    WHEN UPPER(process_name) LIKE '%KERNEL%' OR UPPER(process_name) LIKE '%SYSTEM%' OR UPPER(process_name) LIKE '%INIT%' THEN 'system'
    WHEN UPPER(process_name) LIKE '%APP%' OR UPPER(process_name) LIKE '%LUNA%' THEN 'app'
    WHEN UPPER(process_name) LIKE '%NETWORK%' OR UPPER(process_name) LIKE '%WIFI%' OR UPPER(process_name) LIKE '%NET%' THEN 'network'
    ELSE 'other'
  END AS error_category,
  -- Firmware age
  DATEDIFF(CAST(timestamp AS DATE), manufacturing_date) AS device_age_days,
  CAST(timestamp AS DATE) AS event_date
FROM valid
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # Step 1: Drop existing tables
    print("=" * 60)
    print("Step 1: Dropping existing tables...")
    for name in TABLES:
        r = execute_sql(f"DROP TABLE IF EXISTS {C}.silver.{name}", label=f"DROP {name}")
        print(r)
    print()

    # Step 2: Create all 5 tables in parallel
    print("=" * 60)
    print(f"Step 2: Creating {len(TABLES)} silver tables in parallel...")
    print("=" * 60)

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(execute_sql, sql, name): name
            for name, sql in TABLES.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            result = future.result()
            results[name] = result
            print(result)

    print()
    print("=" * 60)
    success = sum(1 for r in results.values() if r.startswith("✅"))
    fail = len(results) - success
    print(f"완료: {success} 성공 / {fail} 실패")
    print("=" * 60)
