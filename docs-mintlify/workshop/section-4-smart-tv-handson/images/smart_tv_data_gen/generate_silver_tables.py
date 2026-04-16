#!/usr/bin/env python3
"""Generate 10 Silver tables for Smart TV PoC.

Common transformation principles (from workshop Section 4):
- event_id deduplication (keep latest timestamp)
- device_id referential integrity (INNER JOIN to devices)
- event_date partitioning
- COMMENT on every table
- CREATE OR REPLACE (no DROP)
"""

import json
import time
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PROFILE = "fevm-smarttv"
WAREHOUSE_ID = "cc6084f1d2fff960"
HOST = "https://fevm-byungjun-lee-smarttv-training.cloud.databricks.com"
CATALOG = "byungjun_lee_smarttv_training_catalog"


def get_token():
    r = subprocess.run(
        ["databricks", "auth", "token", "--profile", PROFILE],
        capture_output=True, text=True,
    )
    return json.loads(r.stdout)["access_token"]


TOKEN = get_token()


def execute_sql(sql, label=""):
    """Submit SQL async and poll until done."""
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
# SQL Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

C = CATALOG

TABLES = {}

# ── 1. devices_cleaned ← bronze.devices ──
TABLES["devices_cleaned"] = f"""
CREATE OR REPLACE TABLE {C}.silver.devices_cleaned
COMMENT 'Cleansed device master — deduplicated, region/country standardized'
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY manufacturing_date DESC) AS rn
  FROM {C}.bronze.devices
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
WHERE rn = 1
"""

# ── 2. app_sessions ← bronze.app_launch_events ──
TABLES["app_sessions"] = f"""
CREATE OR REPLACE TABLE {C}.silver.app_sessions
COMMENT 'App sessions — deduplicated, orphan events filtered, session metrics enriched'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.app_launch_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM valid
"""

# ── 3. boot_events ← bronze.system_boot_events ──
TABLES["boot_events"] = f"""
CREATE OR REPLACE TABLE {C}.silver.boot_events
COMMENT 'System boot events — deduplicated, ON/OFF paired, boot performance tiered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.system_boot_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM paired
"""

# ── 4. media_sessions ← bronze.media_playback_events ──
TABLES["media_sessions"] = f"""
CREATE OR REPLACE TABLE {C}.silver.media_sessions
COMMENT 'Media playback sessions — START/STOP paired, NULL hdr_type → SDR, quality tiered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.media_playback_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM enriched
"""

# ── 5. network_events ← bronze.wifi_connection_events ──
TABLES["network_events"] = f"""
CREATE OR REPLACE TABLE {C}.silver.network_events
COMMENT 'WiFi connection events — signal strength corrected (양수→음수), CONNECTED/DISCONNECTED paired'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.wifi_connection_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM corrected
"""

# ── 6. acr_content ← bronze.acr_events ──
TABLES["acr_content"] = f"""
CREATE OR REPLACE TABLE {C}.silver.acr_content
COMMENT 'ACR content recognition — low confidence (<0.5) filtered, duplicate fingerprints removed'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.acr_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
WHERE fp_rn = 1
"""

# ── 7. voice_interactions ← bronze.voice_command_events ──
TABLES["voice_interactions"] = f"""
CREATE OR REPLACE TABLE {C}.silver.voice_interactions
COMMENT 'Voice commands — transcript normalized (LOWER/TRIM), empty transcripts filtered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.voice_command_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM valid
"""

# ── 8. iot_interactions ← bronze.thinq_device_events ──
TABLES["iot_interactions"] = f"""
CREATE OR REPLACE TABLE {C}.silver.iot_interactions
COMMENT 'ThinQ IoT interactions — command/ack paired, response time outliers (>30s) filtered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.thinq_device_events
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM paired
"""

# ── 9. panel_health ← bronze.panel_diagnostics ──
TABLES["panel_health"] = f"""
CREATE OR REPLACE TABLE {C}.silver.panel_health
COMMENT 'Panel diagnostics — OLED/LCD categorized, thermal status, panel age tiered, time-ordered'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.panel_diagnostics
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
FROM valid
"""

# ── 10. firmware_history ← bronze.firmware_updates ──
TABLES["firmware_history"] = f"""
CREATE OR REPLACE TABLE {C}.silver.firmware_history
COMMENT 'Firmware update history — OTA sequence validated, failures flagged, download speed calculated'
PARTITIONED BY (event_date)
AS
WITH deduped AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY timestamp DESC) AS rn
  FROM {C}.bronze.firmware_updates
),
valid AS (
  SELECT d.*
  FROM deduped d
  INNER JOIN {C}.bronze.devices dev ON d.device_id = dev.device_id
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
FROM sequenced
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # Step 1: Ensure silver schema exists
    print("=" * 60)
    print("Step 1: Creating silver schema...")
    schema_result = execute_sql(
        f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.silver COMMENT 'Silver layer — cleansed and enriched Smart TV data'",
        label="silver schema",
    )
    print(schema_result)
    print()

    # Step 2: Execute all 10 tables in parallel
    print("=" * 60)
    print(f"Step 2: Creating {len(TABLES)} silver tables in parallel...")
    print("=" * 60)

    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
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
