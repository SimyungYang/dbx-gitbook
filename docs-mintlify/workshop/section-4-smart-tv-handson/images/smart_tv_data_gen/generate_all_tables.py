"""
LG webOS Smart TV 가상 데이터 생성 스크립트
- byungjun_lee_smarttv_training_catalog.bronze 스키마에 16개 테이블 병렬 생성
- SQL Statement Execution API 사용 (SQL Warehouse)
"""

import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PROFILE = "fevm-smarttv"
WAREHOUSE_ID = "cc6084f1d2fff960"
CATALOG = "byungjun_lee_smarttv_training_catalog"
SCHEMA = "bronze"

def run_sql(statement, description=""):
    """Submit SQL via Statement Execution API and wait for completion."""
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": statement,
        "wait_timeout": "0s",  # async
    }
    result = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements",
         "--profile", PROFILE, "--json", json.dumps(payload)],
        capture_output=True, text=True
    )
    resp = json.loads(result.stdout)
    stmt_id = resp.get("statement_id")
    state = resp.get("status", {}).get("state", "UNKNOWN")

    if not stmt_id:
        return f"❌ {description}: Failed to submit - {resp}"

    # Poll for completion
    start = time.time()
    while state in ("PENDING", "RUNNING"):
        time.sleep(5)
        poll = subprocess.run(
            ["databricks", "api", "get", f"/api/2.0/sql/statements/{stmt_id}",
             "--profile", PROFILE],
            capture_output=True, text=True
        )
        poll_resp = json.loads(poll.stdout)
        state = poll_resp.get("status", {}).get("state", "UNKNOWN")
        elapsed = int(time.time() - start)
        if elapsed % 30 == 0 and elapsed > 0:
            print(f"  ⏳ {description}: {state} ({elapsed}s)")

    elapsed = int(time.time() - start)
    if state == "SUCCEEDED":
        return f"✅ {description}: 완료 ({elapsed}s)"
    else:
        error = poll_resp.get("status", {}).get("error", {})
        return f"❌ {description}: {state} ({elapsed}s) - {error.get('message', '')[:200]}"


# ============================================================
# Table SQL Generators
# ============================================================

def sql_system_boot_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.system_boot_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids,
         collect_list(webos_version) AS wvers,
         collect_list(firmware_version) AS fvers
  FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids, wvers, fvers,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 50000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_BOOT_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CAST(rand() * 86400000 AS BIGINT) AS monotonic_ms,
  CASE WHEN r1 < 0.30 THEN 'POWER_ON'
       WHEN r1 < 0.55 THEN 'POWER_OFF'
       WHEN r1 < 0.75 THEN 'STANDBY_ENTER'
       WHEN r1 < 0.90 THEN 'STANDBY_EXIT'
       WHEN r1 < 0.95 THEN 'COLD_BOOT'
       ELSE 'WARM_BOOT' END AS event_type,
  CASE WHEN r1 < 0.30 THEN
    element_at(array('user_remote','timer_wakeup','cec_wakeup','ota_update','watchdog_reset'),
      CAST(FLOOR(r2*5) AS INT)+1)
    ELSE NULL END AS boot_reason,
  CASE WHEN r1 < 0.30 THEN CAST(8000 + r3 * 7000 AS INT)
       WHEN r1 >= 0.95 THEN CAST(5000 + r3 * 7000 AS INT)
       WHEN r1 >= 0.90 THEN CAST(15000 + r3 * 10000 AS INT)
       ELSE NULL END AS boot_time_ms,
  CASE WHEN r4 < 0.85 THEN 'clean' WHEN r4 < 0.95 THEN 'dirty' ELSE 'watchdog' END AS previous_shutdown,
  wvers[didx] AS webos_version,
  fvers[didx] AS firmware_version,
  concat('5.15.', CAST(FLOOR(r5*50) AS INT), '-lge-tv') AS kernel_version,
  CAST(r5 * 604800 AS BIGINT) AS uptime_before_event_sec
FROM base
"""

def sql_resource_utilization():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.resource_utilization AS
WITH device_pool AS (
  SELECT collect_list(d.device_id) AS dids,
         collect_list(d.ram_mb) AS rams,
         collect_list(d.storage_mb) AS stores
  FROM (SELECT * FROM {CATALOG}.{SCHEMA}.devices ORDER BY rand() LIMIT 2000) d
),
base AS (
  SELECT seq, dids, rams, stores,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5,
    rand() AS r6, rand() AS r7, rand() AS r8, rand() AS r9, rand() AS r10,
    dateadd(MINUTE, seq % 43200, TIMESTAMP '2025-06-01') AS ts
  FROM (SELECT explode(sequence(1, 200000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  dids[didx] AS device_id,
  ts AS `timestamp`,
  ROUND(5 + r1 * 75, 1) AS cpu_usage_pct,
  rams[didx] * 1024 AS mem_total_kb,
  ROUND(40 + r2 * 45, 1) AS mem_used_pct,
  CAST(rams[didx] * 1024 * (1 - (40 + r2 * 45)/100) AS INT) AS mem_available_kb,
  CAST(r3 * 50000 AS INT) AS swap_used_kb,
  ROUND(5 + r4 * 65, 1) AS gpu_usage_pct,
  ROUND(35 + r1 * 40, 1) AS thermal_zone_0_c,
  ROUND(30 + r4 * 25, 1) AS thermal_zone_1_c,
  (35 + r1 * 40) > 70 AND r5 < 0.02 AS thermal_throttle_active,
  CAST(stores[didx] * 0.3 + r6 * stores[didx] * 0.5 AS INT) AS storage_available_mb,
  element_at(array('com.webos.app.livetv','netflix','youtube.leanback.v4','amazon','com.webos.app.home','disneyplus','wavve','tving'),
    CAST(FLOOR(r7*8) AS INT)+1) AS active_app_id,
  CAST(80 + r8 * 120 AS INT) AS process_count,
  CAST(r9 * 50000000 AS BIGINT) AS network_rx_bytes,
  CAST(r10 * 5000000 AS BIGINT) AS network_tx_bytes
FROM base
"""

def sql_firmware_updates():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.firmware_updates AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(firmware_version) AS fvers
  FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids, fvers,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS base_ts
  FROM (SELECT explode(sequence(1, 15000)) AS seq) x
  CROSS JOIN device_pool
),
timed AS (
  SELECT *,
    date_trunc('DAY', base_ts) + make_interval(0,0,0,0, 2 + CAST(r5*3 AS INT), CAST(r4*59 AS INT), 0) AS ts
  FROM base
)
SELECT
  concat('EVT_OTA_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.15 THEN 'OTA_CHECK'
       WHEN r1 < 0.25 THEN 'AVAILABLE'
       WHEN r1 < 0.40 THEN 'DOWNLOAD_START'
       WHEN r1 < 0.55 THEN 'DOWNLOAD_COMPLETE'
       WHEN r1 < 0.70 THEN 'INSTALL_START'
       WHEN r1 < 0.90 THEN 'INSTALL_COMPLETE'
       ELSE 'ROLLBACK' END AS event_type,
  fvers[didx] AS current_version,
  concat(substring(fvers[didx], 1, length(fvers[didx])-2), lpad(CAST(CAST(substring(fvers[didx], -2) AS INT)+1 AS STRING),2,'0')) AS target_version,
  CAST(300000000 + r2 * 500000000 AS BIGINT) AS download_size_bytes,
  CAST(60000 + r3 * 540000 AS BIGINT) AS download_duration_ms,
  CASE WHEN r4 < 0.95 THEN 'SUCCESS'
       WHEN r4 < 0.97 THEN 'FAIL_VERIFY'
       WHEN r4 < 0.99 THEN 'FAIL_SPACE'
       ELSE 'FAIL_POWER' END AS install_result,
  CASE WHEN r5 < 0.90 THEN 'stable' ELSE 'beta' END AS update_channel
FROM timed
"""

def sql_viewing_logs():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.viewing_logs AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(product_line) AS plines, collect_list(region) AS regions
  FROM (SELECT * FROM {CATALOG}.{SCHEMA}.devices ORDER BY rand() LIMIT 8000) d
),
base AS (
  SELECT seq, dids, plines, regions,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5,
    rand() AS r6, rand() AS r7, rand() AS r8, rand() AS r9,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS base_ts
  FROM (SELECT explode(sequence(1, 500000)) AS seq) x
  CROSS JOIN device_pool
),
enriched AS (
  SELECT *,
    CASE WHEN r1 < 0.35 THEN 'live_tv' WHEN r1 < 0.80 THEN 'ott_app' WHEN r1 < 0.95 THEN 'hdmi_input' ELSE 'usb_media' END AS content_source,
    CAST(CASE WHEN r3 < 0.15 THEN 1800 WHEN r3 < 0.40 THEN 3600 WHEN r3 < 0.60 THEN 5400 WHEN r3 < 0.80 THEN 1200 ELSE 600 END * (0.5 + r4) AS INT) AS dur
  FROM base
)
SELECT
  concat('EVT_VIEW_', date_format(base_ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  base_ts AS session_start,
  dateadd(SECOND, dur, base_ts) AS session_end,
  dur AS duration_sec,
  content_source,
  CASE WHEN content_source = 'ott_app' THEN
    element_at(array('netflix','youtube.leanback.v4','disneyplus','wavve','coupangplay','tving'), CAST(FLOOR(r5*6) AS INT)+1)
    WHEN content_source = 'live_tv' THEN 'com.webos.app.livetv'
    WHEN content_source = 'hdmi_input' THEN 'com.webos.app.hdmi'
    ELSE 'com.webos.app.photovideo' END AS app_id,
  CASE WHEN content_source = 'live_tv' THEN CAST(FLOOR(r6 * 50 + 1) AS STRING) ELSE NULL END AS channel_number,
  CASE WHEN content_source = 'live_tv' THEN
    element_at(array('KBS1','KBS2','MBC','SBS','EBS','tvN','JTBC','MBN','채널A','TV조선','OCN','Mnet'), CAST(FLOOR(r7*12) AS INT)+1)
    ELSE NULL END AS channel_name,
  CASE WHEN content_source = 'live_tv' THEN
    element_at(array('ATSC','DVB-T','IPTV','IP_STREAM'), CAST(FLOOR(r8*4) AS INT)+1) ELSE NULL END AS broadcast_type,
  CASE WHEN content_source = 'live_tv' THEN
    element_at(array('뉴스9','나혼자산다','놀면뭐하니','슬기로운의사생활','이상한변호사우영우','무한도전','런닝맨','전지적참견시점','골목식당','뉴스데스크'), CAST(FLOOR(r9*10) AS INT)+1) ELSE NULL END AS program_title,
  element_at(array('Drama','Entertainment','News','Sports','Movie','Kids','Documentary'), CAST(FLOOR(r2*7) AS INT)+1) AS genre,
  ROUND(-30 - r6 * 40, 1) AS signal_strength_dbm,
  CAST(60 + r7 * 40 AS INT) AS signal_quality_pct,
  CAST(200 + r8 * 2800 AS INT) AS tune_latency_ms,
  CASE WHEN r5 < 0.60 THEN '3840x2160' WHEN r5 < 0.90 THEN '1920x1080' ELSE '1280x720' END AS resolution,
  CASE WHEN plines[didx] LIKE 'OLED%' THEN
    element_at(array('DolbyVision','HDR10','HDR10Plus','HLG','SDR','SDR','SDR'), CAST(FLOOR(r9*7) AS INT)+1)
    ELSE element_at(array('HDR10','SDR','SDR','SDR','SDR'), CAST(FLOOR(r9*5) AS INT)+1)
  END AS hdr_type
FROM enriched
"""

def sql_app_launch_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.app_launch_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 300000)) AS seq) x
  CROSS JOIN device_pool
),
apps AS (
  SELECT *,
    element_at(array('com.webos.app.livetv','netflix','youtube.leanback.v4','amazon','disneyplus','com.webos.app.browser','com.webos.app.photovideo','com.webos.app.settings','wavve','coupangplay','tving','melon'),
      CAST(FLOOR(r1*12) AS INT)+1) AS app_id
  FROM base
)
SELECT
  concat('EVT_APP_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r2 < 0.30 THEN 'NL_APP_LAUNCH_BEGIN'
       WHEN r2 < 0.60 THEN 'NL_APP_LAUNCH_END'
       WHEN r2 < 0.85 THEN 'APP_CLOSE'
       WHEN r2 < 0.95 THEN 'APP_PAUSE'
       ELSE 'APP_RELAUNCH' END AS msgid,
  app_id,
  CASE WHEN app_id = 'netflix' THEN 'Netflix'
       WHEN app_id = 'youtube.leanback.v4' THEN 'YouTube'
       WHEN app_id = 'amazon' THEN 'Prime Video'
       WHEN app_id = 'disneyplus' THEN 'Disney+'
       WHEN app_id = 'com.webos.app.livetv' THEN 'Live TV'
       WHEN app_id = 'com.webos.app.browser' THEN '웹 브라우저'
       WHEN app_id = 'com.webos.app.settings' THEN '설정'
       WHEN app_id = 'wavve' THEN 'Wavve'
       WHEN app_id = 'coupangplay' THEN 'Coupang Play'
       WHEN app_id = 'tving' THEN 'TVING'
       WHEN app_id = 'melon' THEN 'Melon'
       ELSE 'Photo & Video' END AS app_name,
  concat(CAST(FLOOR(r3*5+1) AS STRING), '.', CAST(FLOOR(r4*9) AS STRING), '.', CAST(FLOOR(r5*20) AS STRING)) AS app_version,
  CASE WHEN r6 < 0.7 THEN 'com.webos.surfacemanager' ELSE 'com.webos.app.home' END AS caller_id,
  CASE WHEN r7 < 0.80 THEN 'normal' WHEN r7 < 0.95 THEN 'background' ELSE 'hidden' END AS launch_mode,
  CASE WHEN app_id = 'netflix' THEN CAST(2000+r3*2000 AS INT)
       WHEN app_id = 'youtube.leanback.v4' THEN CAST(1500+r3*1500 AS INT)
       WHEN app_id = 'com.webos.app.livetv' THEN CAST(800+r3*1200 AS INT)
       WHEN app_id = 'com.webos.app.settings' THEN CAST(500+r3*500 AS INT)
       ELSE CAST(1000+r3*2000 AS INT) END AS launch_time_ms,
  CASE WHEN r4 < 0.85 THEN 'user' WHEN r4 < 0.93 THEN 'system_oom' WHEN r4 < 0.98 THEN 'app_crash' ELSE 'relaunch' END AS close_reason,
  CAST(60 + r5 * 5400 AS INT) AS session_duration_sec,
  CAST(200000 + r6 * 800000 AS INT) AS memory_at_launch_kb
FROM apps
"""

def sql_input_switch_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.input_switch_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(product_line) AS plines
  FROM (SELECT * FROM {CATALOG}.{SCHEMA}.devices ORDER BY rand() LIMIT 6000) d
),
base AS (
  SELECT seq, dids, plines,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 80000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_INPUT_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  element_at(array('HDMI_1','HDMI_2','HDMI_3','HDMI_4'), CAST(FLOOR(r1*4) AS INT)+1) AS input_id,
  element_at(array('HDMI_1','HDMI_2','HDMI_3','HDMI_4','COMP_TV'), CAST(FLOOR(r2*5) AS INT)+1) AS previous_input_id,
  CASE WHEN r3 < 0.35 THEN 'stb' WHEN r3 < 0.60 THEN 'game_console' WHEN r3 < 0.75 THEN 'soundbar'
       WHEN r3 < 0.85 THEN 'bluray' WHEN r3 < 0.95 THEN 'pc' ELSE 'unknown' END AS device_type,
  CASE WHEN r3 < 0.35 THEN element_at(array('KT IPTV','SK Btv','LG U+ tv','Apple TV 4K','Fire TV Stick'), CAST(FLOOR(r4*5) AS INT)+1)
       WHEN r3 < 0.60 THEN element_at(array('PlayStation 5','XBOX Series X','Nintendo Switch'), CAST(FLOOR(r4*3) AS INT)+1)
       WHEN r3 < 0.75 THEN element_at(array('LG SP9YA','Samsung HW-Q990B','Sonos Arc'), CAST(FLOOR(r4*3) AS INT)+1)
       ELSE element_at(array('LG UBK90','Sony UBP-X800M2','Panasonic DP-UB9000'), CAST(FLOOR(r4*3) AS INT)+1) END AS cec_device_name,
  CASE WHEN plines[didx] LIKE 'OLED%' AND r5 < 0.80 THEN 'HDMI2.1' WHEN r5 < 0.30 THEN 'HDMI2.1' ELSE 'HDMI2.0' END AS hdmi_signal_type,
  r3 >= 0.35 AND r3 < 0.60 AND r5 < 0.90 AS allm_active,
  r3 >= 0.35 AND r3 < 0.60 AND (plines[didx] LIKE 'OLED%' AND r5 < 0.80 OR r5 < 0.30) AND r4 < 0.85 AS vrr_active
FROM base
"""

def sql_wifi_connection_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.wifi_connection_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(network_type) AS ntypes
  FROM {CATALOG}.{SCHEMA}.devices WHERE network_type LIKE 'wifi%'
),
base AS (
  SELECT seq, dids, ntypes,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 100000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_WIFI_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.40 THEN 'WIFI_CONNECTED' WHEN r1 < 0.65 THEN 'DISCONNECTED' WHEN r1 < 0.85 THEN 'DHCP_SUCCESS'
       WHEN r1 < 0.95 THEN 'SCAN_COMPLETE' WHEN r1 < 0.98 THEN 'AUTH_FAIL' ELSE 'DHCP_FAIL' END AS event_type,
  CASE WHEN r1 < 0.40 THEN 'connected' WHEN r1 < 0.65 THEN 'disconnected' WHEN r1 < 0.85 THEN 'connected' ELSE 'connecting' END AS state,
  element_at(array('HomeNet_5G','KT_GiGA_WiFi','SK_WiFi_Home','U+Net_5G','iptime_A8004','HomeNet_2G','KT_GiGA_2G'), CAST(FLOOR(r2*7) AS INT)+1) AS ssid,
  CASE WHEN r3 < 0.60 THEN 'WPA2-PSK' WHEN r3 < 0.85 THEN 'WPA3-SAE' WHEN r3 < 0.95 THEN 'WPA2-Enterprise' ELSE 'Open' END AS security_type,
  CASE WHEN ntypes[didx] LIKE '%5%' OR ntypes[didx] LIKE '%6%' THEN
    element_at(array(5180,5200,5220,5240,5745,5765), CAST(FLOOR(r4*6) AS INT)+1)
    ELSE element_at(array(2412,2437,2462), CAST(FLOOR(r4*3) AS INT)+1) END AS frequency_mhz,
  CASE WHEN ntypes[didx] LIKE '%5%' OR ntypes[didx] LIKE '%6%' THEN
    element_at(array(36,40,44,48,149,153), CAST(FLOOR(r4*6) AS INT)+1)
    ELSE element_at(array(1,6,11), CAST(FLOOR(r4*3) AS INT)+1) END AS channel,
  CAST(-30 - r5 * 50 AS INT) AS signal_strength_dbm,
  CASE WHEN ntypes[didx] LIKE '%5%' OR ntypes[didx] LIKE '%6%' THEN CAST(300 + r6 * 900 AS INT) ELSE CAST(72 + r6 * 228 AS INT) END AS link_speed_mbps,
  concat('192.168.', CAST(FLOOR(r7*3) AS INT), '.', CAST(FLOOR(r7*254)+1 AS INT)) AS ip_address,
  concat('192.168.', CAST(FLOOR(r7*3) AS INT), '.1') AS gateway,
  CASE WHEN r5 < 0.5 THEN '8.8.8.8,8.8.4.4' ELSE '1.1.1.1,1.0.0.1' END AS dns_servers
FROM base
"""

def sql_streaming_buffer_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.streaming_buffer_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 150000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_BUF_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.30 THEN 'BITRATE_SWITCH' WHEN r1 < 0.55 THEN 'STREAM_START' WHEN r1 < 0.65 THEN 'BUFFER_UNDERRUN'
       WHEN r1 < 0.75 THEN 'BUFFER_RECOVERY' WHEN r1 < 0.95 THEN 'STREAM_STOP' ELSE 'STREAM_ERROR' END AS event_type,
  element_at(array('netflix','youtube.leanback.v4','wavve','coupangplay','tving','disneyplus'), CAST(FLOOR(r2*6) AS INT)+1) AS app_id,
  ROUND(r3 * 100, 1) AS buffer_level_pct,
  CAST(r4 * 10000 AS INT) AS buffer_duration_ms,
  CASE WHEN r1 >= 0.55 AND r1 < 0.65 THEN CAST(1 + r5 * 9 AS INT) ELSE 0 END AS stall_count,
  CASE WHEN r1 >= 0.55 AND r1 < 0.65 THEN CAST(500 + r6 * 9500 AS INT) ELSE 0 END AS stall_duration_total_ms,
  CASE WHEN r3 < 0.50 THEN CAST(15000 + r4 * 10000 AS INT)
       WHEN r3 < 0.85 THEN CAST(3000 + r4 * 5000 AS INT)
       ELSE CAST(1500 + r4 * 1500 AS INT) END AS current_bitrate_kbps,
  CAST(20000 + r5 * 5000 AS INT) AS target_bitrate_kbps,
  CASE WHEN r2 < 0.30 THEN concat('ipv4-c', lpad(CAST(FLOOR(r6*999) AS STRING),3,'0'), '-sel.nflxvideo.net')
       WHEN r2 < 0.55 THEN concat('rr', CAST(FLOOR(r6*9)+1 AS STRING), '---sn-', 'ogul7n7e.googlevideo.com')
       ELSE concat('cdn-', CAST(FLOOR(r6*20)+1 AS STRING), '.stream.wavve.com') END AS cdn_host,
  CAST(10 + r7 * 190 AS INT) AS latency_ms,
  CAST(5 + r7 * 95 AS INT) AS dns_resolve_ms
FROM base
"""

def sql_media_playback_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.media_playback_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(product_line) AS plines
  FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids, plines,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5,
    rand() AS r6, rand() AS r7, rand() AS r8, rand() AS r9, rand() AS r10,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 200000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_MEDIA_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.35 THEN 'MEDIA_PLAY_START' WHEN r1 < 0.65 THEN 'PLAY_STOP' WHEN r1 < 0.80 THEN 'RESOLUTION_CHANGE'
       WHEN r1 < 0.92 THEN 'HDR_MODE_CHANGE' ELSE 'CODEC_SWITCH' END AS event_type,
  CASE WHEN r2 < 0.40 THEN 'HEVC' WHEN r2 < 0.60 THEN 'AV1' WHEN r2 < 0.75 THEN 'VP9' WHEN r2 < 0.95 THEN 'H264' ELSE 'MPEG2' END AS video_codec,
  CASE WHEN r2 < 0.60 THEN 'Main10' WHEN r2 < 0.85 THEN 'Main' ELSE 'High' END AS video_profile,
  CASE WHEN r3 < 0.50 THEN '3840x2160' WHEN r3 < 0.85 THEN '1920x1080' WHEN r3 < 0.95 THEN '1280x720' ELSE '7680x4320' END AS resolution,
  element_at(array(59.94, 23.976, 29.97, 60.0, 120.0), CAST(FLOOR(r4*5) AS INT)+1) AS frame_rate,
  CASE WHEN r2 < 0.60 THEN 10 ELSE 8 END AS bit_depth,
  CASE WHEN r3 < 0.50 THEN 'BT.2020' ELSE 'BT.709' END AS color_space,
  CASE WHEN plines[didx] LIKE 'OLED%' THEN
    element_at(array('DolbyVision','HDR10','HDR10Plus','HLG','SDR','SDR','SDR'), CAST(FLOOR(r5*7) AS INT)+1)
    ELSE element_at(array('HDR10','HDR10Plus','HLG','SDR','SDR','SDR','SDR','SDR'), CAST(FLOOR(r5*8) AS INT)+1)
  END AS hdr_type,
  CASE WHEN r5 < 0.25 AND plines[didx] LIKE 'OLED%' THEN element_at(array('dvhe.05.06','dvhe.08.06'), CAST(FLOOR(r6*2) AS INT)+1) ELSE NULL END AS dolby_vision_profile,
  CAST(500 + r6 * 3500 AS INT) AS max_cll_nits,
  CAST(200 + r7 * 800 AS INT) AS max_fall_nits,
  CASE WHEN r8 < 0.20 THEN 'EAC3_ATMOS' WHEN r8 < 0.50 THEN 'EAC3' WHEN r8 < 0.80 THEN 'AAC' ELSE 'AC3' END AS audio_codec,
  CASE WHEN r8 < 0.20 THEN '7.1.4' WHEN r8 < 0.50 THEN '5.1' ELSE '2.0' END AS audio_channels,
  r9 < 0.30 AS audio_passthrough,
  CASE WHEN r10 < 0.45 THEN 'ott' WHEN r10 < 0.75 THEN 'live_tv' WHEN r10 < 0.90 THEN 'hdmi' ELSE 'usb' END AS content_source,
  CASE WHEN r10 < 0.45 THEN element_at(array('widevine','widevine','playready'), CAST(FLOOR(r9*3) AS INT)+1) ELSE 'none' END AS drm_type
FROM base
"""

def sql_acr_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.acr_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(region) AS regions
  FROM {CATALOG}.{SCHEMA}.devices WHERE thinq_connected = true
),
base AS (
  SELECT seq, dids, regions,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 300000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_ACR_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.70 THEN 'ACR_MATCH' WHEN r1 < 0.90 THEN 'ACR_NO_MATCH' ELSE 'ACR_FINGERPRINT' END AS event_type,
  md5(concat(CAST(seq AS STRING), CAST(r2 AS STRING))) AS fingerprint_hash,
  CASE WHEN r1 < 0.70 THEN ROUND(0.85 + r3 * 0.14, 3) ELSE NULL END AS match_confidence,
  CASE WHEN r1 < 0.70 THEN concat('EP', lpad(CAST(FLOOR(r4 * 999999999999) AS STRING), 12, '0')) ELSE NULL END AS content_id,
  CASE WHEN r1 < 0.70 THEN
    CASE WHEN regions[didx] IN ('KR') THEN
      element_at(array('슬기로운의사생활','이상한변호사우영우','나혼자산다','놀면뭐하니','KBS뉴스9','무한도전','런닝맨','전지적참견시점','골목식당','뉴스데스크'), CAST(FLOOR(r5*10) AS INT)+1)
    ELSE
      element_at(array('Breaking Bad','The Office','NFL Football','The Crown','Stranger Things','Game of Thrones','Friends','Seinfeld','The Mandalorian','Ted Lasso'), CAST(FLOOR(r5*10) AS INT)+1)
    END ELSE NULL END AS program_title,
  CASE WHEN regions[didx] = 'KR' THEN element_at(array('tvN','MBC','SBS','KBS','JTBC','MBN'), CAST(FLOOR(r6*6) AS INT)+1)
       ELSE element_at(array('NBC','CBS','ABC','FOX','HBO','Netflix'), CAST(FLOOR(r6*6) AS INT)+1) END AS network_name,
  element_at(array('Drama','News','Sports','Entertainment','Movie','Documentary'), CAST(FLOOR(r7*6) AS INT)+1) AS genre,
  CASE WHEN r2 < 0.45 THEN 'linear_tv' WHEN r2 < 0.75 THEN 'ott_stream' WHEN r2 < 0.95 THEN 'hdmi_external' ELSE 'gaming' END AS content_type,
  r2 < 0.45 AND r3 < 0.25 AS is_ad_break,
  CASE WHEN r2 < 0.45 AND r3 < 0.25 THEN
    CASE WHEN regions[didx] = 'KR' THEN element_at(array('삼성전자','현대자동차','LG전자','SK텔레콤','롯데'), CAST(FLOOR(r4*5) AS INT)+1)
         ELSE element_at(array('Toyota','Apple','Amazon','Google','Microsoft'), CAST(FLOOR(r4*5) AS INT)+1) END
    ELSE NULL END AS ad_brand,
  CASE WHEN regions[didx] = 'KR' THEN element_at(array('KR_SEOUL','KR_BUSAN','KR_INCHEON','KR_DAEGU','KR_DAEJEON'), CAST(FLOOR(r5*5) AS INT)+1)
       ELSE element_at(array('US_501','US_803','US_602','US_623','US_753'), CAST(FLOOR(r5*5) AS INT)+1) END AS dma_code
FROM base
"""

def sql_ad_impressions():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.ad_impressions AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7, rand() AS r8,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 200000)) AS seq) x
  CROSS JOIN device_pool
)
SELECT
  concat('EVT_AD_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.10 THEN 'AD_REQUEST' WHEN r1 < 0.25 THEN 'IMPRESSION' WHEN r1 < 0.40 THEN 'START'
       WHEN r1 < 0.50 THEN 'FIRST_QUARTILE' WHEN r1 < 0.60 THEN 'MIDPOINT' WHEN r1 < 0.70 THEN 'THIRD_QUARTILE'
       WHEN r1 < 0.80 THEN 'COMPLETE' WHEN r1 < 0.90 THEN 'SKIP' WHEN r1 < 0.95 THEN 'CLICK' ELSE 'ERROR' END AS event_type,
  element_at(array('lg_home_banner_01','lg_home_banner_02','lg_channels_preroll','lg_epg_native','lg_screensaver_01'), CAST(FLOOR(r2*5) AS INT)+1) AS ad_unit_id,
  concat('CR_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(FLOOR(r3*999) AS STRING), 3, '0')) AS creative_id,
  concat('CAMP_Q', CAST(quarter(ts) AS STRING), '_2025_', lpad(CAST(FLOOR(r4*9999) AS STRING), 4, '0')) AS campaign_id,
  element_at(array('Samsung Electronics','Hyundai Motor','LG Electronics','SK Telecom','Lotte','Toyota','Apple','Amazon','Nike','Coca-Cola'), CAST(FLOOR(r5*10) AS INT)+1) AS advertiser_name,
  CASE WHEN r6 < 0.30 THEN 'display_banner' WHEN r6 < 0.55 THEN 'video_preroll' WHEN r6 < 0.75 THEN 'native_tile'
       WHEN r6 < 0.90 THEN 'screensaver' ELSE 'pause_ad' END AS ad_format,
  element_at(array(15, 15, 30, 30, 60), CAST(FLOOR(r7*5) AS INT)+1) AS ad_duration_sec,
  ROUND(r8 * 100, 1) AS completion_pct,
  CASE WHEN r3 < 0.35 THEN 'home_screen' WHEN r3 < 0.60 THEN 'lg_channels' WHEN r3 < 0.75 THEN 'content_store'
       WHEN r3 < 0.90 THEN 'epg' ELSE 'screensaver' END AS placement,
  CASE WHEN r4 < 0.60 THEN 'CPM' WHEN r4 < 0.85 THEN 'CPC' ELSE 'CPCV' END AS revenue_model,
  CASE WHEN r4 < 0.60 THEN ROUND(5 + r5 * 20, 2)
       WHEN r4 < 0.85 THEN ROUND(0.5 + r5 * 2.5, 2)
       ELSE ROUND(10 + r5 * 30, 2) END AS bid_price_usd,
  ROUND(70 + r6 * 30, 1) AS viewability_pct
FROM base
"""

def sql_thinq_device_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.thinq_device_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(region) AS regions
  FROM {CATALOG}.{SCHEMA}.devices WHERE thinq_connected = true
),
base AS (
  SELECT seq, dids, regions,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 50000)) AS seq) x
  CROSS JOIN device_pool
),
typed AS (
  SELECT *,
    CASE WHEN r2 < 0.25 THEN 'air_conditioner' WHEN r2 < 0.45 THEN 'washer' WHEN r2 < 0.65 THEN 'refrigerator'
         WHEN r2 < 0.80 THEN 'air_purifier' WHEN r2 < 0.90 THEN 'robot_vacuum' WHEN r2 < 0.95 THEN 'dryer' ELSE 'styler' END AS iot_type
  FROM base
)
SELECT
  concat('EVT_IOT_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.35 THEN 'STATUS_CHANGE' WHEN r1 < 0.60 THEN 'COMMAND_SENT' WHEN r1 < 0.80 THEN 'COMMAND_ACK'
       WHEN r1 < 0.90 THEN 'DISCOVERED' WHEN r1 < 0.95 THEN 'PAIRED' ELSE 'REMOVED' END AS event_type,
  concat('LG_', upper(substring(iot_type, 1, 3)), '_', regions[didx], '_', lpad(CAST(FLOOR(r3*999999) AS STRING), 6, '0')) AS iot_device_id,
  iot_type AS iot_device_type,
  concat('LG', upper(substring(iot_type, 1, 2)), '-', CAST(FLOOR(r4*9000+1000) AS STRING), 'S') AS iot_device_model,
  CASE WHEN r5 < 0.70 THEN 'thinq_cloud' WHEN r5 < 0.90 THEN 'matter' ELSE 'wifi_direct' END AS protocol,
  CASE WHEN r6 < 0.85 THEN 'online' WHEN r6 < 0.95 THEN 'offline' ELSE 'pairing' END AS connection_status,
  CASE WHEN iot_type = 'air_conditioner' THEN element_at(array('power_on','set_temperature','get_status','set_mode'), CAST(FLOOR(r3*4) AS INT)+1)
       WHEN iot_type = 'washer' THEN element_at(array('start_cycle','get_status','pause','set_program'), CAST(FLOOR(r3*4) AS INT)+1)
       WHEN iot_type = 'robot_vacuum' THEN element_at(array('start_clean','stop','go_charge','get_status'), CAST(FLOOR(r3*4) AS INT)+1)
       ELSE element_at(array('power_on','power_off','get_status','set_mode'), CAST(FLOOR(r3*4) AS INT)+1) END AS command,
  CASE WHEN r4 < 0.90 THEN 'success' WHEN r4 < 0.95 THEN 'timeout' WHEN r4 < 0.98 THEN 'device_offline' ELSE 'invalid_command' END AS command_result,
  CASE WHEN r5 < 0.70 THEN CAST(300 + r6 * 1700 AS INT) WHEN r5 < 0.90 THEN CAST(50 + r6 * 250 AS INT) ELSE CAST(100 + r6 * 400 AS INT) END AS response_time_ms
FROM typed
"""

def sql_voice_command_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.voice_command_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(voice_assistant) AS vassists, collect_list(region) AS regions
  FROM {CATALOG}.{SCHEMA}.devices WHERE voice_assistant != 'none'
),
base AS (
  SELECT seq, dids, vassists, regions,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 80000)) AS seq) x
  CROSS JOIN device_pool
),
intent_data AS (
  SELECT *,
    CASE WHEN r2 < 0.20 THEN 'channel_change' WHEN r2 < 0.35 THEN 'volume_control' WHEN r2 < 0.60 THEN 'search_content'
         WHEN r2 < 0.75 THEN 'smart_home_control' WHEN r2 < 0.90 THEN 'app_launch' ELSE 'general_query' END AS intent
  FROM base
)
SELECT
  concat('EVT_VOICE_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.15 THEN 'VOICE_WAKE' WHEN r1 < 0.35 THEN 'COMMAND_START' WHEN r1 < 0.55 THEN 'COMMAND_END'
       WHEN r1 < 0.85 THEN 'RESULT' WHEN r1 < 0.95 THEN 'ERROR' ELSE 'CANCEL' END AS event_type,
  vassists[didx] AS assistant_type,
  CASE WHEN vassists[didx] = 'lg_thinq_ai' THEN '하이 엘지'
       WHEN vassists[didx] = 'alexa' THEN 'Alexa'
       ELSE 'Hey Google' END AS wake_word,
  CASE WHEN regions[didx] = 'KR' THEN
    CASE WHEN intent = 'channel_change' THEN element_at(array('KBS로 바꿔줘','다음 채널','11번 틀어줘','SBS 뉴스 보여줘','tvN으로 변경'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'volume_control' THEN element_at(array('소리 올려줘','소리 줄여줘','음소거 해줘','볼륨 15로 맞춰줘','소리 크게'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'search_content' THEN element_at(array('액션 영화 추천해줘','BTS 뮤직비디오','오늘 드라마 뭐 해','넷플릭스 인기작','범죄도시 검색'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'smart_home_control' THEN element_at(array('에어컨 24도로 맞춰줘','로봇청소기 시작','공기청정기 켜줘','세탁기 상태 알려줘','거실 불 꺼줘'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'app_launch' THEN element_at(array('넷플릭스 틀어줘','유튜브 열어줘','웨이브 켜줘','디즈니플러스 실행','설정 열어'), CAST(FLOOR(r3*5) AS INT)+1)
         ELSE element_at(array('내일 날씨 알려줘','지금 몇 시야','오늘 뉴스 알려줘','타이머 10분','알람 맞춰줘'), CAST(FLOOR(r3*5) AS INT)+1) END
    ELSE
    CASE WHEN intent = 'channel_change' THEN element_at(array('Switch to NBC','Next channel','Channel 11','Go to ESPN','Turn to CNN'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'volume_control' THEN element_at(array('Volume up','Turn it down','Mute','Set volume to 15','Louder'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'search_content' THEN element_at(array('Find action movies','Play BTS music video','What is on tonight','Show popular on Netflix','Search Avengers'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'smart_home_control' THEN element_at(array('Set AC to 72','Start robot vacuum','Turn on air purifier','Washer status','Turn off lights'), CAST(FLOOR(r3*5) AS INT)+1)
         WHEN intent = 'app_launch' THEN element_at(array('Open Netflix','Launch YouTube','Start Disney Plus','Open settings','Play Spotify'), CAST(FLOOR(r3*5) AS INT)+1)
         ELSE element_at(array('What is the weather','What time is it','Tell me the news','Set timer 10 min','Set alarm'), CAST(FLOOR(r3*5) AS INT)+1) END
  END AS transcript,
  intent,
  CASE WHEN r4 < 0.75 THEN ROUND(0.85 + r5 * 0.14, 3)
       WHEN r4 < 0.87 THEN ROUND(0.50 + r5 * 0.34, 3)
       ELSE ROUND(0.10 + r5 * 0.39, 3) END AS confidence_score,
  CASE WHEN r4 < 0.75 THEN 'success' WHEN r4 < 0.87 THEN 'partial_match' WHEN r4 < 0.95 THEN 'no_match'
       WHEN r4 < 0.98 THEN 'timeout' ELSE 'error' END AS result_status,
  CAST(500 + r6 * 3000 AS INT) AS audio_duration_ms,
  CASE WHEN vassists[didx] = 'lg_thinq_ai' THEN CAST(500 + r7 * 1000 AS INT)
       WHEN vassists[didx] = 'alexa' THEN CAST(300 + r7 * 900 AS INT)
       ELSE CAST(200 + r7 * 800 AS INT) END AS processing_latency_ms,
  CASE WHEN r5 < 0.80 THEN 'magic_remote' ELSE 'built_in' END AS microphone_source,
  CASE WHEN regions[didx] = 'KR' THEN 'ko-KR' WHEN regions[didx] = 'US' THEN 'en-US' WHEN regions[didx] = 'JP' THEN 'ja-JP'
       WHEN regions[didx] = 'EU' THEN element_at(array('en-GB','de-DE','fr-FR'), CAST(FLOOR(r6*3) AS INT)+1) ELSE 'en-US' END AS language
FROM intent_data
"""

def sql_app_lifecycle_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.app_lifecycle_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 100000)) AS seq) x
  CROSS JOIN device_pool
),
app_data AS (
  SELECT *,
    element_at(array('netflix','youtube.leanback.v4','disneyplus','wavve','tving','coupangplay','com.webos.app.browser','com.webos.app.miracast','apple.tv','amazon','melon','spotify','bugs.music','flo','khan.academy','ted','duolingo','com.webos.app.settings'),
      CAST(FLOOR(r2*18) AS INT)+1) AS app_id
  FROM base
)
SELECT
  concat('EVT_APPLIFE_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN r1 < 0.50 THEN 'APP_UPDATE' WHEN r1 < 0.75 THEN 'UPDATE_CHECK' WHEN r1 < 0.90 THEN 'APP_INSTALL' ELSE 'APP_UNINSTALL' END AS event_type,
  app_id,
  CASE WHEN app_id = 'netflix' THEN 'Netflix' WHEN app_id = 'youtube.leanback.v4' THEN 'YouTube'
       WHEN app_id = 'disneyplus' THEN 'Disney+' WHEN app_id = 'wavve' THEN 'Wavve'
       WHEN app_id = 'tving' THEN 'TVING' WHEN app_id = 'coupangplay' THEN 'Coupang Play'
       WHEN app_id = 'melon' THEN 'Melon' WHEN app_id = 'spotify' THEN 'Spotify'
       WHEN app_id = 'com.webos.app.browser' THEN '웹 브라우저'
       ELSE app_id END AS app_name,
  concat(CAST(FLOOR(r3*5+1) AS STRING), '.', CAST(FLOOR(r4*9) AS STRING), '.', CAST(FLOOR(r5*20) AS STRING)) AS app_version,
  CASE WHEN r1 < 0.50 THEN concat(CAST(FLOOR(r3*5) AS STRING), '.', CAST(FLOOR(r4*9) AS STRING), '.', CAST(FLOOR(r5*20) AS STRING)) ELSE NULL END AS previous_version,
  CASE WHEN app_id IN ('netflix','youtube.leanback.v4','disneyplus','wavve','tving','coupangplay','amazon','apple.tv') THEN CAST(30000000 + r6 * 50000000 AS BIGINT)
       WHEN app_id LIKE 'com.webos%' THEN CAST(5000000 + r6 * 15000000 AS BIGINT)
       ELSE CAST(10000000 + r6 * 40000000 AS BIGINT) END AS app_size_bytes,
  CASE WHEN r7 < 0.60 THEN 'content_store' WHEN r7 < 0.90 THEN 'auto_update' ELSE 'preloaded' END AS install_source,
  CASE WHEN app_id IN ('netflix','youtube.leanback.v4','disneyplus','wavve','tving','coupangplay','amazon','melon','spotify') THEN 'Entertainment'
       WHEN app_id LIKE '%khan%' OR app_id LIKE '%ted%' OR app_id LIKE '%duolingo%' THEN 'Education'
       WHEN app_id LIKE 'com.webos%' THEN 'Utility'
       ELSE 'Lifestyle' END AS category,
  CAST(5000 + r3 * 60000 AS INT) AS download_duration_ms,
  CASE WHEN r4 < 0.95 THEN 'SUCCESS' WHEN r4 < 0.97 THEN 'FAIL_SPACE' WHEN r4 < 0.99 THEN 'FAIL_NETWORK'
       WHEN r4 < 0.995 THEN 'FAIL_VERIFY' ELSE 'FAIL_INCOMPATIBLE' END AS install_result,
  CAST(2000 + r5 * 14000 AS INT) AS storage_after_mb
FROM app_data
"""

def sql_panel_diagnostics():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.panel_diagnostics AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(product_line) AS plines, collect_list(panel_type) AS ptypes
  FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids, plines, ptypes,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7, rand() AS r8,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS base_ts
  FROM (SELECT explode(sequence(1, 30000)) AS seq) x
  CROSS JOIN device_pool
),
timed AS (
  SELECT *, date_trunc('DAY', base_ts) + make_interval(0,0,0,0, 3 + CAST(r8*2 AS INT), CAST(r7*59 AS INT), 0) AS ts
  FROM base
)
SELECT
  concat('EVT_PANEL_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  CASE WHEN plines[didx] LIKE 'OLED%' THEN
    CASE WHEN r1 < 0.25 THEN 'PIXEL_REFRESH_SHORT' WHEN r1 < 0.40 THEN 'PIXEL_REFRESH_LONG' WHEN r1 < 0.55 THEN 'JB_COMPENSATION'
         WHEN r1 < 0.70 THEN 'OFFRS_COMPENSATION' WHEN r1 < 0.80 THEN 'ABL_ADJUST' WHEN r1 < 0.90 THEN 'TPC_ADJUST' ELSE 'GSR_CYCLE' END
    ELSE CASE WHEN r1 < 0.50 THEN 'ABL_ADJUST' ELSE 'TPC_ADJUST' END END AS event_type,
  ptypes[didx] AS panel_type,
  CAST(100 + r2 * 9900 AS INT) AS panel_total_hours,
  CAST(100 + r3 * 4900 AS INT) AS panel_on_count,
  CASE WHEN r1 < 0.40 THEN 'offrs' WHEN r1 < 0.55 THEN 'jb' ELSE NULL END AS compensation_type,
  CASE WHEN r4 < 0.85 THEN 'auto_scheduled' WHEN r4 < 0.95 THEN 'cumulative_hours' ELSE 'user_manual' END AS trigger_reason,
  CASE WHEN r1 < 0.25 THEN 7 WHEN r1 < 0.40 THEN 60 ELSE CAST(5 + r5 * 10 AS INT) END AS duration_min,
  CASE WHEN r5 < 0.92 THEN 'completed' WHEN r5 < 0.97 THEN 'interrupted_power_loss' ELSE 'skipped_no_standby' END AS result,
  CAST(30 + r6 * 70 AS INT) AS backlight_level,
  ROUND(40 + r6 * 60, 1) AS abl_current_pct,
  CAST(500 + r7 * 3500 AS INT) AS peak_luminance_nits,
  ROUND(30 + r3 * 30, 1) AS panel_temperature_c,
  CAST(r4 * 500 AS INT) AS ambient_light_lux,
  element_at(array('standard','vivid','filmmaker','eco','game','cinema','sports'), CAST(FLOOR(r7*7) AS INT)+1) AS picture_mode,
  CASE WHEN r8 < 0.40 THEN 'auto' WHEN r8 < 0.70 THEN 'off' WHEN r8 < 0.85 THEN 'minimum' WHEN r8 < 0.95 THEN 'medium' ELSE 'maximum' END AS energy_saving_mode
FROM timed
"""

def sql_error_crash_events():
    return f"""
CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.error_crash_events AS
WITH device_pool AS (
  SELECT collect_list(device_id) AS dids, collect_list(webos_version) AS wvers
  FROM {CATALOG}.{SCHEMA}.devices
),
base AS (
  SELECT seq, dids, wvers,
    CAST(FLOOR(rand() * size(dids)) AS INT) AS didx,
    rand() AS r1, rand() AS r2, rand() AS r3, rand() AS r4, rand() AS r5, rand() AS r6, rand() AS r7, rand() AS r8,
    dateadd(SECOND, CAST(rand() * 31536000 AS INT), TIMESTAMP '2025-01-01') AS ts
  FROM (SELECT explode(sequence(1, 40000)) AS seq) x
  CROSS JOIN device_pool
),
typed AS (
  SELECT *,
    CASE WHEN r1 < 0.30 THEN 'APP_CRASH' WHEN r1 < 0.50 THEN 'APP_ANR' WHEN r1 < 0.65 THEN 'APP_OOM'
         WHEN r1 < 0.85 THEN 'MEDIA_PIPELINE_ERROR' WHEN r1 < 0.90 THEN 'GPU_HANG' WHEN r1 < 0.95 THEN 'SYSTEM_WATCHDOG' ELSE 'KERNEL_PANIC' END AS evt_type
  FROM base
)
SELECT
  concat('EVT_ERR_', date_format(ts, 'yyyyMMdd'), '_', lpad(CAST(seq AS STRING), 6, '0')) AS event_id,
  dids[didx] AS device_id,
  ts AS `timestamp`,
  evt_type AS event_type,
  CASE WHEN evt_type IN ('KERNEL_PANIC','SYSTEM_WATCHDOG') THEN 'CRITICAL'
       WHEN evt_type IN ('APP_CRASH','APP_ANR','APP_OOM','MEDIA_PIPELINE_ERROR','GPU_HANG') AND r2 < 0.8 THEN 'ERROR'
       ELSE 'WARNING' END AS severity,
  CASE WHEN evt_type LIKE 'APP%' THEN element_at(array('WebAppMgr','WebAppMgr','WebAppMgr','sam','audiod','settingsservice','media-pipeline'), CAST(FLOOR(r3*7) AS INT)+1)
       WHEN evt_type = 'MEDIA_PIPELINE_ERROR' THEN element_at(array('media-pipeline','media-pipeline','audiod'), CAST(FLOOR(r3*3) AS INT)+1)
       WHEN evt_type = 'GPU_HANG' THEN 'gpu-driver'
       ELSE element_at(array('kernel','watchdog','init'), CAST(FLOOR(r3*3) AS INT)+1) END AS process_name,
  CASE WHEN evt_type LIKE 'APP%' THEN
    element_at(array('netflix','com.webos.app.browser','youtube.leanback.v4','disneyplus','wavve','tving','amazon'), CAST(FLOOR(r4*7) AS INT)+1) ELSE NULL END AS app_id,
  CASE WHEN r5 < 0.40 THEN 'SIGSEGV' WHEN r5 < 0.70 THEN 'SIGABRT' WHEN r5 < 0.90 THEN 'SIGKILL' ELSE 'SIGBUS' END AS crash_signal,
  CASE WHEN evt_type = 'APP_OOM' THEN 137 WHEN r5 < 0.40 THEN 139 WHEN r5 < 0.70 THEN 134 ELSE CAST(128 + FLOOR(r6*10) AS INT) END AS exit_code,
  CASE WHEN evt_type = 'MEDIA_PIPELINE_ERROR' THEN
    element_at(array('MEDIA_ERR_DECODE','MEDIA_ERR_NETWORK','DRM_LICENSE_FAIL','MEDIA_ERR_UNSUPPORTED','MEDIA_ERR_ENCRYPTED'), CAST(FLOOR(r4*5) AS INT)+1)
       WHEN evt_type = 'GPU_HANG' THEN 'EGL_BAD_DISPLAY'
       ELSE NULL END AS error_code,
  CASE WHEN evt_type = 'APP_CRASH' THEN 'Segmentation fault in rendering thread'
       WHEN evt_type = 'APP_ANR' THEN 'Application not responding for 10s'
       WHEN evt_type = 'APP_OOM' THEN concat('Out of memory: killed process (used ', CAST(FLOOR(90+r7*10) AS STRING), '%)')
       WHEN evt_type = 'MEDIA_PIPELINE_ERROR' THEN 'Pipeline error during media decode'
       WHEN evt_type = 'GPU_HANG' THEN 'GPU hang detected, resetting'
       WHEN evt_type = 'KERNEL_PANIC' THEN 'Kernel panic - not syncing: Fatal exception'
       ELSE 'Watchdog timeout - system unresponsive' END AS error_detail,
  ROUND(20 + r6 * 60, 1) AS cpu_usage_at_event,
  CASE WHEN evt_type = 'APP_OOM' THEN ROUND(90 + r7 * 10, 1) ELSE ROUND(40 + r7 * 40, 1) END AS mem_used_pct_at_event,
  CAST(r8 * 604800 AS BIGINT) AS uptime_sec,
  wvers[didx] AS webos_version,
  CASE WHEN evt_type IN ('KERNEL_PANIC','SYSTEM_WATCHDOG') THEN r6 < 0.90
       WHEN r2 < 0.8 THEN r6 < 0.50
       ELSE r6 < 0.10 END AS coredump_available
FROM typed
"""


# ============================================================
# Main Execution
# ============================================================

TABLES = [
    ("system_boot_events",     sql_system_boot_events,     "50K rows"),
    ("resource_utilization",   sql_resource_utilization,    "200K rows"),
    ("firmware_updates",       sql_firmware_updates,        "15K rows"),
    ("viewing_logs",           sql_viewing_logs,            "500K rows"),
    ("app_launch_events",      sql_app_launch_events,       "300K rows"),
    ("input_switch_events",    sql_input_switch_events,     "80K rows"),
    ("wifi_connection_events", sql_wifi_connection_events,  "100K rows"),
    ("streaming_buffer_events",sql_streaming_buffer_events, "150K rows"),
    ("media_playback_events",  sql_media_playback_events,   "200K rows"),
    ("acr_events",             sql_acr_events,              "300K rows"),
    ("ad_impressions",         sql_ad_impressions,          "200K rows"),
    ("thinq_device_events",    sql_thinq_device_events,     "50K rows"),
    ("voice_command_events",   sql_voice_command_events,    "80K rows"),
    ("app_lifecycle_events",   sql_app_lifecycle_events,    "100K rows"),
    ("panel_diagnostics",      sql_panel_diagnostics,       "30K rows"),
    ("error_crash_events",     sql_error_crash_events,      "40K rows"),
]

def generate_table(table_name, sql_func, desc):
    print(f"🚀 {table_name} ({desc}) 생성 시작...")
    sql = sql_func()
    result = run_sql(sql, f"{table_name} ({desc})")
    print(result)
    return result

if __name__ == "__main__":
    print(f"=" * 60)
    print(f"LG webOS Smart TV 데이터 생성")
    print(f"Catalog: {CATALOG}")
    print(f"Schema: {SCHEMA}")
    print(f"Warehouse: {WAREHOUSE_ID}")
    print(f"테이블 수: {len(TABLES)}")
    print(f"=" * 60)

    # Run all table generations in parallel (max 8 concurrent)
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(generate_table, name, func, desc): name
            for name, func, desc in TABLES
        }
        for future in as_completed(futures):
            table_name = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(f"❌ {table_name}: Exception - {e}")
                print(f"❌ {table_name}: Exception - {e}")

    print(f"\n{'=' * 60}")
    print("📊 결과 요약")
    print(f"{'=' * 60}")
    for r in sorted(results):
        print(r)

    success = sum(1 for r in results if r.startswith("✅"))
    print(f"\n✅ 성공: {success}/{len(TABLES)}")
