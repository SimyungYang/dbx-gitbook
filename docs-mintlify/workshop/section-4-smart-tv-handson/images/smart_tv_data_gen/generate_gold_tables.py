#!/usr/bin/env python3
"""Generate 6 Gold tables for Smart TV PoC (workshop Section 4-03).

Gold tables aggregate Silver layer into business-ready KPIs:
1. daily_viewing_summary  — device × date viewing metrics
2. content_popularity     — program × date audience metrics
3. ad_campaign_kpi        — campaign × date ad performance
4. device_health_score    — device × date health scoring
5. streaming_qoe          — app × region × date QoE metrics
6. user_engagement_360    — device-level 30-day profile snapshot
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
# Gold SQL Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TABLES = {}

# ── Gold 1: daily_viewing_summary ──
TABLES["daily_viewing_summary"] = f"""
CREATE OR REPLACE TABLE {C}.gold.daily_viewing_summary
COMMENT 'Daily viewing summary per device — viewing time, content mix, top app/genre'
PARTITIONED BY (event_date)
AS
WITH viewing AS (
  SELECT
    v.*,
    d.region,
    d.product_line,
    d.panel_type
  FROM {C}.silver.viewing_sessions v
  INNER JOIN {C}.silver.devices_cleaned d ON v.device_id = d.device_id
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
GROUP BY v.device_id, v.event_date, v.region, v.product_line, v.panel_type, ta.top_app, tg.top_genre
"""

# ── Gold 2: content_popularity ──
TABLES["content_popularity"] = f"""
CREATE OR REPLACE TABLE {C}.gold.content_popularity
COMMENT 'Content popularity — audience reach, viewing time, regional distribution per program'
PARTITIONED BY (event_date)
AS
WITH total_devices AS (
  SELECT COUNT(DISTINCT device_id) AS total_active
  FROM {C}.silver.viewing_sessions
),
viewing_with_device AS (
  SELECT v.*, d.region, d.product_line
  FROM {C}.silver.viewing_sessions v
  INNER JOIN {C}.silver.devices_cleaned d ON v.device_id = d.device_id
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
    ROUND(AVG(LEAST(duration_sec * 100.0 / GREATEST(1800, 1), 100)), 1) AS completion_rate,
    MAP_FROM_ENTRIES(COLLECT_LIST(STRUCT(region, cnt)))
  FROM (
    SELECT program_title, genre, content_source, event_date, device_id,
           duration_min, duration_sec, region,
           COUNT(*) OVER (PARTITION BY program_title, genre, content_source, event_date, region) AS cnt
    FROM viewing_with_device
  ) sub
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
CROSS JOIN total_devices td
"""

# ── Gold 3: ad_campaign_kpi ──
TABLES["ad_campaign_kpi"] = f"""
CREATE OR REPLACE TABLE {C}.gold.ad_campaign_kpi
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
FROM {C}.silver.ad_funnel
GROUP BY campaign_id, advertiser_name, ad_format, placement, event_date
"""

# ── Gold 4: device_health_score ──
TABLES["device_health_score"] = f"""
CREATE OR REPLACE TABLE {C}.gold.device_health_score
COMMENT 'Device health score — CPU/mem/temp metrics, crash/OOM counts, 0-100 health scoring'
PARTITIONED BY (event_date)
AS
WITH metrics AS (
  SELECT
    device_id,
    event_date,
    ROUND(AVG(avg_cpu_pct), 1) AS avg_cpu_pct,
    ROUND(AVG(avg_mem_used_pct), 1) AS avg_mem_pct,
    ROUND(MAX(peak_thermal_0_c), 1) AS peak_soc_temp,
    ROUND(MAX(peak_thermal_1_c), 1) AS peak_panel_temp,
    SUM(CASE WHEN any_thermal_throttle THEN 1 ELSE 0 END) AS throttle_count
  FROM {C}.silver.system_metrics
  GROUP BY device_id, event_date
),
errors AS (
  SELECT
    device_id,
    event_date,
    SUM(CASE WHEN is_crash THEN 1 ELSE 0 END) AS crash_count,
    SUM(CASE WHEN is_oom THEN 1 ELSE 0 END) AS oom_count,
    SUM(CASE WHEN is_media_error THEN 1 ELSE 0 END) AS media_error_count
  FROM {C}.silver.error_events
  GROUP BY device_id, event_date
),
boots AS (
  SELECT
    device_id,
    event_date,
    SUM(CASE WHEN event_type IN ('POWER_ON', 'COLD_BOOT', 'WARM_BOOT', 'REBOOT') THEN 1 ELSE 0 END) AS reboot_count,
    SUM(CASE WHEN previous_shutdown IN ('DIRTY', 'ABNORMAL', 'CRASH', 'WATCHDOG') THEN 1 ELSE 0 END) AS dirty_shutdown_count
  FROM {C}.silver.boot_events
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
  -- Health score: start at 100, deduct
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
  -- Risk factors array
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
LEFT JOIN {C}.silver.devices_cleaned d ON c.device_id = d.device_id
"""

# ── Gold 5: streaming_qoe ──
TABLES["streaming_qoe"] = f"""
CREATE OR REPLACE TABLE {C}.gold.streaming_qoe
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
  -- QoE score: 100 - penalties
  ROUND(GREATEST(0, LEAST(100,
    100
    - (SUM(CASE WHEN sq.is_buffering THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1)) * 0.5
    - AVG(sq.stall_count) * 5
    - (SUM(CASE WHEN sq.is_outlier THEN 1 ELSE 0 END) * 100.0 / GREATEST(COUNT(*), 1)) * 0.3
    - (CASE WHEN PERCENTILE_APPROX(sq.latency_ms, 0.95) > 200 THEN 10 ELSE 0 END)
  )), 1) AS qoe_score
FROM {C}.silver.streaming_quality sq
INNER JOIN {C}.silver.devices_cleaned d ON sq.device_id = d.device_id
GROUP BY sq.app_id, d.region, sq.quality_tier, sq.event_date
"""

# ── Gold 6: user_engagement_360 ──
TABLES["user_engagement_360"] = f"""
CREATE OR REPLACE TABLE {C}.gold.user_engagement_360
COMMENT 'User engagement 360 — 30-day device profile with viewing, quality, ad, and segment data'
AS
WITH date_range AS (
  SELECT
    MAX(event_date) AS max_date,
    DATE_SUB(MAX(event_date), 30) AS min_date
  FROM {C}.silver.viewing_sessions
),
-- Viewing behavior
viewing AS (
  SELECT
    v.device_id,
    ROUND(SUM(v.duration_min) / GREATEST(DATEDIFF(dr.max_date, dr.min_date), 1), 1) AS avg_daily_viewing_min,
    ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%LIVE%' OR UPPER(v.content_source) LIKE '%TV%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS live_tv_pct,
    ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%OTT%' OR UPPER(v.content_source) LIKE '%STREAM%' OR UPPER(v.content_source) LIKE '%APP%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS ott_pct,
    ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%HDMI%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS hdmi_pct,
    ROUND(SUM(CASE WHEN v.is_primetime THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS primetime_ratio,
    ROUND(SUM(CASE WHEN DAYOFWEEK(v.session_start) IN (1, 7) THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS weekend_ratio,
    COUNT(DISTINCT v.channel_name) AS unique_channels,
    COUNT(*) AS total_sessions,
    ROUND(COUNT(*) * 1.0 / GREATEST(DATEDIFF(dr.max_date, dr.min_date), 1), 1) AS avg_sessions_per_day,
    ROUND(AVG(v.duration_min), 1) AS avg_session_duration_min
  FROM {C}.silver.viewing_sessions v
  CROSS JOIN date_range dr
  WHERE v.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY v.device_id, dr.max_date, dr.min_date
),
-- Top 3 apps
top_apps AS (
  SELECT device_id,
    COLLECT_LIST(app_id) AS top_3_apps
  FROM (
    SELECT device_id, app_id,
      ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY SUM(duration_min) DESC) AS rn
    FROM {C}.silver.viewing_sessions v
    CROSS JOIN date_range dr
    WHERE v.event_date BETWEEN dr.min_date AND dr.max_date AND app_id IS NOT NULL
    GROUP BY device_id, app_id
  ) WHERE rn <= 3
  GROUP BY device_id
),
-- Top 3 genres
top_genres AS (
  SELECT device_id,
    COLLECT_LIST(genre) AS top_3_genres
  FROM (
    SELECT device_id, genre,
      ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY SUM(duration_min) DESC) AS rn
    FROM {C}.silver.viewing_sessions v
    CROSS JOIN date_range dr
    WHERE v.event_date BETWEEN dr.min_date AND dr.max_date AND genre IS NOT NULL
    GROUP BY device_id, genre
  ) WHERE rn <= 3
  GROUP BY device_id
),
-- Voice usage
voice AS (
  SELECT
    vc.device_id,
    ROUND(COUNT(*) * 1.0 / GREATEST(DATEDIFF(dr.max_date, dr.min_date), 1), 2) AS voice_usage_rate
  FROM {C}.silver.voice_interactions vc
  CROSS JOIN date_range dr
  WHERE vc.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY vc.device_id, dr.max_date, dr.min_date
),
-- IoT devices
iot AS (
  SELECT
    io.device_id,
    COUNT(DISTINCT io.iot_device_id) AS iot_device_count
  FROM {C}.silver.iot_interactions io
  CROSS JOIN date_range dr
  WHERE io.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY io.device_id
),
-- HDMI devices
hdmi AS (
  SELECT
    n.device_id,
    COUNT(DISTINCT n.cec_device_name) AS hdmi_device_count
  FROM {C}.silver.network_events n
  CROSS JOIN date_range dr
  WHERE n.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY n.device_id
),
-- Streaming QoE
stream AS (
  SELECT
    sq.device_id,
    ROUND(AVG(100 - (CASE WHEN sq.is_buffering THEN 20 ELSE 0 END) - (sq.stall_count * 5) - (CASE WHEN sq.is_outlier THEN 10 ELSE 0 END)), 1) AS avg_streaming_qoe
  FROM {C}.silver.streaming_quality sq
  CROSS JOIN date_range dr
  WHERE sq.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY sq.device_id
),
-- Crash frequency
crashes AS (
  SELECT
    er.device_id,
    COUNT(*) AS crash_frequency
  FROM {C}.silver.error_events er
  CROSS JOIN date_range dr
  WHERE er.event_date BETWEEN dr.min_date AND dr.max_date AND er.is_crash
  GROUP BY er.device_id
),
-- Ad engagement
ads AS (
  SELECT
    af.device_id,
    ROUND((SUM(CASE WHEN af.is_clicked OR af.is_completed THEN 1 ELSE 0 END)) * 100.0 / GREATEST(COUNT(*), 1), 1) AS ad_engagement_rate,
    ROUND(AVG(af.completion_pct), 1) AS avg_ad_completion_pct
  FROM {C}.silver.ad_funnel af
  CROSS JOIN date_range dr
  WHERE af.event_date BETWEEN dr.min_date AND dr.max_date
  GROUP BY af.device_id
)
SELECT
  d.device_id,
  d.model_name,
  d.product_line,
  d.region,
  d.panel_type,
  d.webos_version,
  -- Viewing behavior
  COALESCE(vw.avg_daily_viewing_min, 0) AS avg_daily_viewing_min,
  CASE
    WHEN COALESCE(vw.live_tv_pct, 0) >= COALESCE(vw.ott_pct, 0) AND COALESCE(vw.live_tv_pct, 0) >= COALESCE(vw.hdmi_pct, 0) THEN 'live_tv'
    WHEN COALESCE(vw.ott_pct, 0) >= COALESCE(vw.hdmi_pct, 0) THEN 'ott'
    ELSE 'hdmi'
  END AS preferred_content_source,
  ta.top_3_apps,
  tg.top_3_genres,
  COALESCE(vw.primetime_ratio, 0) AS primetime_ratio,
  COALESCE(vw.weekend_ratio, 0) AS weekend_ratio,
  COALESCE(vw.unique_channels, 0) AS channel_diversity,
  -- Device usage
  COALESCE(vw.avg_sessions_per_day, 0) AS avg_sessions_per_day,
  COALESCE(vw.avg_session_duration_min, 0) AS avg_session_duration_min,
  COALESCE(vc.voice_usage_rate, 0) AS voice_usage_rate,
  COALESCE(io.iot_device_count, 0) AS iot_device_count,
  COALESCE(hd.hdmi_device_count, 0) AS hdmi_device_count,
  -- Quality
  COALESCE(st.avg_streaming_qoe, 100) AS avg_streaming_qoe,
  COALESCE(cr.crash_frequency, 0) AS crash_frequency,
  -- Ads
  COALESCE(ad.ad_engagement_rate, 0) AS ad_engagement_rate,
  COALESCE(ad.avg_ad_completion_pct, 0) AS avg_ad_completion_pct,
  -- User segment
  CASE
    WHEN COALESCE(vw.avg_daily_viewing_min, 0) > 240 AND COALESCE(vw.avg_sessions_per_day, 0) > 5 THEN 'power_user'
    WHEN COALESCE(vw.ott_pct, 0) > 70 THEN 'ott_native'
    WHEN COALESCE(vw.live_tv_pct, 0) > 60 THEN 'linear_loyalist'
    WHEN COALESCE(vw.hdmi_pct, 0) > 40 THEN 'gamer'
    WHEN COALESCE(io.iot_device_count, 0) >= 5 THEN 'smart_home_enthusiast'
    ELSE 'casual'
  END AS user_segment
FROM {C}.silver.devices_cleaned d
LEFT JOIN viewing vw ON d.device_id = vw.device_id
LEFT JOIN top_apps ta ON d.device_id = ta.device_id
LEFT JOIN top_genres tg ON d.device_id = tg.device_id
LEFT JOIN voice vc ON d.device_id = vc.device_id
LEFT JOIN iot io ON d.device_id = io.device_id
LEFT JOIN hdmi hd ON d.device_id = hd.device_id
LEFT JOIN stream st ON d.device_id = st.device_id
LEFT JOIN crashes cr ON d.device_id = cr.device_id
LEFT JOIN ads ad ON d.device_id = ad.device_id
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Execution
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # Step 1: Ensure gold schema exists
    print("=" * 60)
    print("Step 1: Creating gold schema...")
    r = execute_sql(
        f"CREATE SCHEMA IF NOT EXISTS {C}.gold COMMENT 'Gold layer — business-ready aggregations and KPIs'",
        label="gold schema",
    )
    print(r)
    print()

    # Step 2: Execute all 6 gold tables in parallel
    print("=" * 60)
    print(f"Step 2: Creating {len(TABLES)} gold tables in parallel...")
    print("=" * 60)

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
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
