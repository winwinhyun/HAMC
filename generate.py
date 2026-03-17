"""
generate.py — 2단계 파이프라인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1단계: web_search 툴로 최신 뉴스 수집 + 자유 형식 심층 분석 리포트 작성
         (Claude가 검색 결과를 충분히 소화하고 길게 분석)
2단계: 1단계 리포트를 입력으로 받아 JSON 구조화
         (검색 없이 순수 구조화만 담당 → 파싱 안정성 ↑)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import json
import re
import urllib.request
import os
import time
from datetime import datetime, timezone, timedelta, date

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
DATE_ONLY   = now.strftime("%Y년 %m월 %d일")
TIMESTAMP   = now.strftime("%Y년 %m월 %d일 %H시 %M분")

today      = date.today()
month_ago  = today - timedelta(days=30)
SEARCH_PERIOD = (
    f"{month_ago.strftime('%Y년 %m월 %d일')} ~ {today.strftime('%Y년 %m월 %d일')}"
)

# ── 제품 컨텍스트 (두 단계 공통) ──────────────────
PRODUCT_CONTEXT = """
Hanwha Advanced Materials product lines (internal reference only):
- StrongLite(GMT): Glass fiber Mat reinforced Thermoplastics. World #1 market share.
  Applications: front/rear bumper beams, battery trays, seat backs, underbody covers.
- SuperLite(LWRT): Light Weight Reinforced Thermoplastics. World #1 market share.
  Applications: underbody panels, headliners, door trims, wheel guards, luggage boards.
- BuffLite(EPP): Expanded Polypropylene foam.
  Applications: bumper energy absorbers, sound insulation, EMI/electromagnetic shielding.
- IntermLite(PMC): Powder Slush Molding Compound + TPO/PVC interior sheets.
  Applications: instrument panels, door trims, seat covers (luxury sedans).
- SMC: Sheet Molding Compound (thermosetting).
  Applications: exterior body panels, battery pack cases, pickup truck beds, EV front trunks.
- Solar Materials: EVA/POE Encapsulant + Backsheet for PV modules.
  Production capacity: 9GW/year. Key customer: Hanwha Q CELLS.
Key competitors: Toray, Hexcel, SGL Carbon (composites); Hangzhou First Applied Material, Cybrid Technologies (solar).
Annual revenue: KRW 1.2308 trillion (2024). Overseas revenue ratio: 61%. 8 overseas production sites.
"""

# ── web_search 툴 정의 ──────────────────────────
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 8   # 1단계에서 충분히 검색
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1단계 시스템 프롬프트 — 검색 + 자유 형식 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM_STAGE1 = f"""You are a senior market intelligence analyst for Hanwha Advanced Materials.
{PRODUCT_CONTEXT}

YOUR TASK:
1. Use web_search to gather REAL, RECENT news from the past 30 days.
2. Search comprehensively — search at least 5-6 times covering different angles.
3. After all searches, write a detailed FREE-FORM analysis report in Korean.

REPORT FORMAT (free-form, write in Korean):
- 분석 기간: {SEARCH_PERIOD}
- Executive Summary (3-4 sentences with specific facts/numbers found)
- 주요 발견사항 (at least 6 detailed findings, each 3-5 sentences):
  * Each finding must cite specific company names, numbers, dates from actual search results
  * Include implications for Hanwha Advanced Materials products
- 경쟁사 동향 (3-4 paragraphs on competitor moves)
- 중단기 사업 전망:
  * 단기 (6개월): specific outlook based on found data
  * 중기 (2년): trend projection
  * 장기 (5년): strategic outlook
- 액션 아이템:
  * 영업팀: concrete sales actions
  * R&D팀: specific research directions
  * 경영진: strategic decisions needed
- 검색한 주요 출처 목록

DO NOT write JSON. Write a rich, detailed analytical report.
The more specific facts, numbers, and company names from search results, the better."""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2단계 시스템 프롬프트 — JSON 구조화 전용
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM_STAGE2 = """You are a JSON formatter. Convert the provided analysis report into structured JSON.

STRICT OUTPUT RULES:
- Output ONLY valid JSON — no markdown, no code blocks, no preamble
- NO newlines or tab characters inside any string value
- Use "; " (semicolon + space) to separate sentences within a string
- Preserve specific facts, numbers, company names, and dates from the report
- sections must have exactly 8 items
- Each section content must be 3-5 sentences (rich detail)
- actions.sales / rd / management must be 3-4 sentences each (concrete, specific)
- timeline entries must be 4-5 sentences each (data-driven)
- product_impact: assess impact level for each product based on the report content.
  Keys: "StrongLite (GMT)", "SuperLite (LWRT)", "BuffLite (EPP)", "IntermLite (PMC)", "SMC", "Encapsulant (EVA/POE)"
  Values: "HIGH", "MEDIUM", "LOW", or "NONE"
  Be specific — not all products are affected equally by every topic."""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 토픽별 검색 지시 및 JSON 스키마
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPICS = {
    "weekly": {
        "label": "주간 종합",
        "stage1_instruction": f"""Today is {DATE_ONLY}. Analyze global automotive & EV industry trends for the past 30 days.

Search for these topics (search each separately for best coverage):
1. Global EV sales data and market share changes this month
2. Major OEM announcements — Hyundai/Kia, Toyota, BMW, GM, Tesla, BYD
3. Automotive lightweight composite material demand trends
4. US/EU/China automotive policy changes
5. EV battery and platform technology news
6. Automotive supply chain and raw material price trends

Write a comprehensive analysis report as instructed.""",
        "json_schema": """{"summary":"[3-4 sentence Korean summary with specific facts/numbers]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":90,"has_ai_inference":false,"note":"[실제 검색 출처 나열]"},"data_sources":[{"name":"[source]","type":"market"},{"name":"[source]","type":"regulatory"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentence Korean content with specific facts]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"market"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","SMC","BuffLite (EPP)"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentence concrete sales actions in Korean]","rd":"[3-4 sentence specific R&D directions in Korean]","management":"[3-4 sentence strategic decisions in Korean]"},"timeline":{"short":"[4-5 sentence 6-month outlook in Korean with specific data]","mid":"[4-5 sentence 2-year outlook in Korean]","long":"[4-5 sentence 5-year outlook in Korean]"}}"""
    },
    "ev": {
        "label": "EV / 정책",
        "stage1_instruction": f"""Today is {DATE_ONLY}. Analyze global EV market and policy landscape for the past 30 days.

Search for these topics separately:
1. US IRA EV tax credits — latest updates, changes, beneficiary companies
2. EU CO2 emission targets 2025 — automaker fines, compliance status
3. China NEV policy — subsidies, sales mandates, BYD/CATL developments
4. Global EV sales figures — monthly data, market share by brand/region
5. EV charging infrastructure expansion news
6. EV battery technology and cost reduction news

Write a comprehensive analysis report as instructed.""",
        "json_schema": """{"summary":"[3-4 sentence Korean summary with specific policy facts/numbers]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":92,"has_ai_inference":false,"note":"[실제 검색 출처 나열]"},"data_sources":[{"name":"[source]","type":"regulatory"},{"name":"[source]","type":"market"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentence Korean content with specific policy details/numbers]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"regulatory"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)","SMC"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentence concrete sales actions]","rd":"[3-4 sentence R&D directions]","management":"[3-4 sentence strategic decisions]"},"timeline":{"short":"[4-5 sentence 6-month outlook based on real policy data]","mid":"[4-5 sentence 2-year outlook]","long":"[4-5 sentence 5-year outlook]"}}"""
    },
    "oem": {
        "label": "OEM 동향",
        "stage1_instruction": f"""Today is {DATE_ONLY}. Analyze major OEM automotive developments for the past 30 days.

Search for these topics separately:
1. Hyundai/Kia — new EV models, production plans, material announcements
2. Tesla — production numbers, new model updates, cost reduction moves
3. BYD — sales records, overseas expansion, new platform
4. BMW/Mercedes/Volkswagen — EV transition progress, material decisions
5. GM/Ford/Stellantis — EV strategy updates, plant investments
6. Toyota — hybrid vs EV strategy, new model announcements
7. Automotive lightweight material adoption by OEMs

Write a comprehensive analysis report as instructed.""",
        "json_schema": """{"summary":"[3-4 sentence Korean summary with specific OEM names/models/facts]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":89,"has_ai_inference":false,"note":"[실제 검색 출처 나열]"},"data_sources":[{"name":"[source]","type":"official"},{"name":"[source]","type":"market"},{"name":"[source]","type":"market"}],"sections":[{"title":"[제목]","content":"[3-5 sentence Korean content with specific model names and facts]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","IntermLite (PMC)","SMC","BuffLite (EPP)"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentence concrete OEM-specific sales actions]","rd":"[3-4 sentence R&D directions based on OEM needs]","management":"[3-4 sentence strategic partnership decisions]"},"timeline":{"short":"[4-5 sentence 6-month outlook by OEM]","mid":"[4-5 sentence 2-year platform transition outlook]","long":"[4-5 sentence 5-year OEM landscape outlook]"}}"""
    },
    "materials": {
        "label": "소재 기술",
        "stage1_instruction": f"""Today is {DATE_ONLY}. Analyze automotive lightweight composite material trends for the past 30 days.

Search for these topics separately:
1. CFRP carbon fiber composite material — market size, price, demand news
2. Toray Industries — latest announcements, new products, automotive contracts
3. Hexcel Corporation — recent news, aerospace/automotive developments
4. SGL Carbon — new developments, EV battery material news
5. Thermoplastic composite materials — new applications, technology advances
6. EV battery enclosure / housing material trends
7. Recycled composite materials — sustainability regulations, GRS certification trends

Write a comprehensive analysis report as instructed.""",
        "json_schema": """{"summary":"[3-4 sentence Korean summary with specific material technology facts]","impact_score":"MEDIUM","analysis_period":"PERIOD","accuracy_summary":{"overall_score":86,"has_ai_inference":false,"note":"[실제 검색 출처 나열]"},"data_sources":[{"name":"[source]","type":"market"},{"name":"[source]","type":"market"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentence Korean content with specific technology facts]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content about specific competitor]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content about another competitor]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"EV동향","accuracy_level":"MEDIUM","source_type":"market"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)","SMC"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentence concrete sales actions citing competitor weaknesses]","rd":"[3-4 sentence specific technology R&D priorities]","management":"[3-4 sentence strategic positioning decisions]"},"timeline":{"short":"[4-5 sentence 6-month material market outlook]","mid":"[4-5 sentence 2-year technology transition outlook]","long":"[4-5 sentence 5-year material paradigm outlook]"}}"""
    },
    "solar": {
        "label": "태양광 소재",
        "stage1_instruction": f"""Today is {DATE_ONLY}. Analyze solar PV materials market for the past 30 days.

Search for these topics separately:
1. Solar PV encapsulant EVA POE market — pricing, demand, capacity news
2. Hanwha Q CELLS — latest news, production, US factory updates
3. US IRA solar manufacturing tax credits — latest updates, beneficiaries
4. China solar supply chain — overcapacity, pricing, export restrictions
5. Floating solar market — growth, new projects, material requirements
6. Solar backsheet market — demand trends, new materials
7. Global solar installation forecast 2025 — key markets, growth rates

Write a comprehensive analysis report as instructed.""",
        "json_schema": """{"summary":"[3-4 sentence Korean summary with specific solar market facts/numbers]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":90,"has_ai_inference":false,"note":"[실제 검색 출처 나열]"},"data_sources":[{"name":"[source]","type":"market"},{"name":"[source]","type":"regulatory"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentence Korean content with specific solar market numbers]","tag":"태양광시장","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content about Hanwha Q CELLS or key customer]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"태양광시장","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"}],"products_affected":["Encapsulant (EVA/POE)","Backsheet","태양광 소재 사업부"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentence concrete solar sales actions]","rd":"[3-4 sentence solar material R&D directions]","management":"[3-4 sentence strategic solar business decisions]"},"timeline":{"short":"[4-5 sentence 6-month solar market outlook]","mid":"[4-5 sentence 2-year solar growth outlook]","long":"[4-5 sentence 5-year solar material technology outlook]"}}"""
    }
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 공통 유틸
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def api_request(payload):
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_tool_loop(system, messages, tools=None, max_tokens=8000, max_loops=12):
    """tool_use 루프 실행 → 최종 text 반환"""
    search_count = 0
    for loop in range(max_loops):
        payload = {
            "model": "claude-sonnet-4-5",
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        body    = api_request(payload)
        stop    = body.get("stop_reason", "")
        blocks  = body.get("content", [])

        for b in blocks:
            if b.get("type") == "tool_use" and b.get("name") == "web_search":
                search_count += 1
                print(f"    🔍 검색 {search_count}: {b.get('input',{}).get('query','')}")

        if stop == "end_turn":
            text = "".join(b.get("text","") for b in blocks if b.get("type")=="text")
            return text, search_count

        elif stop == "tool_use":
            messages.append({"role": "assistant", "content": blocks})
            tool_results = [
                {"type": "tool_result", "tool_use_id": b["id"], "content": ""}
                for b in blocks if b.get("type") == "tool_use"
            ]
            messages.append({"role": "user", "content": tool_results})

        elif stop == "max_tokens":
            text = "".join(b.get("text","") for b in blocks if b.get("type")=="text")
            return text, search_count

        else:
            raise RuntimeError(f"Unexpected stop_reason: {stop}")

    raise RuntimeError("max_loops exceeded")


def fix_and_parse(text):
    """JSON 추출 + 파싱"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    s = text.find('{')
    e = text.rfind('}')
    if s == -1 or e == -1:
        return None
    text = text[s:e+1]

    out, in_str, esc = [], False, False
    for ch in text:
        if esc:
            out.append(ch); esc = False
        elif ch == '\\':
            out.append(ch); esc = True
        elif ch == '"':
            in_str = not in_str; out.append(ch)
        elif in_str and ch in '\n\r\t':
            out.append(' ')
        else:
            out.append(ch)

    try:
        return json.loads(''.join(out))
    except json.JSONDecodeError as e:
        print(f"  파싱 오류: {e}")
        return None


def make_error(msg):
    return {
        "error": msg,
        "generated_at": TIMESTAMP,
        "summary": "분석 데이터 생성 실패 - 다음 갱신 시 자동 복구됩니다.",
        "impact_score": "MEDIUM",
        "analysis_period": SEARCH_PERIOD,
        "accuracy_summary": {"overall_score": 0, "has_ai_inference": True, "note": "오류"},
        "data_sources": [],
        "sections": [],
        "products_affected": [],
        "actions": {"sales": "", "rd": "", "management": ""},
        "timeline": {"short": "", "mid": "", "long": ""}
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 2단계 파이프라인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_topic(topic_id, topic_data):
    print(f"\n{'='*50}")
    print(f"▶ [{topic_id}] {topic_data['label']} 분석 시작")
    print(f"{'='*50}")

    # ── 1단계: 검색 + 자유 형식 심층 분석 ──────────
    print("  [1단계] 웹 검색 + 심층 분석 리포트 작성...")
    try:
        report_text, search_count = run_tool_loop(
            system=SYSTEM_STAGE1,
            messages=[{"role": "user", "content": topic_data['stage1_instruction']}],
            tools=[WEB_SEARCH_TOOL],
            max_tokens=8000,
            max_loops=15
        )
    except Exception as e:
        print(f"  ✗ 1단계 오류: {e}")
        return make_error(f"stage1: {e}")

    print(f"  ✓ 1단계 완료 — 검색 {search_count}회, 리포트 {len(report_text)}자")

    if not report_text.strip():
        return make_error("stage1_empty_report")

    # ── 2단계: 리포트 → JSON 구조화 ─────────────
    print("  [2단계] JSON 구조화 중...")

    schema = topic_data['json_schema'].replace("PERIOD", SEARCH_PERIOD)

    stage2_prompt = f"""아래는 한화첨단소재 시장 인텔리전스 분석 리포트입니다.
이 리포트의 내용을 바탕으로 JSON을 생성하세요.
리포트에 있는 구체적인 수치, 회사명, 날짜, 사실을 최대한 JSON에 반영하세요.

=== 분석 리포트 ===
{report_text}
===================

위 리포트를 아래 JSON 스키마에 맞게 변환하세요.
각 sections의 content는 3-5문장으로 구체적 사실을 포함하세요.
actions와 timeline도 리포트의 실제 내용을 기반으로 상세하게 작성하세요.

JSON 스키마:
{schema}"""

    try:
        json_text, _ = run_tool_loop(
            system=SYSTEM_STAGE2,
            messages=[{"role": "user", "content": stage2_prompt}],
            tools=None,       # 2단계는 검색 없음 — 순수 구조화만
            max_tokens=6000,
            max_loops=3
        )
    except Exception as e:
        print(f"  ✗ 2단계 오류: {e}")
        return make_error(f"stage2: {e}")

    result = fix_and_parse(json_text)
    if not result:
        print(f"  ⚠ 2단계 파싱 실패, 원문: {json_text[:300]}")
        return make_error("stage2_parse_failed")

    result["generated_at"]  = TIMESTAMP
    result["search_powered"] = True
    result["search_count"]  = search_count
    print(f"  ✓ 완료 — sections {len(result.get('sections',[]))}개")
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
os.makedirs("data", exist_ok=True)

items = list(TOPICS.items())
for i, (topic_id, topic_data) in enumerate(items):
    result    = generate_topic(topic_id, topic_data)
    out_path  = f"data/{topic_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {out_path} 저장")

    if i < len(items) - 1:
        wait = 25
        print(f"  ⏳ {wait}초 대기 (rate limit)...")
        time.sleep(wait)

print("\n✅ 전체 완료")
