# 03. SDP 파이프라인 — 데이터 품질과 Medallion Architecture

> **소요 시간**: ~1시간 | **핵심 기능**: Lakeflow Declarative Pipelines, Expectations, Auto Loader
>
> **핵심 메시지**: "Raw 데이터를 신뢰할 수 있는 분석용 데이터로 바꾸는 과정을 자연어 한 줄로 자동화한다"

## 개요

17개 Bronze 테이블의 Raw 로그 데이터에는 **결측치, 중복, 이상치, 타입 불일치** 등 현실 세계의 데이터 품질 문제가 존재합니다. 이 모듈에서는:

1. **수동 CTAS**로 Bronze→Silver→Gold 변환 로직을 이해한 뒤
2. **SDP(Spark Declarative Pipeline)**로 동일 로직을 선언적으로 자동화합니다

> Genie Code에서 전체 파이프라인을 한 번의 대화로 생성합니다.

---

## Part A: 데이터 품질 문제 이해하기

### Bronze 데이터에 의도적으로 포함된 품질 이슈

| 이슈 유형 | 테이블 | 구체적 문제 | 영향 |
|----------|--------|-----------|------|
| **결측치 (NULL)** | viewing_logs | `program_title`이 NULL (OTT 시청 시) | Genie Space 질의 시 빈 결과 |
| **결측치 (NULL)** | media_playback_events | `hdr_type`이 NULL (SDR 콘텐츠) | 대시보드 HDR 비율 왜곡 |
| **결측치 (NULL)** | streaming_buffer_events | `cdn_host`가 NULL (로컬 재생) | 네트워크 분석 누락 |
| **중복 레코드** | system_boot_events | 동일 device+timestamp 중복 (로그 재전송) | 부팅 횟수 과집계 |
| **중복 레코드** | acr_events | 30초 간격 fingerprint 중복 (네트워크 재시도) | ACR 매칭 통계 왜곡 |
| **이상치** | resource_utilization | `cpu_usage_pct > 100` (센서 오류) | 평균 CPU 사용률 왜곡 |
| **이상치** | viewing_logs | `duration_sec < 0` 또는 `> 86400` | 시청 시간 합계 오류 |
| **이상치** | streaming_buffer_events | `latency_ms > 10000` (네트워크 장애) | 평균 레이턴시 왜곡 |
| **타입 불일치** | wifi_connection_events | `signal_strength_dbm`이 양수 (부호 오류) | 신호 분석 반전 |
| **참조 무결성** | 모든 테이블 | 존재하지 않는 `device_id` (삭제된 디바이스) | 조인 시 데이터 손실 |
| **타임스탬프 이상** | app_launch_events | `session_end < session_start` | 세션 시간 음수 |
| **비즈니스 규칙 위반** | ad_impressions | `AD_COMPLETE` 이벤트 뒤에 `AD_START` | 퍼널 분석 오류 |

### Genie Code 프롬프트: 데이터 품질 진단

```
lge_smart_tv.bronze의 모든 테이블에 대해 데이터 품질 리포트를 만들어줘:

1. 각 테이블별 NULL 비율 상위 5개 컬럼
2. 중복 레코드 수 (event_id 기준)
3. 이상치 탐지:
   - resource_utilization: cpu_usage_pct > 100 또는 < 0
   - viewing_logs: duration_sec < 0 또는 > 86400
   - streaming_buffer_events: latency_ms > 10000
   - wifi_connection_events: signal_strength_dbm > 0
4. 참조 무결성: 각 테이블의 device_id가 devices에 없는 건수
5. 타임스탬프 역전: session_end < session_start인 건수

결과를 데이터 품질 스코어카드 형태로 보여줘.
```

---

## Part B: Silver Layer — 정제 & 표준화

### Silver 변환 원칙

| 원칙 | 적용 규칙 |
|------|----------|
| **중복 제거** | `event_id` 기준 DEDUP, 최신 타임스탬프 우선 |
| **NULL 처리** | 비즈니스 키는 DROP, 분석 컬럼은 DEFAULT 값 채움 |
| **이상치 필터링** | 물리적 불가능 값 DROP, 통계적 이상치는 FLAG 컬럼 추가 |
| **타입 정규화** | 타임스탬프 UTC 통일, 문자열 TRIM/LOWER |
| **참조 무결성** | devices 마스터에 없는 device_id는 quarantine 테이블로 분리 |
| **파티셔닝** | 날짜 기반 파티션 (`event_date`) 추가 |

### Silver 테이블 목록

| Silver 테이블 | 원본 Bronze | 주요 변환 |
|--------------|------------|----------|
| `silver.devices_cleaned` | devices | 중복 제거, region/country 표준화 |
| `silver.viewing_sessions` | viewing_logs | 중복 제거, NULL program_title → "Unknown", 이상 duration 필터, 세션 ID 부여 |
| `silver.app_sessions` | app_launch_events | BEGIN/END 쌍 매칭, 세션 duration 계산, 고아 이벤트 필터 |
| `silver.system_metrics` | resource_utilization | 이상치 클리핑(0~100%), 1분 → 5분 집계, 결측 구간 보간 |
| `silver.boot_events` | system_boot_events | 중복 제거, ON/OFF 쌍 매칭 |
| `silver.streaming_quality` | streaming_buffer_events | latency 이상치 필터, bitrate 변환 정규화 |
| `silver.media_sessions` | media_playback_events | START/STOP 쌍 매칭, NULL hdr_type → "SDR" |
| `silver.network_events` | wifi_connection_events | signal_strength 부호 보정, CONNECTED/DISCONNECTED 쌍 매칭 |
| `silver.ad_funnel` | ad_impressions | VAST 이벤트 시퀀스 정합성 검증, 순서 역전 필터 |
| `silver.acr_content` | acr_events | 중복 fingerprint 제거, match_confidence < 0.5 필터 |
| `silver.voice_interactions` | voice_command_events | transcript 정규화, 빈 transcript 필터 |
| `silver.iot_interactions` | thinq_device_events | command/ack 쌍 매칭, 응답시간 이상치 필터 |
| `silver.panel_health` | panel_diagnostics | OLED/LCD 분리, 시간순 정렬 |
| `silver.error_events` | error_crash_events | 중복 제거, severity 표준화 |
| `silver.firmware_history` | firmware_updates | OTA 시퀀스 완성도 검증, 실패 건 flag |

### Genie Code 프롬프트: Silver 테이블 생성 (핵심 5개)

> 전체 15개를 한번에 하면 너무 길어지므로, 핵심 테이블 5개를 먼저 만들고 나머지는 동일 패턴으로 확장합니다.

#### Silver 1: viewing_sessions (시청 세션)

```
lge_smart_tv.bronze.viewing_logs를 정제하여 lge_smart_tv.silver.viewing_sessions 테이블을 만들어줘.

변환 규칙:
1. event_id 기준 중복 제거 (같은 event_id면 최신 timestamp만 유지)
2. device_id가 bronze.devices에 없는 레코드 제거
3. duration_sec이 0 이하이거나 86400(24시간) 초과인 레코드 제거
4. session_end < session_start인 레코드 제거
5. NULL 처리:
   - program_title이 NULL → content_source가 'ott_app'이면 app_id 값으로 채움, 아니면 'Unknown'
   - channel_name이 NULL이고 content_source가 'live_tv' → 'Unknown Channel'
   - hdr_type이 NULL → 'SDR'
6. 추가 컬럼:
   - event_date: timestamp에서 추출한 DATE (파티션 키)
   - viewing_hour: 시청 시작 시간대 (0~23)
   - is_primetime: viewing_hour가 20~23이면 true
   - duration_min: duration_sec / 60.0 (소수점 1자리)
7. event_date로 파티셔닝
8. device_id, event_date로 Z-ORDER

CTAS SQL로 만들어줘.
```

#### Silver 2: system_metrics (시스템 메트릭)

```
lge_smart_tv.bronze.resource_utilization을 정제하여 lge_smart_tv.silver.system_metrics를 만들어줘.

변환 규칙:
1. 이상치 클리핑: cpu_usage_pct, gpu_usage_pct, mem_used_pct → CLIP(0, 100)
2. thermal_zone_0_c > 100 또는 < 0 → NULL로 변환
3. device_id가 devices에 없는 레코드 제거
4. 5분 단위로 집계 (1분 데이터 → 5분 평균):
   - AVG(cpu_usage_pct), AVG(gpu_usage_pct), AVG(mem_used_pct)
   - MAX(thermal_zone_0_c) as peak_soc_temp
   - MAX(thermal_zone_1_c) as peak_panel_temp  
   - SUM(network_rx_bytes) as total_rx_bytes_5min
   - SUM(network_tx_bytes) as total_tx_bytes_5min
   - BOOL_OR(thermal_throttle_active) as any_throttle
5. 추가 컬럼:
   - event_date: DATE 파티션 키
   - health_status: cpu > 80 AND mem > 85 → 'critical', cpu > 60 OR mem > 70 → 'warning', else 'normal'
6. event_date 파티셔닝, device_id Z-ORDER

CTAS SQL로 만들어줘.
```

#### Silver 3: ad_funnel (광고 퍼널)

```
lge_smart_tv.bronze.ad_impressions를 정제하여 lge_smart_tv.silver.ad_funnel을 만들어줘.

변환 규칙:
1. event_id 기준 중복 제거
2. VAST 이벤트 시퀀스 검증:
   - 같은 creative_id + device_id 내에서 이벤트 시간 순서가 올바른지 확인
   - AD_REQUEST → AD_IMPRESSION → AD_START → FIRST_QUARTILE → MIDPOINT → THIRD_QUARTILE → AD_COMPLETE
   - 순서가 역전된 이벤트는 is_sequence_valid = false로 마킹
3. NULL 처리:
   - completion_pct이 NULL → event_type에 따라 계산 (FIRST_QUARTILE=25, MIDPOINT=50, THIRD_QUARTILE=75, COMPLETE=100)
4. 추가 컬럼:
   - event_date: DATE 파티션 키
   - is_completed: event_type = 'AD_COMPLETE'
   - is_clicked: event_type = 'AD_CLICK'
   - is_skipped: event_type = 'AD_SKIP'
   - time_to_action_sec: AD_IMPRESSION ~ AD_CLICK 간 시간차
5. event_date 파티셔닝

CTAS SQL로 만들어줘.
```

#### Silver 4: streaming_quality (스트리밍 품질)

```
lge_smart_tv.bronze.streaming_buffer_events를 정제하여 lge_smart_tv.silver.streaming_quality를 만들어줘.

변환 규칙:
1. event_id 중복 제거
2. 이상치 필터: latency_ms > 10000 → is_outlier = true (제거하지 않고 플래그)
3. current_bitrate_kbps < 0 레코드 제거
4. NULL cdn_host → 'local_playback'
5. 추가 컬럼:
   - event_date: DATE 파티션 키
   - quality_tier: bitrate > 15000 → '4K', > 5000 → 'FHD', > 2000 → 'HD', else 'SD'
   - is_buffering: event_type IN ('BUFFER_UNDERRUN')
   - is_quality_degraded: event_type = 'BITRATE_SWITCH' AND current_bitrate_kbps < target_bitrate_kbps
   - buffering_ratio: BUFFER_UNDERRUN 이벤트 수 / 전체 이벤트 수 (디바이스+세션별)
6. event_date 파티셔닝, device_id Z-ORDER

CTAS SQL로 만들어줘.
```

#### Silver 5: error_events (에러 이벤트)

```
lge_smart_tv.bronze.error_crash_events를 정제하여 lge_smart_tv.silver.error_events를 만들어줘.

변환 규칙:
1. event_id 중복 제거
2. severity 표준화: 대소문자 통일, 유효값(CRITICAL/ERROR/WARNING) 외 → 'UNKNOWN'
3. devices 테이블과 조인하여 webos_version, product_line 추가
4. 추가 컬럼:
   - event_date: DATE 파티션 키
   - is_oom: event_type = 'APP_OOM'
   - is_crash: event_type IN ('APP_CRASH', 'KERNEL_PANIC')
   - is_media_error: event_type = 'MEDIA_PIPELINE_ERROR'
   - firmware_age_days: DATEDIFF(timestamp, devices.manufacturing_date)
   - error_category: process_name 기반 분류 → 'web_runtime', 'media', 'system', 'audio', 'app'
5. event_date 파티셔닝

CTAS SQL로 만들어줘.
```

---

## Part C: Gold Layer — 비즈니스 집계 테이블

### Gold 테이블 설계

Gold 테이블은 **대시보드, Genie Space, ML 모델, 에이전트**가 직접 소비하는 테이블입니다.

| Gold 테이블 | 소비자 | 그레인 | 설명 |
|------------|--------|--------|------|
| `gold.daily_viewing_summary` | 대시보드, Genie | 디바이스 × 일 | 일별 시청 통계 |
| `gold.content_popularity` | 대시보드, Genie | 프로그램 × 일 | 콘텐츠별 인기도 |
| `gold.hourly_engagement` | 대시보드 | 시간대 × 일 | 시간대별 활성 사용자 |
| `gold.ad_campaign_kpi` | 대시보드, Genie | 캠페인 × 일 | 광고 캠페인 KPI |
| `gold.device_health_score` | 대시보드, ML | 디바이스 × 일 | 디바이스 건강 점수 |
| `gold.streaming_qoe` | 대시보드, Genie | 앱 × 지역 × 일 | 스트리밍 QoE 지표 |
| `gold.voice_usage_analytics` | 대시보드 | 어시스턴트 × 의도 × 일 | 음성 사용 분석 |
| `gold.iot_ecosystem_stats` | 대시보드, Genie | 디바이스유형 × 일 | IoT 생태계 통계 |
| `gold.error_rate_by_firmware` | 대시보드, Genie | 펌웨어 × 일 | 펌웨어별 에러율 |
| `gold.user_engagement_360` | ML, 에이전트 | 디바이스 | 사용자 360도 프로파일 |

### Genie Code 프롬프트: Gold 테이블 생성

#### Gold 1: daily_viewing_summary

```
silver.viewing_sessions를 집계하여 gold.daily_viewing_summary를 만들어줘.

그레인: device_id × event_date (디바이스별 일별 1행)

컬럼:
- device_id, event_date
- total_viewing_min: 총 시청 시간(분)
- session_count: 시청 세션 수
- avg_session_min: 평균 세션 길이
- max_session_min: 최장 세션
- live_tv_min: Live TV 시청 시간
- ott_min: OTT 시청 시간
- hdmi_min: HDMI 입력 시청 시간
- top_app: 가장 많이 시청한 앱
- top_genre: 가장 많이 시청한 장르
- unique_channels: 시청한 고유 채널 수
- primetime_min: 프라임타임(20~23시) 시청 시간
- hdr_viewing_pct: HDR 콘텐츠 비율
- 4k_viewing_pct: 4K 콘텐츠 비율

devices 테이블과 조인하여 region, product_line, panel_type 추가.
event_date 파티셔닝, device_id Z-ORDER.
```

#### Gold 2: content_popularity

```
silver.viewing_sessions와 silver.acr_content를 결합하여 gold.content_popularity를 만들어줘.

그레인: program_title × genre × content_source × event_date

컬럼:
- program_title, genre, content_source, event_date
- total_viewers: 시청 디바이스 수 (unique device_id)
- total_viewing_min: 총 시청 시간
- avg_viewing_min: 평균 시청 시간
- completion_rate: 프로그램 완주율 (시청시간/프로그램길이 기반 추정)
- reach_pct: 전체 활성 디바이스 대비 시청 비율
- region_distribution: 지역별 시청자 분포 (JSON MAP)
- product_line_distribution: 제품라인별 시청자 분포 (JSON MAP)
- peak_concurrent: 동시 최대 시청자 수 (같은 시간대 시청 디바이스)
- trend_vs_7d_ago: 7일 전 대비 시청자 증감률

event_date 파티셔닝.
```

#### Gold 3: ad_campaign_kpi

```
silver.ad_funnel을 집계하여 gold.ad_campaign_kpi를 만들어줘.

그레인: campaign_id × advertiser_name × ad_format × placement × event_date

컬럼:
- campaign_id, advertiser_name, ad_format, placement, event_date
- impressions: 노출 수
- clicks: 클릭 수
- completions: 완료 수  
- skips: 스킵 수
- errors: 에러 수
- ctr: 클릭률 (clicks / impressions * 100)
- vcr: 완료율 (completions / impressions * 100)
- avg_completion_pct: 평균 시청 완료율
- total_revenue_usd: 총 수익 (bid_price 기반)
- ecpm: 유효 CPM (total_revenue / impressions * 1000)
- avg_time_to_click_sec: 평균 클릭까지 시간
- unique_devices: 노출된 고유 디바이스 수
- frequency: 디바이스당 평균 노출 빈도

event_date 파티셔닝.
```

#### Gold 4: device_health_score

```
silver.system_metrics, silver.error_events, silver.boot_events를 결합하여 gold.device_health_score를 만들어줘.

그레인: device_id × event_date

컬럼:
- device_id, event_date
- avg_cpu_pct: 일 평균 CPU
- avg_mem_pct: 일 평균 메모리
- peak_soc_temp: 최고 SoC 온도
- peak_panel_temp: 최고 패널 온도
- throttle_count: 쓰로틀링 발생 횟수
- crash_count: 크래시 횟수
- oom_count: OOM 횟수
- media_error_count: 미디어 에러 횟수
- reboot_count: 리부팅 횟수
- dirty_shutdown_count: 비정상 종료 횟수
- health_score: 종합 건강 점수 (0~100)
  - 100점에서 감점: crash(-10), oom(-8), throttle(-5), dirty_shutdown(-15), media_error(-3)
  - 보정: avg_cpu > 80 → -5, peak_temp > 75 → -5
- health_grade: A(90~100), B(70~89), C(50~69), D(30~49), F(0~29)
- risk_factors: 주요 위험 요인 배열 (예: ["high_crash_rate", "thermal_throttle", "oom_frequent"])

devices 조인으로 product_line, webos_version, firmware_version 추가.
event_date 파티셔닝, device_id Z-ORDER.
```

#### Gold 5: streaming_qoe (Quality of Experience)

```
silver.streaming_quality와 silver.viewing_sessions를 결합하여 gold.streaming_qoe를 만들어줘.

그레인: app_id × region × quality_tier × event_date

컬럼:
- app_id, region, quality_tier, event_date
- total_streams: 총 스트림 수
- unique_devices: 고유 디바이스 수
- avg_bitrate_kbps: 평균 비트레이트
- avg_latency_ms: 평균 레이턴시
- p95_latency_ms: P95 레이턴시
- buffering_rate: 버퍼링 발생률 (버퍼링 세션 / 전체 세션)
- avg_stall_count: 평균 정지 횟수
- avg_stall_duration_sec: 평균 정지 시간
- bitrate_downgrade_rate: 비트레이트 하향 비율
- error_rate: 스트림 에러율
- qoe_score: QoE 점수 (0~100)
  - 100점에서 감점: buffering_rate*50, avg_stall_count*5, error_rate*30, p95_latency>200ms → -10

event_date 파티셔닝.
```

#### Gold 6: user_engagement_360 (사용자 프로파일)

```
모든 silver 테이블을 결합하여 gold.user_engagement_360을 만들어줘.

그레인: device_id (디바이스당 1행 — 최근 30일 기반 스냅샷)

컬럼:
- device_id
- -- 시청 행동 --
- avg_daily_viewing_min: 일 평균 시청 시간
- preferred_content_source: 주 시청 소스 (live_tv/ott/hdmi)
- top_3_apps: 상위 3개 앱 (JSON ARRAY)
- top_3_genres: 상위 3개 장르 (JSON ARRAY)
- primetime_ratio: 프라임타임 시청 비율
- weekend_ratio: 주말 시청 비율
- channel_diversity_index: 채널 다양성 지수 (Shannon entropy)
- -- 디바이스 사용 --
- avg_sessions_per_day: 일 평균 세션 수
- avg_session_duration_min: 평균 세션 길이
- voice_usage_rate: 음성 명령 사용 빈도 (일 평균)
- iot_device_count: 연결된 IoT 디바이스 수
- hdmi_device_count: 연결된 HDMI 디바이스 수
- -- 품질 지표 --
- avg_streaming_qoe: 평균 스트리밍 QoE
- crash_frequency: 30일간 크래시 빈도
- health_grade: 최근 건강 등급
- -- 광고 --
- ad_engagement_rate: 광고 참여율 (click + complete / impression)
- avg_ad_completion_pct: 평균 광고 완료율
- -- 세그먼트 --
- user_segment: 사용자 세그먼트 분류
  - 'power_user': daily_viewing > 240min AND sessions > 5
  - 'ott_native': ott_ratio > 70%
  - 'linear_loyalist': live_tv_ratio > 60%  
  - 'gamer': hdmi_ratio > 40% AND top device_type = 'game_console'
  - 'smart_home_enthusiast': iot_device_count >= 5
  - 'casual': 나머지

devices 조인으로 마스터 정보 추가.
```

---

## Part D: SDP 파이프라인으로 자동화

### 수동 CTAS → SDP 전환의 의미

| 항목 | 수동 CTAS | SDP (Lakeflow) |
|------|----------|----------------|
| 실행 방식 | 노트북에서 수동 Run | 파이프라인 자동 스케줄링 |
| 증분 처리 | 전체 재처리 (Full Refresh) | 자동 증분 (Incremental) |
| 데이터 품질 | 코드에서 직접 필터 | `@dlt.expect` 선언적 규칙 |
| 의존성 관리 | 실행 순서 수동 관리 | DAG 자동 해석 |
| 에러 복구 | 수동 재실행 | 자동 재시도 + 격리 |

### Genie Code 프롬프트: SDP 파이프라인 생성

```
위에서 만든 Bronze → Silver → Gold 변환 로직을 SDP(Spark Declarative Pipeline)로 전환해줘.

파이프라인 이름: lge_smart_tv_pipeline
타겟 카탈로그: lge_smart_tv
타겟 스키마: silver (Silver 테이블), gold (Gold 테이블)

요구사항:
1. Bronze → Silver 변환을 Streaming Table로 구성 (증분 처리)
2. Silver → Gold 변환을 Materialized View로 구성 (자동 리프레시)
3. 각 테이블에 Expectations 추가:
   - viewing_sessions: expect("valid_duration", "duration_sec > 0 AND duration_sec <= 86400")
   - system_metrics: expect("valid_cpu", "cpu_usage_pct >= 0 AND cpu_usage_pct <= 100")
   - ad_funnel: expect("valid_sequence", "is_sequence_valid = true")
   - streaming_quality: expect("valid_latency", "latency_ms > 0")
   - error_events: expect("valid_severity", "severity IN ('CRITICAL','ERROR','WARNING')")
4. Quarantine 테이블: 위반 레코드는 별도 quarantine 스키마로 분리
5. 데이터 품질 위반 시 처리 방식:
   - Silver: expect_or_drop (위반 시 제거)
   - Gold: expect_or_fail (위반 시 파이프라인 중단)

노트북 코드를 생성해줘. Python + SQL 혼합 가능.
```

### Genie Code 프롬프트: SDP 파이프라인 실행

```
방금 만든 SDP 파이프라인 노트북을 실행할 수 있도록:
1. lge_smart_tv_pipeline 이름으로 파이프라인 생성
2. 서버리스 컴퓨트 사용
3. Continuous 모드 대신 Triggered 모드로 설정
4. 파이프라인 실행하고 결과 확인

실행 후 각 테이블의 row count와 Expectations 통과율을 보여줘.
```

### 기대 결과: Expectations 대시보드

파이프라인 실행 후 SDP UI에서 확인할 수 있는 데이터 품질 메트릭:

| 테이블 | Expectation | 통과율 | 위반 건수 |
|--------|------------|--------|----------|
| viewing_sessions | valid_duration | 99.2% | ~4,000 |
| system_metrics | valid_cpu | 98.0% | ~4,000 |
| ad_funnel | valid_sequence | 97.5% | ~5,000 |
| streaming_quality | valid_latency | 99.5% | ~750 |
| error_events | valid_severity | 99.8% | ~80 |

---

## Part E: 파이프라인 Job 스케줄링

### Genie Code 프롬프트 (AI Dev Kit MCP 활용)

```
lge_smart_tv_pipeline을 매일 자동 실행하는 Job을 만들어줘.

설정:
- Job 이름: lge_smart_tv_daily_refresh
- 스케줄: 매일 오전 6시 KST (cron: 0 21 * * * UTC)
- 재시도: 최대 2회, 간격 10분
- 알림: 실패 시 이메일 알림
- 클러스터: 서버리스
- 타임아웃: 2시간
```

---

## 핵심 포인트 정리

| 배운 것 | Databricks 기능 | 비즈니스 가치 |
|---------|----------------|-------------|
| 데이터 품질 진단 | SQL, DataFrame API | Raw 데이터의 신뢰성 파악 |
| 결측치/이상치 처리 | CTAS, Window 함수 | 분석 결과의 정확도 향상 |
| 선언적 파이프라인 | SDP (Lakeflow) | 운영 부담 최소화, 자동 증분 처리 |
| 데이터 품질 규칙 | Expectations | 품질 위반 자동 감지 및 격리 |
| Gold Layer 설계 | Materialized View | 대시보드/Genie/ML이 바로 소비 가능한 데이터 |
| Job 스케줄링 | Databricks Jobs | 일일 자동 리프레시 |

---

## 다음 단계

- **[04. 대시보드 & Genie Space](04-dashboard-genie.md)** — Gold 테이블로 대시보드와 Genie Space 구축, 정확도 고도화
