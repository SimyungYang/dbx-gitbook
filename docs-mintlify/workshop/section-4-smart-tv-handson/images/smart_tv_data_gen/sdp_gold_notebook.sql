-- Databricks notebook source

-- MAGIC %md
-- MAGIC # LGE Smart TV SDP Pipeline — Gold Layer
-- MAGIC
-- MAGIC Silver 테이블을 집계하여 비즈니스 KPI 생성. 6개 Materialized View.
-- MAGIC Expectation 위반 시 `ON VIOLATION FAIL UPDATE` → 파이프라인 중단.
-- MAGIC
-- MAGIC **파이프라인:** `lge_smart_tv_pipeline_claude_gold`
-- MAGIC **카탈로그:** `byungjun_lee_smarttv_training_catalog`
-- MAGIC **타겟 스키마:** `gold`

-- COMMAND ----------

-- ============================================================
-- Gold 1: daily_viewing_summary
-- 그레인: device_id × event_date
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW daily_viewing_summary (
  CONSTRAINT valid_viewing EXPECT (total_viewing_min >= 0) ON VIOLATION FAIL UPDATE
)
COMMENT 'Daily viewing summary per device — viewing time, content mix, top app/genre'
AS
WITH viewing AS (
  SELECT v.*, d.region, d.product_line, d.panel_type
  FROM byungjun_lee_smarttv_training_catalog.silver.viewing_sessions v
  INNER JOIN byungjun_lee_smarttv_training_catalog.silver.devices_cleaned d ON v.device_id = d.device_id
),
top_app AS (
  SELECT device_id, event_date, app_id AS top_app,
    ROW_NUMBER() OVER (PARTITION BY device_id, event_date ORDER BY SUM(duration_min) DESC) AS rn
  FROM viewing WHERE app_id IS NOT NULL
  GROUP BY device_id, event_date, app_id
),
top_genre AS (
  SELECT device_id, event_date, genre AS top_genre,
    ROW_NUMBER() OVER (PARTITION BY device_id, event_date ORDER BY SUM(duration_min) DESC) AS rn
  FROM viewing WHERE genre IS NOT NULL
  GROUP BY device_id, event_date, genre
)
SELECT
  v.device_id, v.event_date, v.region, v.product_line, v.panel_type,
  ROUND(SUM(v.duration_min), 1) AS total_viewing_min,
  COUNT(*) AS session_count,
  ROUND(AVG(v.duration_min), 1) AS avg_session_min,
  ROUND(MAX(v.duration_min), 1) AS max_session_min,
  ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%LIVE%' OR UPPER(v.content_source) LIKE '%TV%' OR UPPER(v.broadcast_type) LIKE '%LIVE%' THEN v.duration_min ELSE 0 END), 1) AS live_tv_min,
  ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%OTT%' OR UPPER(v.content_source) LIKE '%STREAM%' OR UPPER(v.content_source) LIKE '%APP%' THEN v.duration_min ELSE 0 END), 1) AS ott_min,
  ROUND(SUM(CASE WHEN UPPER(v.content_source) LIKE '%HDMI%' OR UPPER(v.content_source) LIKE '%EXTERNAL%' THEN v.duration_min ELSE 0 END), 1) AS hdmi_min,
  ta.top_app, tg.top_genre,
  COUNT(DISTINCT v.channel_name) AS unique_channels,
  ROUND(SUM(CASE WHEN v.is_primetime THEN v.duration_min ELSE 0 END), 1) AS primetime_min,
  ROUND(SUM(CASE WHEN v.hdr_type != 'SDR' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS hdr_viewing_pct,
  ROUND(SUM(CASE WHEN v.resolution LIKE '%2160%' OR v.resolution LIKE '%3840%' OR v.resolution LIKE '%4K%' THEN v.duration_min ELSE 0 END) * 100.0 / GREATEST(SUM(v.duration_min), 1), 1) AS `4k_viewing_pct`
FROM viewing v
LEFT JOIN top_app ta ON v.device_id = ta.device_id AND v.event_date = ta.event_date AND ta.rn = 1
LEFT JOIN top_genre tg ON v.device_id = tg.device_id AND v.event_date = tg.event_date AND tg.rn = 1
GROUP BY v.device_id, v.event_date, v.region, v.product_line, v.panel_type, ta.top_app, tg.top_genre;

-- COMMAND ----------

-- ============================================================
-- Gold 2: content_popularity
-- 그레인: program_title × genre × content_source × event_date
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW content_popularity (
  CONSTRAINT valid_viewers EXPECT (total_viewers > 0) ON VIOLATION FAIL UPDATE
)
COMMENT 'Content popularity — audience reach, viewing time, regional distribution per program'
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
    program_title, genre, content_source, event_date,
    COUNT(DISTINCT device_id) AS total_viewers,
    ROUND(SUM(duration_min), 1) AS total_viewing_min,
    ROUND(AVG(duration_min), 1) AS avg_viewing_min,
    ROUND(AVG(LEAST(duration_sec * 100.0 / GREATEST(1800, 1), 100)), 1) AS completion_rate
  FROM viewing_with_device
  GROUP BY program_title, genre, content_source, event_date
)
SELECT
  b.program_title, b.genre, b.content_source, b.event_date,
  b.total_viewers, b.total_viewing_min, b.avg_viewing_min, b.completion_rate,
  ROUND(b.total_viewers * 100.0 / GREATEST(td.total_active, 1), 2) AS reach_pct
FROM base b CROSS JOIN total_devices td;

-- COMMAND ----------

-- ============================================================
-- Gold 3: ad_campaign_kpi
-- 그레인: campaign_id × advertiser_name × ad_format × placement × event_date
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW ad_campaign_kpi (
  CONSTRAINT valid_impressions EXPECT (impressions > 0) ON VIOLATION FAIL UPDATE
)
COMMENT 'Ad campaign KPIs — impressions, CTR, VCR, revenue, frequency per campaign'
AS
SELECT
  campaign_id, advertiser_name, ad_format, placement, event_date,
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

-- COMMAND ----------

-- ============================================================
-- Gold 4: device_health_score
-- 그레인: device_id × event_date
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW device_health_score (
  CONSTRAINT valid_health_score EXPECT (health_score >= 0 AND health_score <= 100) ON VIOLATION FAIL UPDATE
)
COMMENT 'Device health score — CPU/mem/temp metrics, crash/OOM counts, 0-100 health scoring'
AS
WITH metrics AS (
  SELECT device_id, event_date,
    ROUND(AVG(avg_cpu_pct), 1) AS avg_cpu_pct,
    ROUND(AVG(avg_mem_used_pct), 1) AS avg_mem_pct,
    ROUND(MAX(peak_thermal_0_c), 1) AS peak_soc_temp,
    ROUND(MAX(peak_thermal_1_c), 1) AS peak_panel_temp,
    SUM(CASE WHEN any_thermal_throttle THEN 1 ELSE 0 END) AS throttle_count
  FROM byungjun_lee_smarttv_training_catalog.silver.system_metrics
  GROUP BY device_id, event_date
),
errors AS (
  SELECT device_id, event_date,
    SUM(CASE WHEN is_crash THEN 1 ELSE 0 END) AS crash_count,
    SUM(CASE WHEN is_oom THEN 1 ELSE 0 END) AS oom_count,
    SUM(CASE WHEN is_media_error THEN 1 ELSE 0 END) AS media_error_count
  FROM byungjun_lee_smarttv_training_catalog.silver.error_events
  GROUP BY device_id, event_date
),
boots AS (
  SELECT device_id, event_date,
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
    m.peak_soc_temp, m.peak_panel_temp,
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
  c.device_id, c.event_date, d.product_line, d.webos_version,
  c.avg_cpu_pct, c.avg_mem_pct, c.peak_soc_temp, c.peak_panel_temp,
  c.throttle_count, c.crash_count, c.oom_count, c.media_error_count,
  c.reboot_count, c.dirty_shutdown_count,
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

-- COMMAND ----------

-- ============================================================
-- Gold 5: streaming_qoe
-- 그레인: app_id × region × quality_tier × event_date
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW streaming_qoe (
  CONSTRAINT valid_qoe_score EXPECT (qoe_score >= 0 AND qoe_score <= 100) ON VIOLATION FAIL UPDATE
)
COMMENT 'Streaming QoE — bitrate, latency, buffering, stall metrics and QoE score per app/region'
AS
SELECT
  sq.app_id, d.region, sq.quality_tier, sq.event_date,
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

-- COMMAND ----------

-- ============================================================
-- Gold 6: user_engagement_360
-- 그레인: device_id (30일 스냅샷)
-- 참고: hdmi_agg는 bronze.input_switch_events 직접 참조
-- ============================================================
CREATE OR REFRESH MATERIALIZED VIEW user_engagement_360 (
  CONSTRAINT valid_viewing EXPECT (avg_daily_viewing_min >= 0) ON VIOLATION FAIL UPDATE
)
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
