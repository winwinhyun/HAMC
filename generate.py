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

SYSTEM = (
    "You are a market intelligence analyst for Hanwha Advanced Materials.\n"
    "CRITICAL RULES:\n"
    "1. Respond ONLY with a raw JSON object - no markdown, no code blocks\n"
    "2. ALL string values must be on a SINGLE LINE - no newlines inside strings\n"
    "3. Use \\n for line breaks inside strings if needed\n"
    "4. Start response with { and end with }\n\n"
    "Product reference (internal only):\n"
    "- StrongLite(GMT): world #1, bumper beams, battery trays\n"
    "- SuperLite(LWRT): world #1, underbody panels, headliners\n"
    "- BuffLite(EPP): bumper absorbers, sound insulation, EMI shielding\n"
    "- IntermLite(PMC): automotive interior skin materials\n"
    "- SMC: exterior panels, battery pack cases\n"
    "Competitors: Toray, Hexcel, SGL Carbon\n\n"
    "JSON structure:\n"
    '{"summary":"one line text","impact_score":"HIGH","analysis_period":"...","accuracy_summary":{"overall_score":80,"has_ai_inference":true,"note":"..."},'
    '"data_sources":[{"name":"...","type":"market"}],'
    '"sections":[{"title":"...","content":"one line text no newlines","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"}],'
    '"products_affected":["StrongLite (GMT)"],'
    '"actions":{"sales":"one line","rd":"one line","management":"one line"},'
    '"timeline":{"short":"one line","mid":"one line","long":"one line"}}'
)

TOPICS = {
    "weekly":    "Analyze major global automotive and EV industry trends from the past month and their impact on Hanwha Advanced Materials. Include EV sales, OEM launches, battery tech, lightweighting trends, and policies. Write at least 6 sections. Respond in Korean. ALL string values must be single line.",
    "ev":        "Analyze the latest global EV market trends and policy changes (US IRA, EU carbon regulations, China NEV) and their impact on Hanwha Advanced Materials product demand. Write at least 6 sections. Respond in Korean. ALL string values must be single line.",
    "oem":       "Analyze recent new model launches, platform transitions, and material adoption from major OEMs (Hyundai/Kia, BMW, GM, Toyota, Tesla, BYD) and business opportunities for Hanwha Advanced Materials. Write at least 6 sections. Respond in Korean. ALL string values must be single line.",
    "materials": "Analyze automotive and aerospace lightweight composite material trends, CFRP/GFRP market changes, and competitor moves (Toray, Hexcel, SGL Carbon), and assess Hanwha Advanced Materials technology positioning. Write at least 6 sections. Respond in Korean. ALL string values must be single line."
}

def fix_json_string(text):
    """JSON 문자열 내 줄바꿈 수정"""
    # 코드블록 제거
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # { 시작 ~ 마지막 } 추출
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        return None
    text = text[start:end+1]

    # JSON 문자열 값 안의 줄바꿈 수정
    # "key": "value\nwith\nnewlines" 패턴에서 줄바꿈을 공백으로 교체
    result = []
    in_string = False
    escape_next = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == '\\':
            result.append(ch)
            escape_next = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch == '\n':
            result.append(' ')  # 줄바꿈 → 공백
        elif in_string and ch == '\r':
            pass  # 캐리지리턴 제거
        elif in_string and ch == '\t':
            result.append(' ')  # 탭 → 공백
        else:
            result.append(ch)
        i += 1

    fixed = ''.join(result)
    return fixed

def extract_json(text):
    fixed = fix_json_string(text)
    if not fixed:
        return None
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        print(f"  파싱 오류: {e}")
        # 마지막 시도: 줄바꿈 전체 제거
        try:
            oneline = fixed.replace('\n', ' ').replace('\r', '')
            return json.loads(oneline)
        except Exception as e2:
            print(f"  최종 파싱 실패: {e2}")
            return None

def call_claude(topic_id, prompt):
    print(f"▶ [{topic_id}] 분석 시작...")
    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 4000,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": f"Today's date: {DATE_ONLY}\n\n{prompt}"}]
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

        result = extract_json(text)
        if result:
            result["generated_at"] = TIMESTAMP
            print(f"  ✓ 파싱 성공")
            return result
        else:
            print(f"  ⚠ 파싱 실패")
            return {
                "error": "parse_failed",
                "generated_at": TIMESTAMP,
                "summary": "분석 데이터 파싱 실패 - 다음 갱신 시 자동 복구됩니다.",
                "impact_score": "MEDIUM",
                "analysis_period": DATE_ONLY,
                "accuracy_summary": {"overall_score": 0, "has_ai_inference": True, "note": "파싱 실패"},
                "data_sources": [],
                "sections": [],
                "products_affected": [],
                "actions": {"sales": "", "rd": "", "management": ""},
                "timeline": {"short": "", "mid": "", "long": ""}
            }
    except Exception as e:
        print(f"  ✗ 오류: {e}")
        return {
            "error": str(e),
            "generated_at": TIMESTAMP,
            "summary": f"API 오류: {str(e)}",
            "impact_score": "MEDIUM",
            "analysis_period": DATE_ONLY,
            "accuracy_summary": {"overall_score": 0, "has_ai_inference": False, "note": "오류"},
            "data_sources": [],
            "sections": [],
            "products_affected": [],
            "actions": {"sales": "", "rd": "", "management": ""},
            "timeline": {"short": "", "mid": "", "long": ""}
        }

os.makedirs("data", exist_ok=True)

for i, (topic_id, prompt) in enumerate(TOPICS.items()):
    result = call_claude(topic_id, prompt)
    out_path = f"data/{topic_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {out_path} 저장 완료")
    if i < len(TOPICS) - 1:
        time.sleep(10)

print("✅ 전체 완료")
