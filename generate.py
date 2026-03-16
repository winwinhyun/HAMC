import json
import re
import urllib.request
import os
import time
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
DATE_ONLY = now.strftime("%Y년 %m월 %d일")
TIMESTAMP = now.strftime("%Y년 %m월 %d일 %H시 %M분")

SYSTEM = """You are a market intelligence analyst for Hanwha Advanced Materials.
Product context (do not quote directly):
- StrongLite(GMT): world #1 market share, bumper beams, battery trays, underbody covers
- SuperLite(LWRT): world #1 market share, underbody panels, headliners, door trims
- BuffLite(EPP): bumper energy absorbers, sound insulation, EMI shielding
- IntermLite(PMC): automotive interior skin materials, instrument panels
- SMC: exterior panels, battery pack cases, pickup truck beds
Competitors: Toray, Hexcel, SGL Carbon

STRICT OUTPUT RULES:
- Output ONLY valid JSON
- NO markdown code blocks (no ```)
- NO newlines inside any string value
- NO tab characters inside string values  
- All text in string values must be on ONE line
- Use periods or semicolons instead of newlines in long text"""

TOPICS = {
    "weekly": {
        "label": "주간 종합",
        "prompt": """Analyze global automotive and EV industry trends for the past month relevant to Hanwha Advanced Materials.

Return this exact JSON (all string values single-line, no newlines in strings):
{"summary":"[2-3 sentence summary in Korean]","impact_score":"HIGH","analysis_period":"[period in Korean]","accuracy_summary":{"overall_score":78,"has_ai_inference":true,"note":"[note in Korean]"},"data_sources":[{"name":"글로벌 자동차 업계 뉴스","type":"market"},{"name":"EV 정책 동향","type":"regulatory"},{"name":"AI 시장 추론","type":"ai"}],"sections":[{"title":"[title]","content":"[2-3 sentence content in Korean, no newlines]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[title]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[title]","content":"[content]","tag":"정책변화","accuracy_level":"MEDIUM","source_type":"regulatory"},{"title":"[title]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"수요예측","accuracy_level":"LOW","source_type":"ai"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","SMC"],"actions":{"sales":"[action in Korean, single line]","rd":"[action in Korean, single line]","management":"[action in Korean, single line]"},"timeline":{"short":"[6month outlook in Korean, single line]","mid":"[2year outlook in Korean, single line]","long":"[5year outlook in Korean, single line]"}}"""
    },
    "ev": {
        "label": "EV / 정책",
        "prompt": """Analyze global EV market trends and policy changes (US IRA, EU carbon regulations, China NEV) relevant to Hanwha Advanced Materials.

Return this exact JSON (all string values single-line, no newlines in strings):
{"summary":"[2-3 sentence summary in Korean]","impact_score":"HIGH","analysis_period":"[period in Korean]","accuracy_summary":{"overall_score":80,"has_ai_inference":true,"note":"[note in Korean]"},"data_sources":[{"name":"각국 EV 정책 동향","type":"regulatory"},{"name":"글로벌 EV 판매 데이터","type":"market"},{"name":"AI 시장 추론","type":"ai"}],"sections":[{"title":"[title]","content":"[2-3 sentence content in Korean, no newlines]","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[title]","content":"[content]","tag":"정책변화","accuracy_level":"HIGH","source_type":"regulatory"},{"title":"[title]","content":"[content]","tag":"EV동향","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[title]","content":"[content]","tag":"경쟁사","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"리스크","accuracy_level":"LOW","source_type":"ai"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)"],"actions":{"sales":"[action in Korean, single line]","rd":"[action in Korean, single line]","management":"[action in Korean, single line]"},"timeline":{"short":"[6month outlook in Korean, single line]","mid":"[2year outlook in Korean, single line]","long":"[5year outlook in Korean, single line]"}}"""
    },
    "oem": {
        "label": "OEM 동향",
        "prompt": """Analyze recent OEM (Hyundai/Kia, BMW, GM, Toyota, Tesla, BYD) model launches, platform transitions, and material adoption relevant to Hanwha Advanced Materials.

Return this exact JSON (all string values single-line, no newlines in strings):
{"summary":"[2-3 sentence summary in Korean]","impact_score":"HIGH","analysis_period":"[period in Korean]","accuracy_summary":{"overall_score":75,"has_ai_inference":true,"note":"[note in Korean]"},"data_sources":[{"name":"OEM 공식 발표 및 업계 보도","type":"official"},{"name":"자동차 플랫폼 분석","type":"market"},{"name":"AI 사업 기회 분석","type":"ai"}],"sections":[{"title":"[title]","content":"[2-3 sentence content in Korean, no newlines]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"official"},{"title":"[title]","content":"[content]","tag":"OEM동향","accuracy_level":"HIGH","source_type":"market"},{"title":"[title]","content":"[content]","tag":"EV동향","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[title]","content":"[content]","tag":"경쟁사","accuracy_level":"LOW","source_type":"ai"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","IntermLite (PMC)","SMC"],"actions":{"sales":"[action in Korean, single line]","rd":"[action in Korean, single line]","management":"[action in Korean, single line]"},"timeline":{"short":"[6month outlook in Korean, single line]","mid":"[2year outlook in Korean, single line]","long":"[5year outlook in Korean, single line]"}}"""
    },
    "materials": {
        "label": "소재 기술",
        "prompt": """Analyze automotive/aerospace lightweight composite material trends, CFRP/GFRP market, and competitor moves (Toray, Hexcel, SGL Carbon) relevant to Hanwha Advanced Materials.

Return this exact JSON (all string values single-line, no newlines in strings):
{"summary":"[2-3 sentence summary in Korean]","impact_score":"MEDIUM","analysis_period":"[period in Korean]","accuracy_summary":{"overall_score":77,"has_ai_inference":true,"note":"[note in Korean]"},"data_sources":[{"name":"소재 기술 업계 보도","type":"market"},{"name":"경쟁사 동향 분석","type":"market"},{"name":"AI 기술 트렌드 추론","type":"ai"}],"sections":[{"title":"[title]","content":"[2-3 sentence content in Korean, no newlines]","tag":"소재기술","accuracy_level":"HIGH","source_type":"market"},{"title":"[title]","content":"[content]","tag":"경쟁사","accuracy_level":"HIGH","source_type":"market"},{"title":"[title]","content":"[content]","tag":"소재기술","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"친환경","accuracy_level":"MEDIUM","source_type":"market"},{"title":"[title]","content":"[content]","tag":"수요예측","accuracy_level":"MEDIUM","source_type":"ai"},{"title":"[title]","content":"[content]","tag":"리스크","accuracy_level":"LOW","source_type":"ai"}],"products_affected":["StrongLite (GMT)","SuperLite (LWRT)","BuffLite (EPP)","SMC"],"actions":{"sales":"[action in Korean, single line]","rd":"[action in Korean, single line]","management":"[action in Korean, single line]"},"timeline":{"short":"[6month outlook in Korean, single line]","mid":"[2year outlook in Korean, single line]","long":"[5year outlook in Korean, single line]"}}"""
    }
}

def fix_and_parse(text):
    # 코드블록 제거
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # { ~ } 추출
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return None
    text = text[start:end+1]

    # 문자열 안의 줄바꿈 제거 (문자 단위 처리)
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == '\\':
            result.append(ch)
            escape_next = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch in '\n\r\t':
            result.append(' ')
        else:
            result.append(ch)

    fixed = ''.join(result)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        print(f"  파싱 오류: {e}")
        return None

def call_claude(topic_id, topic_data):
    print(f"▶ [{topic_id}] 분석 시작...")
    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 4000,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": f"Today: {DATE_ONLY}\n\n{topic_data['prompt']}"}]
    }
    data = json.dumps(payload).encode("utf-8")
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body.get("content", [{}])[0].get("text", "")
        print(f"  응답 길이: {len(text)} chars")

        result = fix_and_parse(text)
        if result:
            result["generated_at"] = TIMESTAMP
            print(f"  ✓ 파싱 성공")
            return result
        else:
            print(f"  ⚠ 파싱 실패 - 원문: {text[:200]}")
            return make_error("parse_failed")
    except Exception as e:
        print(f"  ✗ API 오류: {e}")
        return make_error(str(e))

def make_error(msg):
    return {
        "error": msg,
        "generated_at": TIMESTAMP,
        "summary": "분석 데이터 파싱 실패 - 다음 갱신 시 자동 복구됩니다.",
        "impact_score": "MEDIUM",
        "analysis_period": DATE_ONLY,
        "accuracy_summary": {"overall_score": 0, "has_ai_inference": True, "note": "오류"},
        "data_sources": [],
        "sections": [],
        "products_affected": [],
        "actions": {"sales": "", "rd": "", "management": ""},
        "timeline": {"short": "", "mid": "", "long": ""}
    }

os.makedirs("data", exist_ok=True)

items = list(TOPICS.items())
for i, (topic_id, topic_data) in enumerate(items):
    result = call_claude(topic_id, topic_data)
    out_path = f"data/{topic_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {out_path} 저장")
    if i < len(items) - 1:
        time.sleep(10)

print("✅ 전체 완료")
