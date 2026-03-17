"""
generate.py — 2단계 파이프라인 (공식 문서 기반 재작성)

핵심 변경:
- web_search는 단일 API 호출로 자동 처리됨 (루프 불필요)
- 1단계: 검색 포함 단일 호출 → 분석 리포트
- 2단계: 리포트 → JSON 구조화 (검색 없음)
"""
import json
import re
import urllib.request
import urllib.error
import os
import time
from datetime import datetime, timezone, timedelta, date

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

KST       = timezone(timedelta(hours=9))
now       = datetime.now(KST)
DATE_ONLY = now.strftime("%Y년 %m월 %d일")
TIMESTAMP = now.strftime("%Y년 %m월 %d일 %H시 %M분")

today = date.today()

def make_period(days):
    start = today - timedelta(days=days)
    return f"{start.strftime('%Y년 %m월 %d일')} ~ {today.strftime('%Y년 %m월 %d일')}"

PERIODS = {
    "weekly":    make_period(7),
    "ev":        make_period(30),
    "oem":       make_period(30),
    "materials": make_period(60),
    "solar":     make_period(30),
}
SEARCH_PERIOD = make_period(30)

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
Key competitors: Toray, Hexcel, SGL Carbon; Hangzhou First Applied Material, Cybrid Technologies (solar).
Annual revenue: KRW 1.2308 trillion (2024). Overseas revenue ratio: 61%. 8 overseas sites.
"""

# 최신 web_search 툴 (Sonnet 4.6 지원, 동적 필터링으로 토큰 절약)
WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search"
    # max_uses 미설정 시 기본값 사용 (동적 필터링 버전은 max_uses 불필요)
}

SYSTEM_STAGE1 = f"""You are a senior market intelligence analyst for Hanwha Advanced Materials.
{PRODUCT_CONTEXT}

Use web_search to find recent news, then write a concise Korean analysis report.

REPORT FORMAT (Korean, max 1200 words):
1. Executive Summary (3-4 sentences with key facts/numbers from search)
2. 주요 발견사항 (5-6 findings, 2-3 sentences each, cite specific facts)
3. 경쟁사 동향 (2-3 paragraphs)
4. 전망 및 액션 아이템 (단기/중기/장기 + 영업팀/R&D팀/경영진)
5. 주요 출처

Do NOT write JSON. Write Korean report only."""

SYSTEM_STAGE2 = """You are a JSON formatter. Convert the analysis report into structured JSON.

STRICT RULES:
- Output ONLY valid JSON — no markdown, no code blocks, no preamble
- NO newlines or tabs inside string values — use "; " to separate sentences
- summary: 5-6 sentences (comprehensive with key facts and numbers)
- sections: exactly 8 items, each content 3-5 sentences
- actions.sales/rd/management: 3-4 sentences each
- timeline.short/mid/long: 4-5 sentences each
- product_impact keys: "StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)","IntermLite (PMC)","SMC","Encapsulant (EVA/POE)"
- product_impact values: "HIGH","MEDIUM","LOW","NONE" — be specific per topic"""

TOPICS = {
    "weekly": {
        "label": "주간 종합",
        "prompt": f"""Today is {DATE_ONLY}. Search for global automotive & EV industry news from the past 7 days ({PERIODS['weekly']}).
Search for: EV sales, OEM announcements (Hyundai/Kia/BMW/GM/Tesla/BYD), lightweight material trends, automotive policy changes.
Write analysis report as instructed.""",
        "schema": """{"summary":"[5-6 sentence Korean summary]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":88,"has_ai_inference":false,"note":"[출처 나열]"},"data_sources":[{"name":"[source]","type":"market"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentences Korean]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"market"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","SMC","BuffLite (EPP)"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentences Korean]","rd":"[3-4 sentences Korean]","management":"[3-4 sentences Korean]"},"timeline":{"short":"[4-5 sentences Korean]","mid":"[4-5 sentences Korean]","long":"[4-5 sentences Korean]"}}"""
    },
    "ev": {
        "label": "EV / 정책",
        "prompt": f"""Today is {DATE_ONLY}. Search for EV market and policy news from the past 30 days ({PERIODS['ev']}).
Search for: US IRA EV credits, EU CO2 regulations, China NEV policy, global EV sales figures, battery technology.
Write analysis report as instructed.""",
        "schema": """{"summary":"[5-6 sentence Korean summary with policy facts]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":90,"has_ai_inference":false,"note":"[출처 나열]"},"data_sources":[{"name":"[source]","type":"regulatory"},{"name":"[source]","type":"market"}],"sections":[{"title":"[제목]","content":"[3-5 sentences Korean]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"regulatory"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)","SMC"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentences]","rd":"[3-4 sentences]","management":"[3-4 sentences]"},"timeline":{"short":"[4-5 sentences]","mid":"[4-5 sentences]","long":"[4-5 sentences]"}}"""
    },
    "oem": {
        "label": "OEM 동향",
        "prompt": f"""Today is {DATE_ONLY}. Search for major OEM automotive news from the past 30 days ({PERIODS['oem']}).
Search for: Hyundai/Kia new EVs, Tesla production, BYD expansion, BMW/GM/Toyota strategy, lightweight material adoption.
Write analysis report as instructed.""",
        "schema": """{"summary":"[5-6 sentence Korean summary with OEM facts]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":87,"has_ai_inference":false,"note":"[출처 나열]"},"data_sources":[{"name":"[source]","type":"official"},{"name":"[source]","type":"market"}],"sections":[{"title":"[제목]","content":"[3-5 sentences Korean]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","IntermLite (PMC)","SMC","BuffLite (EPP)"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"MEDIUM","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentences]","rd":"[3-4 sentences]","management":"[3-4 sentences]"},"timeline":{"short":"[4-5 sentences]","mid":"[4-5 sentences]","long":"[4-5 sentences]"}}"""
    },
    "materials": {
        "label": "소재 기술",
        "prompt": f"""Today is {DATE_ONLY}. Search for lightweight composite material news from the past 60 days ({PERIODS['materials']}).
Search for: CFRP/carbon fiber market, Toray news, Hexcel news, SGL Carbon news, EV battery housing materials, recycled composites.
Write analysis report as instructed.""",
        "schema": """{"summary":"[5-6 sentence Korean summary with material facts]","impact_score":"MEDIUM","analysis_period":"PERIOD","accuracy_summary":{"overall_score":85,"has_ai_inference":false,"note":"[출처 나열]"},"data_sources":[{"name":"[source]","type":"market"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentences Korean]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content about Toray]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content about Hexcel or SGL]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"regulatory"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"EV동향","accuracy_level":"MEDIUM","source_type":"market"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)","SMC"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"HIGH","BuffLite (EPP)":"MEDIUM","IntermLite (PMC)":"LOW","SMC":"HIGH","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"[3-4 sentences]","rd":"[3-4 sentences]","management":"[3-4 sentences]"},"timeline":{"short":"[4-5 sentences]","mid":"[4-5 sentences]","long":"[4-5 sentences]"}}"""
    },
    "solar": {
        "label": "태양광 소재",
        "prompt": f"""Today is {DATE_ONLY}. Search for solar PV materials market news from the past 30 days ({PERIODS['solar']}).
Search for: EVA/POE encapsulant market, Hanwha Q CELLS news, US IRA solar credits, China solar supply chain, floating solar, backsheet market.
Write analysis report as instructed.""",
        "schema": """{"summary":"[5-6 sentence Korean summary with solar market facts]","impact_score":"HIGH","analysis_period":"PERIOD","accuracy_summary":{"overall_score":88,"has_ai_inference":false,"note":"[출처 나열]"},"data_sources":[{"name":"[source]","type":"market"},{"name":"[source]","type":"regulatory"},{"name":"[source]","type":"official"}],"sections":[{"title":"[제목]","content":"[3-5 sentences Korean]","tag":"태양광시장","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[제목]","content":"[content about Hanwha Q CELLS]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[제목]","content":"[content]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"태양광시장","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[제목]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[제목]","content":"[content]","tag":"리스크","accuracy_level":"MEDIUM","source_type":"ai"}],"products_affected":["Encapsulant (EVA/POE)","Backsheet","태양광 소재 사업부"],"product_impact":{"StrongLite (GMT)":"NONE","SuperLite (LWRT)":"NONE","BuffLite (EPP)":"NONE","IntermLite (PMC)":"NONE","SMC":"LOW","Encapsulant (EVA/POE)":"HIGH"},"actions":{"sales":"[3-4 sentences]","rd":"[3-4 sentences]","management":"[3-4 sentences]"},"timeline":{"short":"[4-5 sentences]","mid":"[4-5 sentences]","long":"[4-5 sentences]"}}"""
    }
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API 호출
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def call_api(payload, max_retries=3):
    """단순 1회 API 호출 + 429 재시도"""
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(max_retries):
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
            except Exception:
                pass
            if e.code == 429:
                wait = 60 * (attempt + 1)
                print(f"  ⚠ 429 Rate limit — {wait}초 대기 후 재시도...")
                time.sleep(wait)
                if attempt == max_retries - 1:
                    raise RuntimeError(f"429: {body}")
            else:
                raise RuntimeError(f"HTTP {e.code}: {body}")
    raise RuntimeError("max_retries exceeded")


def fix_and_parse(text):
    """JSON 추출 + 파싱 + 자동 복구"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text).strip()
    s, e = text.find('{'), text.rfind('}')
    if s == -1 or e == -1:
        return None
    text = text[s:e+1]

    # 문자열 내 줄바꿈·제어문자 제거
    out, in_str, esc = [], False, False
    for ch in text:
        if esc:
            out.append(ch); esc = False
        elif ch == '\\':
            out.append(ch); esc = True
        elif ch == '"':
            in_str = not in_str; out.append(ch)
        elif in_str and (ch in '\n\r\t' or ord(ch) < 32):
            out.append(' ')
        else:
            out.append(ch)

    fixed = ''.join(out)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as err1:
        print(f"  1차 파싱 실패: {err1}")
        # 괄호 복구 시도
        try:
            opens  = fixed.count('{') - fixed.count('}')
            closes = fixed.count('[') - fixed.count(']')
            repaired = fixed + (']' * max(0, closes)) + ('}' * max(0, opens))
            result = json.loads(repaired)
            print(f"  괄호 복구 성공")
            return result
        except json.JSONDecodeError as err2:
            print(f"  2차 복구 실패: {err2}")
            return None


def make_error(msg, period=None):
    return {
        "error": msg,
        "generated_at": TIMESTAMP,
        "summary": "분석 데이터 생성 실패 - 다음 갱신 시 자동 복구됩니다.",
        "impact_score": "MEDIUM",
        "analysis_period": period or SEARCH_PERIOD,
        "accuracy_summary": {"overall_score": 0, "has_ai_inference": True, "note": "오류"},
        "data_sources": [],
        "sections": [],
        "products_affected": [],
        "actions": {"sales": "", "rd": "", "management": ""},
        "timeline": {"short": "", "mid": "", "long": ""}
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2단계 파이프라인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_topic(topic_id, topic_data):
    period = PERIODS[topic_id]
    print(f"\n{'='*52}")
    print(f"▶ [{topic_id}] {topic_data['label']}  |  {period}")
    print(f"{'='*52}")

    # ── 1단계: web_search 포함 단일 호출 ────────────
    # web_search 툴은 단일 호출에서 자동으로 다중 검색 수행
    print("  [1단계] 검색 + 분석 리포트 작성...")
    report_text = ""
    for attempt in range(2):
        try:
            body = call_api({
                "model": "claude-sonnet-4-6",
                "max_tokens": 4000,
                "system": SYSTEM_STAGE1,
                "tools": [WEB_SEARCH_TOOL],
                "messages": [{"role": "user", "content": topic_data['prompt']}]
            })
            # web_search는 end_turn으로 완료, content에서 text 추출
            report_text = "".join(
                b.get("text", "") for b in body.get("content", [])
                if b.get("type") == "text"
            )
            if report_text.strip():
                print(f"  ✓ 리포트 {len(report_text)}자 생성")
                break
            else:
                print(f"  ⚠ 빈 응답 (시도 {attempt+1})")
        except RuntimeError as e:
            print(f"  ✗ 1단계 오류 (시도 {attempt+1}): {e}")
            if attempt == 1:
                return make_error(str(e), period)
            time.sleep(30)

    if not report_text.strip():
        return make_error("empty_report", period)

    # ── 2단계: JSON 구조화 (검색 없이 순수 변환) ────
    print("  [2단계] JSON 구조화 중...")
    schema = topic_data['schema'].replace("PERIOD", period)
    report_trimmed = report_text[:3000] if len(report_text) > 3000 else report_text

    prompt2 = f"""한화첨단소재 인텔리전스 리포트를 JSON으로 변환하세요.
analysis_period: "{period}"
리포트의 수치·회사명·사실을 JSON에 반영하세요. 완전한 JSON만 출력하세요.

=== 리포트 ===
{report_trimmed}
==============

JSON 스키마:
{schema}"""

    result = None
    for attempt in range(2):
        try:
            body = call_api({
                "model": "claude-sonnet-4-6",
                "max_tokens": 6000,
                "system": SYSTEM_STAGE2,
                "messages": [{"role": "user", "content": prompt2}]
                # tools 없음 — 순수 JSON 생성만
            })
            json_text = "".join(
                b.get("text", "") for b in body.get("content", [])
                if b.get("type") == "text"
            )
        except RuntimeError as e:
            print(f"  ✗ 2단계 오류 (시도 {attempt+1}): {e}")
            if attempt == 1:
                return make_error(str(e), period)
            time.sleep(20)
            continue

        result = fix_and_parse(json_text)
        if result:
            break
        print(f"  ⚠ 파싱 실패 (시도 {attempt+1}), 앞부분: {json_text[:150]}")
        if attempt == 0:
            time.sleep(10)

    if not result:
        return make_error("parse_failed", period)

    result["generated_at"]    = TIMESTAMP
    result["search_powered"]  = True
    result["analysis_period"] = period  # 강제 보정
    print(f"  ✓ 완료 — sections {len(result.get('sections', []))}개")
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 실행
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
os.makedirs("data", exist_ok=True)

items = list(TOPICS.items())
for i, (topic_id, topic_data) in enumerate(items):
    result   = generate_topic(topic_id, topic_data)
    out_path = f"data/{topic_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {out_path} 저장")

    if i < len(items) - 1:
        print(f"  ⏳ 60초 대기...")
        time.sleep(60)

print("\n✅ 전체 완료")
