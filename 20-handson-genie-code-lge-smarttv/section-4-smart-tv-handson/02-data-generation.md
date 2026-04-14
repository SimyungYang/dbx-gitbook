# 02. webOS Smart TV 가상 데이터 생성

> **소요 시간**: ~15분 | **사전 조건**: [01. 환경 설정](01-setup.md) 완료 | **컴퓨트**: Serverless 권장

### 이 모듈에서 사용하는 Databricks 기능

| 기능 | 설명 | 공식 문서 |
|------|------|----------|
| **PySpark** | Databricks의 분산 데이터 처리 엔진. 대규모 데이터를 클러스터에서 병렬로 생성/처리합니다. | [docs](https://docs.databricks.com/en/pyspark/index.html) |
| **Faker** | 테스트용 가짜 데이터를 생성하는 Python 라이브러리. 이름, 날짜, IP 주소 등 현실적인 값을 만듭니다. | [pypi](https://pypi.org/project/Faker/) |
| **Delta Lake** | Databricks의 기본 테이블 형식. 트랜잭션 보장, 스키마 진화, 시간 여행(Time Travel) 기능을 제공합니다. | [docs](https://docs.databricks.com/en/delta/index.html) |
| **Unity Catalog Volumes** | 파일(CSV, Parquet, PDF 등)을 저장하는 Unity Catalog 내 스토리지 영역입니다. | [docs](https://docs.databricks.com/en/volumes/index.html) |

## 개요

LG webOS Smart TV에서 실제로 발생하는 텔레메트리 로그 체계를 기반으로 **10개 카테고리, 17개 테이블, 약 250만 건**의 가상 데이터를 생성합니다.

webOS의 실제 로깅 인프라(`pmlogd`, Luna Service API, `rdxd`)의 구조를 반영하여, 현실적인 필드명과 값 분포를 가진 데이터를 만듭니다.

### Genie Code로 생성하기

이 모듈의 모든 데이터는 **Genie Code**를 통해 자연어 프롬프트만으로 생성합니다. 각 테이블별로 제공되는 프롬프트를 Genie Code에 입력하면, PySpark + Faker 기반의 데이터 생성 코드가 자동으로 만들어집니다.

> **Tip**: Genie Code에서 `Cmd+I` → Agent Mode로 전환 후 프롬프트를 입력하세요.

---

## 데이터 아키텍처 전체 구조

```
catalog: lge_smart_tv
├── bronze (Raw 텔레메트리 로그 — 17개 테이블)
│   ├── [Master] devices                     10,000건
│   ├── [System] system_boot_events          50,000건
│   ├── [System] resource_utilization        200,000건
│   ├── [System] firmware_updates            15,000건
│   ├── [Viewing] viewing_logs               500,000건
│   ├── [Viewing] app_launch_events          300,000건
│   ├── [Viewing] input_switch_events        80,000건
│   ├── [Network] wifi_connection_events     100,000건
│   ├── [Network] streaming_buffer_events    150,000건
│   ├── [Media] media_playback_events        200,000건
│   ├── [Ad] acr_events                      300,000건
│   ├── [Ad] ad_impressions                  200,000건
│   ├── [IoT] thinq_device_events            50,000건
│   ├── [Voice] voice_command_events         80,000건
│   ├── [App] app_lifecycle_events           100,000건
│   ├── [Display] panel_diagnostics          30,000건
│   └── [Error] error_crash_events           40,000건
│                                       ─────────────
│                                       합계: ~2,405,000건
```

---

## 진행 방법

> **17개 테이블을 한 번에 다 만들 필요는 없습니다.** 테이블 1(devices)만 먼저 생성하고, 나머지는 카테고리별로 필요할 때 생성하세요. 각 테이블의 프롬프트를 Genie Code에 **그대로 복사 붙여넣기**하면 PySpark + Faker 코드가 자동 생성됩니다.

### 사전 준비: 환경 설정

> [01. 환경 설정](01-setup.md)에서 카탈로그/스키마를 이미 생성했다면 이 단계는 건너뛰세요.

```
Unity Catalog에 다음 환경을 설정해줘:
- 카탈로그: lge_smart_tv 
- 스키마: bronze, silver, gold, quarantine
- 볼륨: bronze 스키마에 raw_files 볼륨 생성
```

---

## 카테고리 안내

아래 17개 테이블은 카테고리별로 묶어서 설명합니다. 각 카테고리를 클릭하면 상세 스키마와 프롬프트가 펼쳐집니다.

| 카테고리 | 테이블 수 | 총 건수 | 포함 테이블 |
|---------|----------|---------|-----------|
| **Master** | 1개 | 10,000 | devices |
| **System** | 3개 | 265,000 | boot_events, resource_utilization, firmware_updates |
| **Viewing** | 3개 | 880,000 | viewing_logs, app_launch_events, input_switch_events |
| **Network** | 2개 | 250,000 | wifi_connection_events, streaming_buffer_events |
| **Media & Ad** | 3개 | 700,000 | media_playback_events, acr_events, ad_impressions |
| **IoT & Voice & App** | 3개 | 230,000 | thinq_device_events, voice_command_events, app_lifecycle_events |
| **Display & Error** | 2개 | 70,000 | panel_diagnostics, error_crash_events |

> **가장 먼저 테이블 1(devices)을 생성하세요.** 나머지 모든 테이블이 devices의 `device_id`를 참조합니다.

---

## 테이블 1: devices (디바이스 마스터)

> 모든 로그의 기준이 되는 TV 디바이스 마스터 테이블. 가장 먼저 생성해야 합니다.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `device_id` | STRING | 고유 디바이스 ID | `LGE_TV_KR_000001` |
| `model_name` | STRING | TV 모델명 | `OLED65C4PSA`, `86QNED90TPA` |
| `product_line` | STRING | 제품 라인 | `OLED_C`, `OLED_G`, `QNED`, `NANO`, `UHD` |
| `panel_type` | STRING | 패널 타입 | `WOLED`, `OLED_EX`, `MLA_OLED_EX`, `NanoCell`, `IPS_LCD` |
| `screen_size_inch` | INT | 화면 크기 | `55`, `65`, `77`, `83`, `97` |
| `manufacturing_date` | DATE | 제조일 | `2024-03-15` |
| `manufacturing_country` | STRING | 제조국 | `KR`, `PL`, `MX`, `CN`, `ID` |
| `webos_version` | STRING | webOS 버전 | `24.10.40`, `23.08.25`, `6.0`, `5.0` |
| `firmware_version` | STRING | 펌웨어 버전 | `03.33.85` |
| `soc_chipset` | STRING | SoC 칩셋 | `Alpha9_Gen7`, `Alpha8`, `Alpha5_Gen7` |
| `ram_mb` | INT | RAM 용량 | `2048`, `3072`, `4096` |
| `storage_mb` | INT | 저장 용량 | `8192`, `16384`, `32768` |
| `region` | STRING | 배포 지역 | `KR`, `US`, `EU`, `JP`, `SEA`, `LATAM` |
| `country` | STRING | 상세 국가 | `KR`, `US`, `DE`, `JP`, `BR` |
| `timezone` | STRING | 타임존 | `Asia/Seoul`, `America/New_York` |
| `registration_date` | DATE | 등록일 | `2024-04-01` |
| `thinq_connected` | BOOLEAN | ThinQ 연결 여부 | `true`, `false` |
| `voice_assistant` | STRING | 음성 비서 | `lg_thinq_ai`, `alexa`, `google_assistant`, `none` |
| `network_type` | STRING | 네트워크 연결 | `wifi_5ghz`, `wifi_2.4ghz`, `ethernet`, `wifi_6` |
| `hdmi_port_count` | INT | HDMI 포트 수 | `3`, `4` |
| `has_earc` | BOOLEAN | eARC 지원 여부 | `true`, `false` |
| `energy_rating` | STRING | 에너지 등급 | `1등급`, `2등급`, `3등급` |

### Genie Code 프롬프트

```
10,000개의 LG webOS Smart TV 디바이스 마스터 데이터를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.devices
- device_id: "LGE_TV_{region}_{6자리 시퀀스}" 형식 (예: LGE_TV_KR_000001)
- model_name: LG TV 실제 모델 naming convention 따를 것
  - OLED: OLED{size}{시리즈}{년도} (예: OLED65C4PSA, OLED77G4PUA)
  - QNED: {size}QNED{시리즈}{년도} (예: 86QNED90TPA, 75QNED85TPA)  
  - NANO: {size}NANO{시리즈}{년도} (예: 65NANO80TPA)
  - UHD: {size}UQ{시리즈}{년도} (예: 55UQ8000PJC)
- product_line 분포: OLED_C(25%), OLED_G(10%), OLED_B(15%), QNED(20%), NANO(15%), UHD(15%)
- panel_type은 product_line에 따라 결정:
  - OLED_C/G → WOLED, OLED_EX, MLA_OLED_EX 중 랜덤
  - QNED/NANO → NanoCell
  - UHD → IPS_LCD
- screen_size_inch: OLED(55,65,77,83,97), QNED(65,75,86), NANO(50,55,65), UHD(43,50,55,65)
- webos_version: "24.10.40"(30%), "23.08.25"(25%), "6.0"(20%), "5.0"(15%), "4.5"(10%)
- region 분포: KR(30%), US(25%), EU(20%), JP(10%), SEA(10%), LATAM(5%)
- manufacturing_date: 2022-01 ~ 2025-12 범위
- soc_chipset은 product_line에 따라: OLED_G→Alpha9_Gen7, OLED_C→Alpha9_Gen7, OLED_B→Alpha8, QNED→Alpha8, NANO/UHD→Alpha5_Gen7
- thinq_connected: 70% true
- voice_assistant 분포: lg_thinq_ai(40%), alexa(25%), google_assistant(20%), none(15%)
- network_type: wifi_5ghz(45%), wifi_2.4ghz(25%), ethernet(15%), wifi_6(15%)

Delta 테이블로 저장하고 COMMENT를 달아줘.
```

### 생성 확인

```
lge_smart_tv.bronze.devices 테이블이 잘 생성됐는지 확인해줘.
총 row 수, region별 분포, product_line별 분포를 보여줘.
```

> ✅ row 수가 10,000건이고, region 분포가 KR(30%) US(25%) EU(20%)에 가까우면 정상입니다.

---

## 카테고리: System (시스템 로그)

<details>
<summary><strong>시스템 로그 3개 테이블 펼치기</strong> — boot_events(50K), resource_utilization(200K), firmware_updates(15K)</summary>

### 테이블 2: system_boot_events (시스템 부팅/전원 이벤트)

> webOS `pmlogd` 로그 형식을 기반으로 한 부팅/전원 상태 전환 이벤트.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_BOOT_20250101_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | ISO 8601 UTC | `2025-01-15T09:24:09.612Z` |
| `monotonic_ms` | BIGINT | 부팅 이후 경과 ms | `10151514` |
| `event_type` | STRING | 이벤트 유형 | `COLD_BOOT`, `WARM_BOOT`, `POWER_ON`, `POWER_OFF`, `STANDBY_ENTER`, `STANDBY_EXIT` |
| `boot_reason` | STRING | 부팅 사유 | `user_remote`, `timer_wakeup`, `cec_wakeup`, `ota_update`, `watchdog_reset` |
| `boot_time_ms` | INT | 부팅 소요 시간 | `8500` ~ `25000` |
| `previous_shutdown` | STRING | 이전 종료 방식 | `clean`, `dirty`, `watchdog` |
| `webos_version` | STRING | OS 버전 | `24.10.40` |
| `firmware_version` | STRING | 펌웨어 버전 | `03.33.85` |
| `kernel_version` | STRING | 커널 버전 | `4.14.150-lge-g12345` |
| `uptime_before_event_sec` | BIGINT | 이벤트 전 가동 시간 | `86400` |

### Genie Code 프롬프트

```
50,000건의 webOS TV 부팅/전원 이벤트 로그를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.system_boot_events
- device_id는 lge_smart_tv.bronze.devices에서 랜덤 샘플링
- timestamp: 2025-01-01 ~ 2025-12-31 범위, 디바이스별 timezone 반영
- event_type 분포: POWER_ON(30%), POWER_OFF(25%), STANDBY_ENTER(20%), STANDBY_EXIT(15%), COLD_BOOT(5%), WARM_BOOT(5%)
- boot_reason: POWER_ON일 때 → user_remote(60%), timer_wakeup(15%), cec_wakeup(15%), ota_update(5%), watchdog_reset(5%)
- boot_time_ms: COLD_BOOT(15000~25000), WARM_BOOT(5000~12000), POWER_ON(8000~15000)
- previous_shutdown: clean(85%), dirty(10%), watchdog(5%)
- POWER_ON/POWER_OFF는 쌍으로 발생하도록 시간 순서 보장
- 일반적으로 하루 1~3회 ON/OFF 사이클
- webos_version, firmware_version은 devices 테이블과 조인하여 사용
- 이벤트 ID: "EVT_BOOT_{YYYYMMDD}_{6자리 시퀀스}" 형식

Delta 테이블로 저장해줘.
```

---

### 테이블 3: resource_utilization (시스템 리소스 사용량)

> 1분 간격으로 수집되는 CPU/메모리/GPU/온도 등 시스템 리소스 메트릭.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 수집 시각 | `2025-03-15T14:30:00.000Z` |
| `cpu_usage_pct` | DOUBLE | CPU 사용률 | `34.7` |
| `mem_total_kb` | INT | 전체 메모리 | `2097152` |
| `mem_used_pct` | DOUBLE | 메모리 사용률 | `75.0` |
| `mem_available_kb` | INT | 가용 메모리 | `524288` |
| `swap_used_kb` | INT | 스왑 사용량 | `102400` |
| `gpu_usage_pct` | DOUBLE | GPU 사용률 | `42.0` |
| `thermal_zone_0_c` | DOUBLE | SoC 온도 | `58.3` |
| `thermal_zone_1_c` | DOUBLE | 패널 온도 | `42.5` |
| `thermal_throttle_active` | BOOLEAN | 쓰로틀링 여부 | `false` |
| `storage_available_mb` | INT | 잔여 저장 공간 | `3200` |
| `active_app_id` | STRING | 현재 포그라운드 앱 | `netflix`, `com.webos.app.livetv` |
| `process_count` | INT | 실행 프로세스 수 | `127` |
| `network_rx_bytes` | BIGINT | 수신 바이트 | `1048576000` |
| `network_tx_bytes` | BIGINT | 송신 바이트 | `5242880` |

### Genie Code 프롬프트

```
200,000건의 TV 시스템 리소스 사용량 데이터를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.resource_utilization
- device_id는 devices 테이블에서 랜덤 샘플링 (활성 디바이스 약 2000대)
- timestamp: 2025-06-01 ~ 2025-06-30 (1개월), 1분 간격 샘플링
- cpu_usage_pct: 앱에 따라 다름
  - com.webos.app.livetv → 15~35%
  - netflix/youtube → 25~55% 
  - 게임(게임앱) → 50~80%
  - 대기 → 5~15%
- mem_total_kb: devices.ram_mb * 1024
- mem_used_pct: 활성 앱 수에 비례, 40~85% 범위
- gpu_usage_pct: 4K HDR 재생 시 40~70%, SDR 시 15~35%, 대기 시 5~15%
- thermal_zone_0_c: cpu 사용률과 상관관계 있게 (35 + cpu_usage_pct * 0.4 + noise)
- thermal_zone_1_c: OLED 패널 → 38~50°C, LCD → 30~42°C
- thermal_throttle_active: thermal_zone_0_c > 70일 때 true (약 2%)
- active_app_id 분포: com.webos.app.livetv(30%), netflix(20%), youtube.leanback.v4(15%), amazon(10%), com.webos.app.home(10%), com.disney.disneyplus(5%), 기타(10%)
- network_rx_bytes: 스트리밍 시 높음 (4K: ~25Mbps, HD: ~5Mbps), 대기 시 낮음

Delta 테이블로 저장해줘.
```

---

### 테이블 4: firmware_updates (펌웨어 업데이트 이벤트)

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_OTA_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T03:00:00.000Z` |
| `event_type` | STRING | OTA 이벤트 유형 | `OTA_CHECK`, `OTA_AVAILABLE`, `OTA_DOWNLOAD_START`, `OTA_DOWNLOAD_COMPLETE`, `OTA_INSTALL_START`, `OTA_INSTALL_COMPLETE`, `OTA_ROLLBACK` |
| `current_version` | STRING | 현재 펌웨어 | `03.33.80` |
| `target_version` | STRING | 대상 펌웨어 | `03.33.85` |
| `download_size_bytes` | BIGINT | 다운로드 크기 | `524288000` |
| `download_duration_ms` | BIGINT | 다운로드 소요 시간 | `180000` |
| `install_result` | STRING | 설치 결과 | `SUCCESS`, `FAIL_VERIFY`, `FAIL_SPACE`, `FAIL_POWER` |
| `update_channel` | STRING | 업데이트 채널 | `stable`, `beta` |

### Genie Code 프롬프트

```
15,000건의 펌웨어 업데이트 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.firmware_updates
- device_id는 devices에서 샘플링
- 업데이트는 주로 새벽 2~5시(로컬 타임존)에 발생
- OTA 이벤트는 시퀀스로 발생: CHECK → AVAILABLE → DOWNLOAD_START → DOWNLOAD_COMPLETE → INSTALL_START → INSTALL_COMPLETE
- 95%는 SUCCESS, 2% FAIL_VERIFY, 2% FAIL_SPACE, 1% FAIL_POWER
- FAIL 시 OTA_ROLLBACK 이벤트 추가 발생
- download_size_bytes: 300MB ~ 800MB
- download_duration_ms: 네트워크 속도에 따라 60초 ~ 10분
- update_channel: stable(90%), beta(10%)
- 분기별 1~2회 major 업데이트, 월 1회 minor 업데이트 패턴

Delta 테이블로 저장해줘.
```

---

</details>

---

## 카테고리: Viewing (시청 로그)

<details>
<summary><strong>시청 로그 3개 테이블 펼치기</strong> — viewing_logs(500K), app_launch_events(300K), input_switch_events(80K)</summary>

### 테이블 5: viewing_logs (시청 로그)

> webOS `com.webos.service.utp.broadcast` Luna Service 기반 채널/앱 시청 기록.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_VIEW_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `session_start` | TIMESTAMP | 시청 시작 | `2025-03-15T20:00:00.000Z` |
| `session_end` | TIMESTAMP | 시청 종료 | `2025-03-15T21:30:00.000Z` |
| `duration_sec` | INT | 시청 시간 (초) | `5400` |
| `content_source` | STRING | 콘텐츠 소스 | `live_tv`, `ott_app`, `hdmi_input`, `usb_media` |
| `app_id` | STRING | 앱 ID (OTT일 때) | `netflix`, `youtube.leanback.v4`, `com.webos.app.livetv` |
| `channel_number` | STRING | 채널 번호 (Live TV) | `6.1`, `11-1` |
| `channel_name` | STRING | 채널명 | `KBS1`, `MBC`, `SBS`, `tvN`, `JTBC` |
| `broadcast_type` | STRING | 방송 타입 | `ATSC`, `DVB-T`, `IPTV`, `IP_STREAM` |
| `program_title` | STRING | 프로그램명 | `뉴스9`, `나혼자산다` |
| `genre` | STRING | 장르 | `Drama`, `News`, `Entertainment`, `Sports`, `Kids`, `Movie`, `Documentary` |
| `signal_strength_dbm` | DOUBLE | 신호 세기 | `-52.3` |
| `signal_quality_pct` | INT | 신호 품질 | `87` |
| `tune_latency_ms` | INT | 채널 전환 지연 | `1250` |
| `resolution` | STRING | 해상도 | `3840x2160`, `1920x1080` |
| `hdr_type` | STRING | HDR 타입 | `DolbyVision`, `HDR10`, `HDR10Plus`, `HLG`, `SDR` |

### Genie Code 프롬프트

```
500,000건의 Smart TV 시청 로그를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.viewing_logs
- device_id는 devices에서 샘플링 (전체 10,000대 중 활성 약 8,000대)
- timestamp: 2025-01-01 ~ 2025-12-31
- 시청 패턴 반영:
  - 평일: 저녁 6시~12시 피크 (60%), 점심 12~1시 (10%), 나머지 시간 (30%)
  - 주말: 오전 10시~12시 (15%), 오후 2시~6시 (25%), 저녁 6시~12시 (40%), 기타 (20%)
- content_source 분포: live_tv(35%), ott_app(45%), hdmi_input(15%), usb_media(5%)
- OTT app_id 분포: netflix(30%), youtube(25%), 디즈니+(15%), 웨이브(10%), 쿠팡플레이(10%), 티빙(10%)
- 한국 지역 채널: KBS1, KBS2, MBC, SBS, EBS, tvN, JTBC, MBN, 채널A, TV조선, OCN, Mnet
- genre 분포: Drama(25%), Entertainment(20%), News(15%), Sports(15%), Movie(10%), Kids(8%), Documentary(7%)
- duration_sec: 평균 45분, 뉴스 30분, 드라마 60~70분, 영화 90~120분, 유튜브 5~30분
- resolution: OLED → 4K(70%), FHD(30%), UHD TV → 4K(50%), FHD(50%)
- hdr_type: OLED에서 DolbyVision(30%), HDR10(25%), SDR(45%) / LCD에서 HDR10(20%), SDR(80%)
- region별로 채널명과 앱 분포를 다르게 설정 (KR은 한국 채널/앱, US는 미국 채널/앱)

Delta 테이블로 저장해줘.
```

---

### 테이블 6: app_launch_events (앱 실행 이벤트)

> webOS `com.webos.applicationManager` (SAM) Luna Service 기반.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_APP_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T20:00:00.000Z` |
| `msgid` | STRING | SAM 메시지 ID | `NL_APP_LAUNCH_BEGIN`, `NL_APP_LAUNCH_END`, `APP_CLOSE`, `APP_PAUSE`, `APP_RELAUNCH` |
| `app_id` | STRING | 앱 ID | `netflix`, `youtube.leanback.v4`, `com.webos.app.browser` |
| `app_name` | STRING | 앱 이름 | `Netflix`, `YouTube`, `웹 브라우저` |
| `app_version` | STRING | 앱 버전 | `5.4.1-2028` |
| `caller_id` | STRING | 호출자 | `com.webos.surfacemanager`, `com.webos.app.home` |
| `launch_mode` | STRING | 실행 모드 | `normal`, `background`, `hidden` |
| `launch_time_ms` | INT | 실행 소요 시간 | `3200` |
| `close_reason` | STRING | 종료 사유 | `user`, `system_oom`, `app_crash`, `relaunch` |
| `session_duration_sec` | INT | 세션 시간 | `5420` |
| `memory_at_launch_kb` | INT | 실행 시 메모리 사용량 | `1245184` |

### Genie Code 프롬프트

```
300,000건의 앱 실행 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.app_launch_events
- device_id는 devices에서 샘플링
- msgid 시퀀스: NL_APP_LAUNCH_BEGIN → NL_APP_LAUNCH_END → (사용) → APP_CLOSE
- app_id 상위 목록:
  - com.webos.app.livetv, com.webos.app.home, netflix, youtube.leanback.v4
  - amazon, com.disney.disneyplus-prod, com.webos.app.browser, com.webos.app.photovideo
  - com.webos.app.settings, com.webos.app.musicplayer, wavve, coupangplay, tving
- launch_time_ms: 앱별 차이 — Netflix(2000~4000), YouTube(1500~3000), LiveTV(800~2000), 설정(500~1000)
- close_reason: user(85%), system_oom(8%), app_crash(5%), relaunch(2%)
- session_duration_sec: Netflix/YouTube(평균 45분), LiveTV(평균 60분), 설정(평균 2분), 브라우저(평균 15분)
- caller_id: 대부분 com.webos.surfacemanager 또는 com.webos.app.home

Delta 테이블로 저장해줘.
```

---

### 테이블 7: input_switch_events (입력 소스 전환)

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_INPUT_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 전환 시각 | `2025-03-15T19:30:00.000Z` |
| `input_id` | STRING | 전환된 입력 | `HDMI_1`, `HDMI_2`, `HDMI_3`, `HDMI_4` |
| `previous_input_id` | STRING | 이전 입력 | `HDMI_2` |
| `device_type` | STRING | 연결 기기 유형 | `stb`, `game_console`, `soundbar`, `bluray`, `pc`, `unknown` |
| `cec_device_name` | STRING | CEC 디바이스명 | `PlayStation 5`, `XBOX Series X`, `Apple TV` |
| `hdmi_signal_type` | STRING | HDMI 신호 타입 | `HDMI2.1`, `HDMI2.0`, `eARC` |
| `allm_active` | BOOLEAN | 자동 저지연 모드 | `true` |
| `vrr_active` | BOOLEAN | 가변 주사율 | `true` |

### Genie Code 프롬프트

```
80,000건의 HDMI 입력 전환 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.input_switch_events  
- device_id는 devices에서 샘플링 (HDMI 사용 디바이스 약 60%)
- device_type 분포: stb(35%), game_console(25%), soundbar(15%), bluray(10%), pc(10%), unknown(5%)
- cec_device_name 예시:
  - game_console → "PlayStation 5", "XBOX Series X", "Nintendo Switch"
  - stb → "Apple TV 4K", "Chromecast", "Fire TV Stick", "KT IPTV", "SK Btv", "LG U+ tv"
  - bluray → "LG UBK90", "Sony UBP-X800M2"
- HDMI2.1 비율: OLED_C/G → 80%, 기타 → 30%
- allm_active: game_console일 때 90% true
- vrr_active: game_console이고 HDMI2.1일 때 85% true
- 전환 빈도: 게이머 디바이스는 하루 3~5회, 일반은 1~2회

Delta 테이블로 저장해줘.
```

---

</details>

---

## 카테고리: Network (네트워크)

<details>
<summary><strong>네트워크 2개 테이블 펼치기</strong> — wifi_connection_events(100K), streaming_buffer_events(150K)</summary>

### 테이블 8: wifi_connection_events (WiFi 연결 이벤트)

> webOS `com.webos.service.connectionmanager` Luna Service 기반.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_WIFI_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T09:00:00.000Z` |
| `event_type` | STRING | 이벤트 유형 | `WIFI_CONNECTED`, `WIFI_DISCONNECTED`, `WIFI_AUTH_FAIL`, `DHCP_SUCCESS`, `DHCP_FAIL`, `WIFI_SCAN_COMPLETE` |
| `state` | STRING | 연결 상태 | `connected`, `disconnected`, `connecting`, `associating` |
| `ssid` | STRING | SSID | `HomeNetwork_5G` |
| `security_type` | STRING | 보안 타입 | `WPA2-PSK`, `WPA3-SAE`, `WPA2-Enterprise` |
| `frequency_mhz` | INT | 주파수 | `5180`, `2437` |
| `channel` | INT | 채널 | `36`, `6` |
| `signal_strength_dbm` | INT | 신호 세기 | `-45` |
| `link_speed_mbps` | INT | 링크 속도 | `866`, `150`, `1200` |
| `ip_address` | STRING | IP 주소 | `192.168.1.105` |
| `gateway` | STRING | 게이트웨이 | `192.168.1.1` |
| `dns_servers` | STRING | DNS 서버 | `8.8.8.8,8.8.4.4` |

### Genie Code 프롬프트

```
100,000건의 WiFi 연결 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.wifi_connection_events
- device_id는 devices에서 network_type이 wifi인 디바이스만 (약 85%)
- event_type: WIFI_CONNECTED(40%), WIFI_DISCONNECTED(25%), DHCP_SUCCESS(20%), WIFI_SCAN_COMPLETE(10%), WIFI_AUTH_FAIL(3%), DHCP_FAIL(2%)
- ssid: 가정집 WiFi 이름 패턴 ("HomeNet_5G", "KT_GiGA_XXXX", "SK_WiFi_XXXX", "U+Net_XXXX", "iptime_XXXX")
- security_type: WPA2-PSK(60%), WPA3-SAE(25%), WPA2-Enterprise(10%), Open(5%)
- frequency_mhz: 5GHz대역(5180,5200,5220,5240,5745,5765) 60%, 2.4GHz대역(2412,2437,2462) 40%
- signal_strength_dbm: -30 ~ -80 범위, 평균 -50
- link_speed_mbps: 5GHz→300~1200, 2.4GHz→72~300
- IP: 192.168.x.x 대역 (x는 0,1,2 중 랜덤, 호스트는 100~250)
- 연결 끊김은 주로 라우터 재부팅, 신호 약화, DHCP 갱신 시 발생

Delta 테이블로 저장해줘.
```

---

### 테이블 9: streaming_buffer_events (스트리밍 버퍼 이벤트)

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_BUF_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T21:15:30.000Z` |
| `event_type` | STRING | 버퍼 이벤트 | `STREAM_START`, `BUFFER_UNDERRUN`, `BUFFER_RECOVERY`, `BITRATE_SWITCH`, `STREAM_STOP`, `STREAM_ERROR` |
| `app_id` | STRING | 스트리밍 앱 | `netflix`, `youtube.leanback.v4` |
| `buffer_level_pct` | DOUBLE | 버퍼 수준 | `15.0` |
| `buffer_duration_ms` | INT | 버퍼 시간 | `2400` |
| `stall_count` | INT | 정지 횟수 | `3` |
| `stall_duration_total_ms` | INT | 총 정지 시간 | `8500` |
| `current_bitrate_kbps` | INT | 현재 비트레이트 | `15000` |
| `target_bitrate_kbps` | INT | 목표 비트레이트 | `25000` |
| `cdn_host` | STRING | CDN 호스트 | `ipv4-c038-sel.nflxvideo.net` |
| `latency_ms` | INT | 레이턴시 | `28` |
| `dns_resolve_ms` | INT | DNS 해석 시간 | `45` |

### Genie Code 프롬프트

```
150,000건의 스트리밍 버퍼 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.streaming_buffer_events
- device_id는 devices에서 샘플링
- event_type 분포: STREAM_START(25%), BITRATE_SWITCH(30%), BUFFER_UNDERRUN(10%), BUFFER_RECOVERY(10%), STREAM_STOP(20%), STREAM_ERROR(5%)
- app_id: netflix(30%), youtube(25%), wavve(15%), coupangplay(10%), tving(10%), disney+(10%)
- BUFFER_UNDERRUN은 signal_strength가 약하거나 link_speed가 낮은 디바이스에서 더 자주 발생
- current_bitrate_kbps: 4K(15000~25000), FHD(3000~8000), HD(1500~3000)
- BITRATE_SWITCH: 상향(60%), 하향(40%)
- cdn_host: 앱별 CDN 패턴 — Netflix는 nflxvideo.net, YouTube는 googlevideo.com
- latency_ms: 국내 10~50ms, 해외 40~200ms
- stall_count: 대부분 0, BUFFER_UNDERRUN 시 1~10

Delta 테이블로 저장해줘.
```

---

</details>

---

## 카테고리: Media & Ad (미디어 & 광고)

<details>
<summary><strong>미디어/광고 3개 테이블 펼치기</strong> — media_playback_events(200K), acr_events(300K), ad_impressions(200K)</summary>

### 테이블 10: media_playback_events (미디어 재생 이벤트)

> 비디오 코덱, 해상도, HDR 메타데이터 등 미디어 파이프라인 로그.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_MEDIA_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T20:05:00.000Z` |
| `event_type` | STRING | 이벤트 유형 | `MEDIA_PLAY_START`, `MEDIA_PLAY_STOP`, `RESOLUTION_CHANGE`, `HDR_MODE_CHANGE`, `CODEC_SWITCH` |
| `video_codec` | STRING | 비디오 코덱 | `HEVC`, `AV1`, `VP9`, `H264` |
| `video_profile` | STRING | 코덱 프로파일 | `Main10`, `Main`, `High` |
| `resolution` | STRING | 해상도 | `3840x2160`, `1920x1080` |
| `frame_rate` | DOUBLE | 프레임레이트 | `59.94`, `23.976`, `120.0` |
| `bit_depth` | INT | 비트 심도 | `10`, `8` |
| `color_space` | STRING | 색 공간 | `BT.2020`, `BT.709` |
| `hdr_type` | STRING | HDR 타입 | `DolbyVision`, `HDR10`, `HDR10Plus`, `HLG`, `SDR` |
| `dolby_vision_profile` | STRING | DV 프로파일 | `dvhe.05.06`, `dvhe.08.06` |
| `max_cll_nits` | INT | 최대 콘텐츠 밝기 | `1000` |
| `max_fall_nits` | INT | 최대 프레임 평균 밝기 | `400` |
| `audio_codec` | STRING | 오디오 코덱 | `EAC3_ATMOS`, `EAC3`, `AAC`, `AC3` |
| `audio_channels` | STRING | 오디오 채널 | `7.1.4`, `5.1`, `2.0` |
| `audio_passthrough` | BOOLEAN | eARC 패스스루 | `true` |
| `content_source` | STRING | 콘텐츠 소스 | `ott`, `live_tv`, `hdmi`, `usb` |
| `drm_type` | STRING | DRM 타입 | `widevine`, `playready`, `none` |

### Genie Code 프롬프트

```
200,000건의 미디어 재생 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.media_playback_events
- device_id는 devices에서 샘플링
- video_codec 분포: HEVC(40%), AV1(20%), VP9(15%), H264(20%), MPEG2(5%)
  - AV1은 주로 YouTube, Netflix 최신 콘텐츠
  - VP9는 YouTube
  - MPEG2는 live_tv 지상파
- resolution: 4K(50%), FHD(35%), HD(10%), 8K(5% - QNED 8K 모델만)
- hdr_type: OLED 디바이스 → DolbyVision(25%), HDR10(20%), HDR10Plus(10%), HLG(10%), SDR(35%)
- hdr_type: LCD 디바이스 → HDR10(15%), HDR10Plus(5%), HLG(10%), SDR(70%)
- frame_rate: 영화(23.976), 방송(29.97/59.94), 게임(60/120)
- audio_codec: OTT → EAC3_ATMOS(20%), EAC3(30%), AAC(50%) / Live TV → AC3(60%), AAC(40%)
- drm_type: OTT → widevine(70%), playready(30%) / Live TV/USB → none
- DolbyVision 재생 시 dolby_vision_profile 포함, 아니면 null

Delta 테이블로 저장해줘.
```

---

### 테이블 11: acr_events (자동 콘텐츠 인식 이벤트)

> LG "Live Plus" ACR 시스템. 화면 핑거프린트를 통한 콘텐츠 식별.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_ACR_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T20:30:00.000Z` |
| `event_type` | STRING | ACR 이벤트 | `ACR_FINGERPRINT`, `ACR_MATCH`, `ACR_NO_MATCH` |
| `fingerprint_hash` | STRING | 화면 해시 | `a3f8c2e1b7d9...` (32자 hex) |
| `match_confidence` | DOUBLE | 매칭 신뢰도 | `0.97` |
| `content_id` | STRING | Gracenote 프로그램 ID | `EP012345678901` |
| `program_title` | STRING | 프로그램명 | `슬기로운 의사생활`, `Breaking Bad` |
| `network_name` | STRING | 방송 네트워크 | `tvN`, `NBC` |
| `genre` | STRING | 장르 | `Drama`, `News`, `Sports` |
| `content_type` | STRING | 콘텐츠 유형 | `linear_tv`, `ott_stream`, `hdmi_external`, `gaming` |
| `is_ad_break` | BOOLEAN | 광고 시간 여부 | `true` |
| `ad_brand` | STRING | 광고 브랜드 (광고일 때) | `Samsung`, `Hyundai`, `Toyota` |
| `dma_code` | STRING | 지역 코드 | `KR_SEOUL`, `US_501` |

### Genie Code 프롬프트

```
300,000건의 ACR(자동 콘텐츠 인식) 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.acr_events
- device_id는 devices에서 샘플링 (ACR opt-in 디바이스 약 70%)
- event_type: ACR_MATCH(70%), ACR_NO_MATCH(20%), ACR_FINGERPRINT(10%)
- 30초 간격으로 fingerprint 생성 (실제는 10ms이지만 로그 집계 기준)
- match_confidence: ACR_MATCH일 때 0.85~0.99 분포
- content_type: linear_tv(45%), ott_stream(30%), hdmi_external(20%), gaming(5%)
- is_ad_break: linear_tv일 때 약 25% true (15분당 3~4분 광고)
- 한국 프로그램: 드라마(슬기로운 의사생활, 이상한 변호사 우영우 등), 예능(나혼자산다, 놀면뭐하니 등), 뉴스(KBS 뉴스9 등)
- 미국 프로그램: Breaking Bad, The Office, NFL Football 등
- ad_brand: 한국(삼성, 현대, LG, SK, 롯데 등), 미국(Toyota, Apple, Amazon 등)
- dma_code: 한국(KR_SEOUL, KR_BUSAN, KR_INCHEON 등), 미국(US_501, US_803 등)

Delta 테이블로 저장해줘.
```

---

### 테이블 12: ad_impressions (광고 노출/클릭/전환)

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_AD_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T20:45:00.000Z` |
| `event_type` | STRING | 광고 이벤트 | `AD_REQUEST`, `AD_IMPRESSION`, `AD_START`, `AD_FIRST_QUARTILE`, `AD_MIDPOINT`, `AD_THIRD_QUARTILE`, `AD_COMPLETE`, `AD_SKIP`, `AD_CLICK`, `AD_ERROR` |
| `ad_unit_id` | STRING | 광고 유닛 | `lg_home_banner_01`, `lg_screensaver_01`, `lg_channel_strip_01` |
| `creative_id` | STRING | 크리에이티브 ID | `CR_20250301_001` |
| `campaign_id` | STRING | 캠페인 ID | `CAMP_Q1_2025_0042` |
| `advertiser_name` | STRING | 광고주 | `Samsung Electronics`, `Hyundai Motor` |
| `ad_format` | STRING | 광고 형식 | `display_banner`, `video_preroll`, `native_tile`, `screensaver`, `pause_ad` |
| `ad_duration_sec` | INT | 광고 길이 | `15`, `30`, `60` |
| `completion_pct` | DOUBLE | 시청 완료율 | `75.0` |
| `placement` | STRING | 노출 위치 | `home_screen`, `content_store`, `lg_channels`, `epg`, `screensaver` |
| `revenue_model` | STRING | 수익 모델 | `CPM`, `CPC`, `CPCV` |
| `bid_price_usd` | DOUBLE | 입찰 가격 | `12.50` |
| `viewability_pct` | DOUBLE | 가시성 | `100.0` |

### Genie Code 프롬프트

```
200,000건의 광고 노출/클릭/전환 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.ad_impressions
- device_id는 devices에서 샘플링
- VAST 이벤트 퍼널: AD_REQUEST → AD_IMPRESSION → AD_START → AD_FIRST_QUARTILE → AD_MIDPOINT → AD_THIRD_QUARTILE → AD_COMPLETE
- 퍼널 드롭율: REQUEST→IMPRESSION(90%), START→COMPLETE(70%), SKIP(15%), ERROR(5%)
- AD_CLICK: IMPRESSION 대비 약 2~5% CTR
- ad_format 분포: display_banner(30%), video_preroll(25%), native_tile(20%), screensaver(15%), pause_ad(10%)
- placement: home_screen(35%), lg_channels(25%), content_store(15%), epg(15%), screensaver(10%)
- ad_duration_sec: 15초(40%), 30초(40%), 60초(20%)
- revenue_model: CPM(60%), CPC(25%), CPCV(15%)
- bid_price_usd: CPM($5~25), CPC($0.5~3), CPCV($10~40)
- advertiser_name: 대기업 위주 (삼성, 현대, SK, LG, 롯데, CJ, 네이버, 카카오 등)
- 시간대별 bid_price 변동: 프라임타임(20~23시) 1.5배, 심야(0~6시) 0.5배

Delta 테이블로 저장해줘.
```

---

</details>

---

## 카테고리: IoT & Voice & App

<details>
<summary><strong>IoT/음성/앱 3개 테이블 펼치기</strong> — thinq_device_events(50K), voice_command_events(80K), app_lifecycle_events(100K)</summary>

### 테이블 13: thinq_device_events (ThinQ IoT 디바이스 이벤트)

> `com.webos.service.iot` Luna Service 기반 ThinQ 스마트홈 연동 이벤트.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_IOT_20250301_000001` |
| `device_id` | STRING | FK → devices (TV) | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T18:00:00.000Z` |
| `event_type` | STRING | IoT 이벤트 | `DEVICE_DISCOVERED`, `DEVICE_PAIRED`, `DEVICE_STATUS_CHANGE`, `DEVICE_COMMAND_SENT`, `DEVICE_COMMAND_ACK`, `DEVICE_REMOVED` |
| `iot_device_id` | STRING | IoT 디바이스 ID | `LG_REF_KR_001234` |
| `iot_device_type` | STRING | 디바이스 유형 | `refrigerator`, `washer`, `dryer`, `air_conditioner`, `air_purifier`, `robot_vacuum`, `styler` |
| `iot_device_model` | STRING | 디바이스 모델 | `LRMVS3006S` |
| `protocol` | STRING | 통신 프로토콜 | `thinq_cloud`, `matter`, `wifi_direct` |
| `connection_status` | STRING | 연결 상태 | `online`, `offline`, `pairing` |
| `command` | STRING | 명령어 | `power_on`, `set_temperature`, `start_cycle`, `get_status` |
| `command_result` | STRING | 명령 결과 | `success`, `timeout`, `device_offline`, `invalid_command` |
| `response_time_ms` | INT | 응답 시간 | `450` |

### Genie Code 프롬프트

```
50,000건의 ThinQ IoT 디바이스 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.thinq_device_events
- device_id는 devices에서 thinq_connected=true인 디바이스만 (약 70%)
- TV 1대당 평균 3~5개 IoT 디바이스 연결
- iot_device_type 분포: air_conditioner(25%), washer(20%), refrigerator(20%), air_purifier(15%), robot_vacuum(10%), dryer(5%), styler(5%)
- event_type: DEVICE_STATUS_CHANGE(35%), DEVICE_COMMAND_SENT(25%), DEVICE_COMMAND_ACK(20%), DEVICE_DISCOVERED(10%), DEVICE_PAIRED(5%), DEVICE_REMOVED(5%)
- command 예시:
  - air_conditioner: set_temperature, set_mode, power_on, power_off, set_fan_speed
  - washer: start_cycle, pause_cycle, get_remaining_time, set_temperature
  - refrigerator: get_status, set_temperature, express_freeze_on
  - robot_vacuum: start_clean, return_home, set_schedule
- command_result: success(90%), timeout(5%), device_offline(3%), invalid_command(2%)
- response_time_ms: thinq_cloud(300~2000), matter(50~300), wifi_direct(100~500)
- protocol: thinq_cloud(70%), matter(20%), wifi_direct(10%)

Delta 테이블로 저장해줘.
```

---

### 테이블 14: voice_command_events (음성 명령 이벤트)

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_VOICE_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T20:10:00.000Z` |
| `event_type` | STRING | 음성 이벤트 | `VOICE_WAKE`, `VOICE_COMMAND_START`, `VOICE_COMMAND_END`, `VOICE_RESULT`, `VOICE_ERROR`, `VOICE_CANCEL` |
| `assistant_type` | STRING | 어시스턴트 | `lg_thinq_ai`, `alexa`, `google_assistant` |
| `wake_word` | STRING | 웨이크워드 | `하이 엘지`, `Alexa`, `Hey Google` |
| `transcript` | STRING | 인식된 텍스트 | `채널 KBS로 바꿔줘` |
| `intent` | STRING | 의도 분류 | `channel_change`, `volume_control`, `search_content`, `smart_home_control`, `app_launch`, `general_query` |
| `confidence_score` | DOUBLE | 인식 신뢰도 | `0.92` |
| `result_status` | STRING | 처리 결과 | `success`, `partial_match`, `no_match`, `timeout` |
| `audio_duration_ms` | INT | 음성 길이 | `2100` |
| `processing_latency_ms` | INT | 처리 지연 | `850` |
| `microphone_source` | STRING | 마이크 소스 | `magic_remote`, `built_in` |
| `language` | STRING | 언어 | `ko-KR`, `en-US`, `ja-JP` |

### Genie Code 프롬프트

```
80,000건의 음성 명령 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.voice_command_events
- device_id는 devices에서 voice_assistant != 'none'인 디바이스 (약 85%)
- assistant_type은 devices.voice_assistant 값 사용
- intent 분포: channel_change(20%), volume_control(15%), search_content(25%), smart_home_control(15%), app_launch(15%), general_query(10%)
- 한국어 transcript 예시:
  - channel_change: "KBS로 바꿔줘", "다음 채널", "11번 채널"
  - volume_control: "볼륨 올려", "소리 좀 줄여", "음소거"
  - search_content: "액션 영화 추천해줘", "BTS 뮤직비디오 찾아줘"
  - smart_home_control: "에어컨 온도 24도로 설정", "로봇청소기 시작"
  - app_launch: "넷플릭스 열어", "유튜브 틀어줘"
  - general_query: "내일 날씨 알려줘", "지금 몇시야"
- confidence_score: success(0.85~0.99), partial_match(0.5~0.84), no_match(<0.5)
- result_status: success(75%), partial_match(12%), no_match(8%), timeout(3%), error(2%)
- processing_latency_ms: lg_thinq_ai(500~1500), alexa(300~1200), google(200~1000)
- microphone_source: magic_remote(80%), built_in(20%)
- language: devices.region에 따라 — KR→ko-KR, US→en-US, JP→ja-JP, EU→en-GB/de-DE/fr-FR

Delta 테이블로 저장해줘.
```

---

### 테이블 15: app_lifecycle_events (앱 설치/삭제/업데이트)

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_APPLIFE_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T14:00:00.000Z` |
| `event_type` | STRING | 라이프사이클 이벤트 | `APP_INSTALL`, `APP_UNINSTALL`, `APP_UPDATE`, `APP_UPDATE_CHECK` |
| `app_id` | STRING | 앱 ID | `com.disney.disneyplus-prod` |
| `app_name` | STRING | 앱 이름 | `Disney+` |
| `app_version` | STRING | 앱 버전 | `2.14.0-rc1` |
| `previous_version` | STRING | 이전 버전 (업데이트 시) | `2.13.2` |
| `app_size_bytes` | BIGINT | 앱 크기 | `52428800` |
| `install_source` | STRING | 설치 소스 | `content_store`, `preloaded`, `auto_update` |
| `category` | STRING | 앱 카테고리 | `Entertainment`, `Game`, `Education`, `Utility`, `Lifestyle` |
| `download_duration_ms` | INT | 다운로드 시간 | `15000` |
| `install_result` | STRING | 설치 결과 | `SUCCESS`, `FAIL_SPACE`, `FAIL_NETWORK`, `FAIL_VERIFY`, `FAIL_INCOMPATIBLE` |
| `storage_after_mb` | INT | 설치 후 잔여 저장 공간 | `2800` |

### Genie Code 프롬프트

```
100,000건의 앱 라이프사이클 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.app_lifecycle_events
- device_id는 devices에서 샘플링
- event_type 분포: APP_UPDATE(50%), APP_UPDATE_CHECK(25%), APP_INSTALL(15%), APP_UNINSTALL(10%)
- app 목록 (인기순):
  - 스트리밍: netflix, youtube, disney+, wavve, tving, coupangplay, apple_tv, amazon_prime
  - 게임: apple_arcade, geforce_now, stadia
  - 유틸리티: com.webos.app.browser, com.webos.app.miracast, airplay
  - 교육: khan_academy, ted, duolingo
  - 라이프: melon, spotify, bugs_music, flo
- install_source: content_store(60%), auto_update(30%), preloaded(10%)
- install_result: SUCCESS(95%), FAIL_SPACE(2%), FAIL_NETWORK(2%), FAIL_VERIFY(0.5%), FAIL_INCOMPATIBLE(0.5%)
- app_size_bytes: 스트리밍(30~80MB), 게임(50~200MB), 유틸리티(5~20MB)
- auto_update는 주로 새벽 3~5시에 발생
- category: Entertainment(50%), Game(15%), Utility(15%), Education(10%), Lifestyle(10%)

Delta 테이블로 저장해줘.
```

---

</details>

---

## 카테고리: Display & Error (디스플레이 & 에러)

<details>
<summary><strong>디스플레이/에러 2개 테이블 펼치기</strong> — panel_diagnostics(30K), error_crash_events(40K)</summary>

### 테이블 16: panel_diagnostics (패널/디스플레이 진단)

> OLED 패널 케어, 픽셀 리프레셔, 밝기 제어 등 디스플레이 진단 로그.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_PANEL_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T04:00:00.000Z` |
| `event_type` | STRING | 패널 이벤트 | `PIXEL_REFRESH_SHORT`, `PIXEL_REFRESH_LONG`, `JB_COMPENSATION`, `OFFRS_COMPENSATION`, `ABL_ADJUST`, `TPC_ADJUST`, `GSR_CYCLE` |
| `panel_type` | STRING | 패널 타입 | `WOLED`, `OLED_EX`, `MLA_OLED_EX` |
| `panel_total_hours` | INT | 총 사용 시간 | `4328` |
| `panel_on_count` | INT | 총 ON 횟수 | `2847` |
| `compensation_type` | STRING | 보상 유형 | `offrs` (4시간마다), `jb` (2000시간마다) |
| `trigger_reason` | STRING | 트리거 사유 | `auto_scheduled`, `user_manual`, `cumulative_hours` |
| `duration_min` | INT | 소요 시간 | `7`, `60` |
| `result` | STRING | 결과 | `completed`, `interrupted_power_loss`, `skipped_no_standby` |
| `backlight_level` | INT | OLED 밝기 수준 | `80` |
| `abl_current_pct` | DOUBLE | ABL 현재 수준 | `72.0` |
| `peak_luminance_nits` | INT | 피크 휘도 | `800` |
| `panel_temperature_c` | DOUBLE | 패널 온도 | `42.5` |
| `ambient_light_lux` | INT | 주변 조도 | `120` |
| `picture_mode` | STRING | 화질 모드 | `filmmaker`, `vivid`, `standard`, `eco`, `game` |
| `energy_saving_mode` | STRING | 절전 모드 | `auto`, `off`, `minimum`, `medium`, `maximum` |

### Genie Code 프롬프트

```
30,000건의 패널 진단 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.panel_diagnostics
- device_id는 devices에서 OLED 제품군(OLED_C, OLED_G, OLED_B) 위주 (70%), LCD도 일부 포함 (30%)
- OLED 전용 이벤트: PIXEL_REFRESH_SHORT, PIXEL_REFRESH_LONG, JB_COMPENSATION, OFFRS_COMPENSATION, GSR_CYCLE
- 공통 이벤트: ABL_ADJUST, TPC_ADJUST
- PIXEL_REFRESH_SHORT(OFFRS): 4시간 사용마다 자동 실행, 7분 소요
- PIXEL_REFRESH_LONG(JB): 2000시간마다 자동 실행, 60분 소요
- panel_total_hours: 100 ~ 10000 범위 (오래된 TV일수록 높음)
- trigger_reason: auto_scheduled(85%), cumulative_hours(10%), user_manual(5%)
- result: completed(92%), interrupted_power_loss(5%), skipped_no_standby(3%)
- backlight_level: 일반적으로 50~100, eco 모드 시 30~50
- picture_mode 분포: standard(30%), vivid(20%), filmmaker(15%), eco(15%), game(10%), hdr_cinema(10%)
- energy_saving_mode: auto(40%), off(30%), minimum(15%), medium(10%), maximum(5%)
- ambient_light_lux: 낮(200~500), 저녁(50~150), 심야(0~50)

Delta 테이블로 저장해줘.
```

---

### 테이블 17: error_crash_events (에러/크래시 로그)

> webOS `rdxd` 데몬이 수집하는 크래시/에러 리포트.

### 스키마 정의

| 컬럼 | 타입 | 설명 | 예시 값 |
|------|------|------|---------|
| `event_id` | STRING | 이벤트 고유 ID | `EVT_ERR_20250301_000001` |
| `device_id` | STRING | FK → devices | `LGE_TV_KR_000001` |
| `timestamp` | TIMESTAMP | 이벤트 시각 | `2025-03-15T22:30:00.000Z` |
| `event_type` | STRING | 에러 유형 | `APP_CRASH`, `APP_ANR`, `APP_OOM`, `SYSTEM_WATCHDOG`, `KERNEL_PANIC`, `GPU_HANG`, `MEDIA_PIPELINE_ERROR` |
| `severity` | STRING | 심각도 | `CRITICAL`, `ERROR`, `WARNING` |
| `process_name` | STRING | 프로세스명 | `WebAppMgr`, `sam`, `audiod`, `media-pipeline`, `settingsservice` |
| `app_id` | STRING | 관련 앱 (앱 크래시 시) | `netflix`, `com.webos.app.browser` |
| `crash_signal` | STRING | 크래시 시그널 | `SIGSEGV(11)`, `SIGABRT(6)`, `SIGKILL(9)` |
| `exit_code` | INT | 종료 코드 | `137`, `139`, `134` |
| `error_code` | STRING | 에러 코드 | `MEDIA_ERR_DECODE`, `DRM_LICENSE_FAIL`, `EGL_BAD_DISPLAY` |
| `error_detail` | STRING | 에러 상세 | `EGL initialization failure`, `Widevine L1 error` |
| `cpu_usage_at_event` | DOUBLE | 이벤트 시 CPU | `98.2` |
| `mem_used_pct_at_event` | DOUBLE | 이벤트 시 메모리 | `94.5` |
| `uptime_sec` | BIGINT | 가동 시간 | `86400` |
| `webos_version` | STRING | OS 버전 | `24.10.40` |
| `coredump_available` | BOOLEAN | 코어덤프 존재 여부 | `true` |

### Genie Code 프롬프트

```
40,000건의 에러/크래시 이벤트를 생성해줘.

조건:
- 테이블: lge_smart_tv.bronze.error_crash_events
- device_id는 devices에서 샘플링 (모든 디바이스에서 발생 가능하지만, 구형 firmware에서 더 빈번)
- event_type 분포: APP_CRASH(30%), APP_ANR(20%), APP_OOM(15%), MEDIA_PIPELINE_ERROR(20%), GPU_HANG(5%), SYSTEM_WATCHDOG(5%), KERNEL_PANIC(5%)
- severity: APP_CRASH/ANR/OOM → ERROR, KERNEL_PANIC/SYSTEM_WATCHDOG → CRITICAL, MEDIA_PIPELINE_ERROR/GPU_HANG → ERROR 또는 WARNING
- process_name:
  - APP_CRASH → WebAppMgr(60%), 기타 앱 프로세스
  - APP_ANR → WebAppMgr(50%), sam(20%), settingsservice(10%)
  - APP_OOM → WebAppMgr(70%), media-pipeline(20%)
  - MEDIA_PIPELINE_ERROR → media-pipeline(80%), audiod(20%)
- crash_signal: SIGSEGV(40%), SIGABRT(30%), SIGKILL(20%), SIGBUS(10%)
- APP_OOM일 때: mem_used_pct_at_event > 90%, exit_code = 137
- MEDIA_PIPELINE_ERROR error_code: MEDIA_ERR_DECODE(30%), MEDIA_ERR_NETWORK(25%), DRM_LICENSE_FAIL(20%), MEDIA_ERR_SRC_NOT_SUPPORTED(15%), MEDIA_ERR_ENCRYPTED(10%)
- 구형 webos_version(5.0, 4.5)에서 에러 발생률 2배 높게
- coredump_available: CRITICAL → 90% true, ERROR → 50% true, WARNING → 10% true

Delta 테이블로 저장해줘.
```

---

</details>

---

## 데이터 생성 후 검증

모든 테이블 생성이 완료되면, Genie Code에 다음 프롬프트를 입력하여 데이터를 검증합니다:

> 💡 **팁**: 각 테이블을 하나씩 생성할 때마다, 아래처럼 간단히 확인할 수 있습니다:
> ```
> 방금 만든 테이블의 row 수와 주요 컬럼 분포를 확인해줘.
> ```
> 17개 모두 만든 뒤 아래 종합 검증 프롬프트를 실행하세요.

### 검증 프롬프트

```
lge_smart_tv.bronze 스키마의 모든 테이블에 대해 다음을 확인해줘:
1. 각 테이블의 row count
2. 각 테이블의 컬럼 수와 주요 컬럼의 distinct count
3. device_id가 devices 테이블에 모두 존재하는지 (참조 무결성)
4. timestamp 범위가 예상과 일치하는지
5. NULL 비율이 10%를 넘는 컬럼이 있는지

결과를 요약 테이블로 보여줘.
```

### 기대 결과

| 테이블 | 건수 | 주요 검증 포인트 |
|--------|------|----------------|
| devices | 10,000 | region 분포, product_line 분포 |
| system_boot_events | 50,000 | POWER_ON/OFF 쌍 정합성 |
| resource_utilization | 200,000 | cpu/mem 값 범위, 상관관계 |
| firmware_updates | 15,000 | OTA 이벤트 시퀀스 정합성 |
| viewing_logs | 500,000 | 시간대별 분포, 장르 분포 |
| app_launch_events | 300,000 | launch/close 쌍, duration 합리성 |
| input_switch_events | 80,000 | HDMI 포트와 device_type 매핑 |
| wifi_connection_events | 100,000 | WiFi 디바이스만 포함 여부 |
| streaming_buffer_events | 150,000 | bitrate와 resolution 상관관계 |
| media_playback_events | 200,000 | codec/HDR과 디바이스 스펙 매핑 |
| acr_events | 300,000 | ACR opt-in 디바이스만 포함 |
| ad_impressions | 200,000 | VAST 퍼널 드롭율 |
| thinq_device_events | 50,000 | thinq_connected 디바이스만 |
| voice_command_events | 80,000 | voice_assistant 디바이스만 |
| app_lifecycle_events | 100,000 | install_result 분포 |
| panel_diagnostics | 30,000 | OLED 전용 이벤트 필터링 |
| error_crash_events | 40,000 | 구형 FW 에러율 비교 |
| **합계** | **~2,405,000** | |

---

## 다음 단계

데이터 생성이 완료되면 다음 모듈로 이동합니다:

- **[03. SDP 파이프라인 — 데이터 품질과 Medallion Architecture](03-sdp-pipeline.md)** — Bronze→Silver→Gold 변환 + 증분 처리 자동화
- **[04. 대시보드 & Genie Space](04-dashboard-genie.md)** — AI/BI 대시보드 + Genie Space + 정확도 고도화
