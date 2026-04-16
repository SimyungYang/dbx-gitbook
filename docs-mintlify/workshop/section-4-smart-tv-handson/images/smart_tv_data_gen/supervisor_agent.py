# Databricks notebook source
# MAGIC %md
# MAGIC # LG Smart TV AI 어시스턴트 — Supervisor Agent
# MAGIC
# MAGIC | 구성 요소 | 역할 |
# MAGIC |-----------|------|
# MAGIC | **Supervisor** | 질문 의도 파악 → 적절한 에이전트로 라우팅 (Claude Sonnet 4) |
# MAGIC | **Knowledge Assistant** | TV 사용 가이드 FAQ 검색 (Vector Search + LLM) |
# MAGIC | **Genie Agent** | 시청/광고/디바이스 데이터 분석 (Genie Space SQL) |

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch openai --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. 설정

# COMMAND ----------

CATALOG = "byungjun_lee_smarttv_training_catalog"
SCHEMA = "bronze"
KB_TABLE = f"{CATALOG}.{SCHEMA}.tv_knowledge_base"

LLM_ENDPOINT = "databricks-claude-sonnet-4"

VS_ENDPOINT_NAME = "vs-endpoint-smart-tv"
VS_INDEX_NAME = f"{CATALOG}.{SCHEMA}.vs_index_tv_knowledge"

GENIE_SPACES = {
    "시청분석": {
        "space_id": "01f138d0589c178d971724088596e02b",
        "keywords": ["시청", "시간", "프로그램", "콘텐츠", "장르", "OTT", "Netflix", "시청률", "인기", "앱"],
    },
    "광고분석": {
        "space_id": "01f138d16eee1dbdb965eb3e4bbc0812",
        "keywords": ["광고", "CTR", "CPM", "eCPM", "클릭", "노출", "캠페인", "광고주", "수익", "VCR"],
    },
    "디바이스분석": {
        "space_id": "01f138d21c20110081538a24b88d6450",
        "keywords": ["에러", "건강", "health", "디바이스", "펌웨어", "온도", "부팅", "스트리밍 품질", "QoE", "장애"],
    },
}

# COMMAND ----------

import time, json, requests
from openai import OpenAI

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
HOST = ctx.apiUrl().get()
TOKEN = ctx.apiToken().get()

llm_client = OpenAI(api_key=TOKEN, base_url=f"{HOST}/serving-endpoints")

def llm_chat(messages, temperature=0.2, max_tokens=2048):
    """Foundation Model API 호출"""
    resp = llm_client.chat.completions.create(
        model=LLM_ENDPOINT,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content

print(f"✅ LLM 연결 확인: {LLM_ENDPOINT}")
print(f"   Host: {HOST}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vector Search 인덱스 생성 (Knowledge Assistant용)

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()

# ── 2-1. VS 엔드포인트 생성 ──
try:
    ep = vsc.get_endpoint(VS_ENDPOINT_NAME)
    print(f"✅ VS 엔드포인트 이미 존재: {VS_ENDPOINT_NAME} (상태: {ep.get('endpoint_status', {}).get('state', 'UNKNOWN')})")
except Exception:
    print(f"📦 VS 엔드포인트 생성 중: {VS_ENDPOINT_NAME}")
    vsc.create_endpoint(VS_ENDPOINT_NAME, endpoint_type="STANDARD")
    print("   생성 요청 완료 — 프로비저닝에 5~10분 소요됩니다.")

# COMMAND ----------

# ── 2-2. VS 엔드포인트 상태 대기 ──
print(f"⏳ VS 엔드포인트 대기 중: {VS_ENDPOINT_NAME}")
for i in range(60):
    ep = vsc.get_endpoint(VS_ENDPOINT_NAME)
    state = ep.get("endpoint_status", {}).get("state", "UNKNOWN")
    if state == "ONLINE":
        print(f"✅ ONLINE (소요: {i * 10}초)")
        break
    if i % 6 == 0:
        print(f"   [{i * 10:>4}s] {state}")
    time.sleep(10)
else:
    print("⚠️  타임아웃 — 엔드포인트가 아직 프로비저닝 중입니다. 잠시 후 다음 셀을 실행하세요.")

# COMMAND ----------

# ── 2-3. Delta Sync 인덱스 생성 ──
EMBEDDING_MODEL = "databricks-qwen3-embedding-0-6b"

try:
    idx = vsc.get_index(VS_ENDPOINT_NAME, VS_INDEX_NAME)
    status = idx.describe().get("status", {}).get("ready", False)
    print(f"✅ VS 인덱스 이미 존재: {VS_INDEX_NAME} (ready={status})")
except Exception:
    print(f"📦 VS 인덱스 생성 중: {VS_INDEX_NAME}")
    vsc.create_delta_sync_index(
        endpoint_name=VS_ENDPOINT_NAME,
        source_table_name=KB_TABLE,
        index_name=VS_INDEX_NAME,
        pipeline_type="TRIGGERED",
        primary_key="doc_id",
        embedding_source_columns=[{"name": "content", "embedding_model_endpoint_name": EMBEDDING_MODEL}],
        columns_to_sync=["doc_id", "category", "title", "content", "tags"],
    )
    print("   인덱스 생성 요청 완료 — 동기화에 3~5분 소요됩니다.")

# COMMAND ----------

# ── 2-4. 인덱스 동기화 대기 ──
print(f"⏳ 인덱스 동기화 대기 중: {VS_INDEX_NAME}")
for i in range(60):
    try:
        idx = vsc.get_index(VS_ENDPOINT_NAME, VS_INDEX_NAME)
        desc = idx.describe()
        ready = desc.get("status", {}).get("ready", False)
        if ready:
            num_docs = desc.get("status", {}).get("num_rows_indexed", "?")
            print(f"✅ 인덱스 준비 완료! (인덱싱된 문서: {num_docs}개, 소요: {i * 10}초)")
            break
        state = desc.get("status", {}).get("detailed_state", "UNKNOWN")
        if i % 6 == 0:
            print(f"   [{i * 10:>4}s] ready={ready}, state={state}")
    except Exception as e:
        if i % 6 == 0:
            print(f"   [{i * 10:>4}s] 대기 중... ({e})")
    time.sleep(10)
else:
    print("⚠️  타임아웃 — 인덱스가 아직 동기화 중입니다. 잠시 후 다음 셀부터 실행하세요.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Knowledge Assistant 정의

# COMMAND ----------

def knowledge_search(query: str, top_k: int = 3) -> list[dict]:
    """Vector Search로 관련 FAQ 문서를 검색합니다."""
    idx = vsc.get_index(VS_ENDPOINT_NAME, VS_INDEX_NAME)
    results = idx.similarity_search(
        query_text=query,
        columns=["doc_id", "category", "title", "content", "tags"],
        num_results=top_k,
    )
    docs = []
    for row in results.get("result", {}).get("data_array", []):
        docs.append({
            "doc_id": row[0],
            "category": row[1],
            "title": row[2],
            "content": row[3],
            "tags": row[4],
            "score": row[-1],
        })
    return docs


def knowledge_assistant(question: str) -> str:
    """Knowledge Assistant: 검색된 문서 기반으로 답변을 생성합니다."""
    docs = knowledge_search(question)
    if not docs:
        return "죄송합니다. 관련 문서를 찾지 못했습니다."

    context = ""
    for i, doc in enumerate(docs, 1):
        context += f"\n### 참고 문서 {i}: {doc['title']}\n카테고리: {doc['category']}\n{doc['content']}\n"

    messages = [
        {
            "role": "system",
            "content": """당신은 LG Smart TV webOS 전문 어시스턴트입니다.
규칙:
1. 반드시 제공된 지식 문서에 기반하여 답변하세요.
2. 문서에 없는 내용은 '해당 정보를 찾을 수 없습니다'라고 답하세요.
3. 한국어로 답변하되, 기술 용어는 영문 병기 (예: 픽셀 리프레셔(Pixel Refresher))
4. 단계별 가이드가 필요한 경우 번호 매기기를 사용하세요.
5. 관련된 추가 팁이 있으면 '💡 참고' 형태로 추가하세요.
6. 안전 관련 주의사항이 있으면 반드시 언급하세요."""
        },
        {
            "role": "user",
            "content": f"## 참고 문서\n{context}\n\n## 질문\n{question}",
        },
    ]
    return llm_chat(messages)


# 테스트
print("🔍 Knowledge Assistant 테스트:")
test_docs = knowledge_search("OLED 번인 예방")
for d in test_docs:
    print(f"  [{d['score']:.3f}] {d['category']} > {d['title']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Genie Agent 정의

# COMMAND ----------

def genie_query(space_id: str, question: str, timeout: int = 120) -> dict:
    """Genie Space에 질문을 보내고 결과를 반환합니다."""
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    # 1) 대화 시작
    resp = requests.post(
        f"{HOST}/api/2.0/genie/spaces/{space_id}/start-conversation",
        headers=headers,
        json={"content": question},
    )
    resp.raise_for_status()
    data = resp.json()
    conv_id = data["conversation_id"]
    msg_id = data["message_id"]

    # 2) 결과 대기
    for _ in range(timeout // 2):
        time.sleep(2)
        resp = requests.get(
            f"{HOST}/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}",
            headers=headers,
        )
        resp.raise_for_status()
        msg = resp.json()
        status = msg.get("status")
        if status in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
            break
    else:
        return {"status": "TIMEOUT", "answer": "질문 처리 시간이 초과되었습니다."}

    # 3) 결과 추출
    result = {"status": status, "answer": "", "sql": None, "data": None}

    # Genie의 텍스트 응답
    for att in msg.get("attachments", []):
        if att.get("text"):
            result["answer"] += att["text"].get("content", "") + "\n"
        if att.get("query"):
            result["sql"] = att["query"].get("query", "")
            att_id = att.get("id")
            # 쿼리 결과 가져오기
            if att_id:
                try:
                    qr_resp = requests.get(
                        f"{HOST}/api/2.0/genie/spaces/{space_id}/conversations/{conv_id}/messages/{msg_id}/query-result/{att_id}",
                        headers=headers,
                    )
                    if qr_resp.ok:
                        qr = qr_resp.json()
                        columns = [c.get("name") for c in qr.get("statement_response", {}).get("manifest", {}).get("schema", {}).get("columns", [])]
                        rows = qr.get("statement_response", {}).get("result", {}).get("data_array", [])
                        result["data"] = {"columns": columns, "rows": rows[:20]}
                except Exception:
                    pass

    return result


def pick_genie_space(question: str) -> str:
    """질문 키워드 기반으로 적합한 Genie Space를 선택합니다."""
    q_lower = question.lower()
    scores = {}
    for name, cfg in GENIE_SPACES.items():
        score = sum(1 for kw in cfg["keywords"] if kw.lower() in q_lower)
        scores[name] = score

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        # 키워드 매칭이 없으면 LLM으로 판단
        messages = [
            {
                "role": "system",
                "content": f"""다음 세 가지 데이터 분석 카테고리 중 질문에 가장 적합한 것을 선택하세요.
카테고리: 시청분석, 광고분석, 디바이스분석
카테고리 이름만 답하세요."""
            },
            {"role": "user", "content": question},
        ]
        best = llm_chat(messages, temperature=0, max_tokens=10).strip()
        if best not in GENIE_SPACES:
            best = "시청분석"  # 기본값
    return best


def genie_agent(question: str) -> str:
    """Genie Agent: 적합한 Space를 선택하고 데이터를 조회합니다."""
    space_name = pick_genie_space(question)
    space_id = GENIE_SPACES[space_name]["space_id"]
    print(f"  📊 Genie Space 선택: {space_name} ({space_id[:12]}...)")

    result = genie_query(space_id, question)

    # 결과를 텍스트로 포맷팅
    output = ""
    if result.get("answer"):
        output += result["answer"].strip() + "\n"
    if result.get("data"):
        cols = result["data"]["columns"]
        rows = result["data"]["rows"]
        if cols and rows:
            output += "\n| " + " | ".join(cols) + " |\n"
            output += "| " + " | ".join(["---"] * len(cols)) + " |\n"
            for row in rows[:10]:
                output += "| " + " | ".join(str(v) for v in row) + " |\n"
            if len(rows) > 10:
                output += f"\n(총 {len(rows)}행 중 상위 10행 표시)\n"
    if result.get("sql"):
        output += f"\n```sql\n{result['sql']}\n```\n"

    return output if output.strip() else "데이터를 조회했으나 결과가 없습니다."


# 테스트
print("📊 Genie Agent 테스트: Space 선택")
for q in ["이번 주 가장 인기 있는 프로그램은?", "CTR이 높은 광고 형식", "디바이스 에러율"]:
    space = pick_genie_space(q)
    print(f"  Q: {q} → {space}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Supervisor Agent 정의

# COMMAND ----------

SUPERVISOR_SYSTEM_PROMPT = """당신은 LG Smart TV 통합 AI 어시스턴트입니다.

## 라우팅 규칙
사용자 질문의 의도를 파악하여 적절한 에이전트로 라우팅하세요:

### Knowledge Assistant로 보낼 질문:
- "어떻게 ~하나요?", "~하는 방법", "~설정"
- 제품 기능 설명, 트러블슈팅, 사용 가이드
- 예: 'DolbyVision 켜는 법', 'WiFi 끊김 해결', 'OLED 번인 예방'

### Genie Agent (데이터 분석)로 보낼 질문:
- "얼마나", "몇 개", "추이", "비교", "분석"
- 숫자/통계/트렌드가 포함된 질문
- 예: '이번 주 시청 시간', '가장 인기 있는 앱', '에러율 추이'

### 두 에이전트 모두 필요한 질문:
- 데이터 + 가이드가 함께 필요한 경우
- 예: 'Netflix 4K가 재생 안 되는 디바이스가 많은데, 해결 방법은?'
  → 먼저 Genie: Netflix 관련 에러 통계 조회
  → 그 다음 KA: Netflix 4K 재생 조건 및 트러블슈팅 가이드

## 답변 규칙
1. 에이전트 라우팅 결정을 사용자에게 노출하지 마세요
2. 여러 에이전트의 답변은 자연스럽게 통합하여 하나의 답변으로 제공
3. 한국어로 답변하되, 기술 용어는 영문 병기
4. 답변 끝에 '🔍 관련 질문'으로 후속 질문 2~3개 제안"""


ROUTER_PROMPT = """사용자 질문을 분석하여 어떤 에이전트를 사용할지 결정하세요.

선택지:
- "KA" : 사용법, 설정, 트러블슈팅 등 가이드 질문
- "GENIE" : 데이터 조회, 통계, 트렌드 분석 질문
- "BOTH" : 데이터 분석 + 가이드가 함께 필요한 질문

반드시 KA, GENIE, BOTH 중 하나만 답하세요."""


class SupervisorAgent:
    """LG Smart TV 통합 AI 어시스턴트 — Supervisor Agent"""

    def __init__(self):
        self.name = "LG Smart TV AI 어시스턴트"
        self.description = "Smart TV에 관한 모든 질문에 답변하는 통합 AI 어시스턴트입니다. 사용 가이드, 데이터 분석, 트러블슈팅을 지원합니다."

    def route(self, question: str) -> str:
        """질문 의도를 분류합니다."""
        messages = [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": question},
        ]
        decision = llm_chat(messages, temperature=0, max_tokens=10).strip().upper()
        # 파싱 보정
        if "BOTH" in decision:
            return "BOTH"
        elif "GENIE" in decision:
            return "GENIE"
        else:
            return "KA"

    def ask(self, question: str) -> str:
        """사용자 질문에 답변합니다."""
        route = self.route(question)
        print(f"🧭 라우팅: {route}")

        ka_result = None
        genie_result = None

        # ── 에이전트 호출 ──
        if route in ("KA", "BOTH"):
            print("  📚 Knowledge Assistant 호출 중...")
            ka_result = knowledge_assistant(question)

        if route in ("GENIE", "BOTH"):
            print("  📊 Genie Agent 호출 중...")
            genie_result = genie_agent(question)

        # ── 단일 에이전트 결과 ──
        if route == "KA" and ka_result:
            answer = ka_result
        elif route == "GENIE" and genie_result:
            answer = genie_result
        else:
            # ── 복합 결과 통합 ──
            synthesis_prompt = f"""다음 두 에이전트의 결과를 자연스럽게 통합하여 하나의 답변으로 만드세요.

## 데이터 분석 결과 (Genie Agent)
{genie_result or '(결과 없음)'}

## 가이드 정보 (Knowledge Assistant)
{ka_result or '(결과 없음)'}

## 사용자 질문
{question}

규칙:
- 데이터 결과를 먼저 제시하고 그에 대한 가이드/해결책을 이어서 설명
- 에이전트 이름이나 라우팅 과정을 노출하지 마세요
- 한국어로 답변, 기술 용어는 영문 병기"""

            messages = [
                {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
                {"role": "user", "content": synthesis_prompt},
            ]
            answer = llm_chat(messages)

        # ── 후속 질문 추가 ──
        if "🔍 관련 질문" not in answer:
            followup = llm_chat(
                [
                    {"role": "system", "content": "사용자의 질문과 답변을 보고, 후속으로 물어볼 만한 관련 질문 3개를 제안하세요. '🔍 관련 질문' 헤더와 함께 간결하게 작성하세요."},
                    {"role": "user", "content": f"질문: {question}\n답변 요약: {answer[:500]}"},
                ],
                temperature=0.5,
                max_tokens=200,
            )
            answer += "\n\n" + followup

        return answer


agent = SupervisorAgent()
print(f"✅ {agent.name} 초기화 완료")
print(f"   설명: {agent.description}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. 테스트

# COMMAND ----------

# MAGIC %md
# MAGIC ### 테스트 1: Knowledge Assistant 라우팅

# COMMAND ----------

q1 = "OLED TV 번인을 예방하려면 어떻게 해야 하나요?"
print(f"💬 질문: {q1}\n")
print(agent.ask(q1))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 테스트 2: Genie Agent 라우팅

# COMMAND ----------

q2 = "최근 7일간 가장 많이 시청된 프로그램 Top 5는?"
print(f"💬 질문: {q2}\n")
print(agent.ask(q2))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 테스트 3: 복합 라우팅 (BOTH)

# COMMAND ----------

q3 = "Wi-Fi 연결 에러가 많이 발생하는 디바이스의 특징과 해결 방법은?"
print(f"💬 질문: {q3}\n")
print(agent.ask(q3))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. 인터랙티브 채팅

# COMMAND ----------

def chat(question: str):
    """간편 채팅 함수"""
    print(f"💬 {question}\n")
    print("─" * 60)
    print(agent.ask(question))
    print("─" * 60)

# 사용법: chat("질문을 입력하세요")
chat("블루투스 이어폰 연결이 자꾸 끊어지는데 어떻게 해결하나요?")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. MLflow 모델 등록 (선택)

# COMMAND ----------

import mlflow
from mlflow.pyfunc import ChatModel
from mlflow.types.llm import (
    ChatMessage,
    ChatParams,
    ChatResponse,
    ChatChoice,
)


class SupervisorChatModel(ChatModel):
    """MLflow ChatModel 인터페이스로 래핑한 Supervisor Agent"""

    def load_context(self, context):
        # 모델 로드 시 초기화 (서빙 환경에서 호출)
        pass

    def predict(self, context, messages: list[ChatMessage], params: ChatParams) -> ChatResponse:
        # 마지막 사용자 메시지 추출
        user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                user_msg = m.content
                break

        if not user_msg:
            answer = "질문을 입력해주세요."
        else:
            answer = agent.ask(user_msg)

        return ChatResponse(
            choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content=answer))]
        )


# 모델 등록 (필요 시 주석 해제)
# with mlflow.start_run(run_name="smarttv_supervisor_agent"):
#     model_info = mlflow.pyfunc.log_model(
#         artifact_path="supervisor_agent",
#         python_model=SupervisorChatModel(),
#         registered_model_name=f"{CATALOG}.{SCHEMA}.smarttv_supervisor_agent",
#     )
#     print(f"✅ 모델 등록 완료: {model_info.model_uri}")
