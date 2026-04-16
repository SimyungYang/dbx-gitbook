"""
LGE Smart TV SDP Pipeline — 생성 및 실행 스크립트

Silver 파이프라인 → Gold 파이프라인 순차 실행.
DLT UC 파이프라인은 target schema 필수이므로 2개로 분리.

1. Silver 노트북 + Gold 노트북 업로드
2. Silver 파이프라인 생성 → 실행 → 완료 대기
3. Gold 파이프라인 생성 → 실행 → 완료 대기
"""

import base64
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

# ─── 설정 ───────────────────────────────────────────────
PROFILE = "fevm-smarttv"
CATALOG = "byungjun_lee_smarttv_training_catalog"
WAREHOUSE_ID = "cc6084f1d2fff960"
HOST = "https://fevm-byungjun-lee-smarttv-training.cloud.databricks.com"

PIPELINES = [
    {
        "name": "lge_smart_tv_pipeline_claude",
        "target": "silver",
        "local_notebook": Path(__file__).parent / "sdp_pipeline_notebook.sql",
        "remote_notebook": "/Users/byungjun.lee@databricks.com/sdp/lge_smart_tv_pipeline_claude",
    },
    {
        "name": "lge_smart_tv_pipeline_claude_gold",
        "target": "gold",
        "local_notebook": Path(__file__).parent / "sdp_gold_notebook.sql",
        "remote_notebook": "/Users/byungjun.lee@databricks.com/sdp/lge_smart_tv_pipeline_claude_gold",
    },
]

POLL_INTERVAL = 30
MAX_WAIT = 3600


def get_token():
    raw = subprocess.check_output(
        ["databricks", "auth", "token", "--profile", PROFILE], text=True
    ).strip()
    return json.loads(raw)["access_token"]


def api(token, method, path, body=None):
    url = f"{HOST}/api/2.0{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.request(method, url, headers=headers, json=body, timeout=120)
    if resp.status_code >= 400:
        print(f"  ❌ API Error {resp.status_code}: {resp.text[:500]}")
    return resp


def upload_notebook(token, local_path, remote_path):
    """노트북을 워크스페이스에 업로드"""
    content = local_path.read_text(encoding="utf-8")
    b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    parent_dir = str(Path(remote_path).parent)
    api(token, "POST", "/workspace/mkdirs", {"path": parent_dir})

    body = {
        "path": remote_path,
        "format": "SOURCE",
        "language": "SQL",
        "content": b64,
        "overwrite": True,
    }
    resp = api(token, "POST", "/workspace/import", body)
    return resp.status_code < 400


def create_or_update_pipeline(token, name, target, remote_notebook):
    """파이프라인 생성 또는 업데이트. pipeline_id 반환."""
    pipeline_config = {
        "name": name,
        "catalog": CATALOG,
        "target": target,
        "libraries": [{"notebook": {"path": remote_notebook}}],
        "serverless": True,
        "continuous": False,
        "development": True,
        "channel": "CURRENT",
    }

    # 기존 파이프라인 확인
    resp = api(token, "GET", f"/pipelines?filter=name+LIKE+'{name}'&max_results=10")
    if resp.status_code == 200:
        for p in resp.json().get("statuses", []):
            if p.get("name") == name:
                pid = p["pipeline_id"]
                print(f"  ♻️  기존 파이프라인 발견: {pid}")
                api(token, "PUT", f"/pipelines/{pid}", pipeline_config)
                return pid

    # 새로 생성
    resp = api(token, "POST", "/pipelines", pipeline_config)
    if resp.status_code < 400:
        pid = resp.json().get("pipeline_id")
        print(f"  ✅ 파이프라인 생성: {pid}")
        return pid
    return None


def start_and_wait(token, pipeline_id, pipeline_name):
    """파이프라인 실행 후 완료까지 폴링"""
    # 실행 트리거
    body = {"full_refresh": True}
    resp = api(token, "POST", f"/pipelines/{pipeline_id}/updates", body)
    if resp.status_code >= 400:
        print(f"  ❌ {pipeline_name} 실행 실패")
        return "FAILED"

    update_id = resp.json().get("update_id")
    print(f"  🚀 {pipeline_name} 실행 시작 (update: {update_id})")

    # 폴링
    start = time.time()
    final_states = {"COMPLETED", "FAILED", "CANCELED"}

    while time.time() - start < MAX_WAIT:
        resp = api(token, "GET", f"/pipelines/{pipeline_id}")
        if resp.status_code != 200:
            time.sleep(POLL_INTERVAL)
            continue

        data = resp.json()
        latest = data.get("latest_updates", [{}])
        update_state = latest[0].get("state", "UNKNOWN") if latest else "UNKNOWN"
        elapsed = int(time.time() - start)

        print(f"  [{elapsed:>4d}s] {pipeline_name}: {update_state}")

        if update_state in final_states:
            return update_state

        time.sleep(POLL_INTERVAL)

    return "TIMEOUT"


def main():
    print("=" * 60)
    print("  LGE Smart TV SDP Pipeline 생성 및 실행")
    print(f"  Catalog: {CATALOG}")
    print(f"  Pipelines: Silver → Gold (순차)")
    print("=" * 60)

    token = get_token()

    # Step 1: 노트북 업로드
    print("\n📤 Step 1: 노트북 업로드")
    for p in PIPELINES:
        ok = upload_notebook(token, p["local_notebook"], p["remote_notebook"])
        status = "✅" if ok else "❌"
        print(f"  {status} {p['name']} → {p['remote_notebook']}")
        if not ok:
            sys.exit(1)

    results = {}

    # Step 2-3: 각 파이프라인 순차 실행
    for i, p in enumerate(PIPELINES, 1):
        step = i + 1
        print(f"\n🔧 Step {step}a: 파이프라인 생성 — {p['name']} (target={p['target']})")
        pid = create_or_update_pipeline(token, p["name"], p["target"], p["remote_notebook"])
        if not pid:
            print(f"  ❌ {p['name']} 파이프라인 생성 실패")
            sys.exit(1)
        p["pipeline_id"] = pid

        print(f"\n⏳ Step {step}b: {p['name']} 실행 대기")
        result = start_and_wait(token, pid, p["name"])
        results[p["name"]] = result

        if result == "COMPLETED":
            print(f"\n  ✅ {p['name']} 완료!")
        else:
            print(f"\n  ❌ {p['name']} 실패: {result}")
            print(f"     UI: {HOST}/#joblist/pipelines/{pid}")
            if p["target"] == "silver":
                print("  ⚠️  Silver 실패 → Gold 파이프라인 실행 건너뜀")
                break

    # 결과 요약
    print("\n" + "=" * 60)
    print("  결과 요약:")
    for p in PIPELINES:
        pid = p.get("pipeline_id", "N/A")
        status = results.get(p["name"], "SKIPPED")
        icon = "✅" if status == "COMPLETED" else "❌" if status == "FAILED" else "⏭️"
        print(f"  {icon} {p['name']} ({p['target']}): {status}")
        if pid != "N/A":
            print(f"     {HOST}/#joblist/pipelines/{pid}")
    print("=" * 60)


if __name__ == "__main__":
    main()
