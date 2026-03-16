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
    "IMPORTANT: Respond ONLY with a single valid JSON object. No markdown, no code blocks, no explanation.\n"
    "The JSON must be on a single line or properly escaped. Do not include newlines inside string values.\n\n"
    "Product reference (internal only, do not quote directly):\n"
    "- StrongLite(GMT): world #1, bumper beams, battery trays\n"
    "- SuperLite(LWRT): world #1, underbody panels, headliners\n"
    "- BuffLite(EPP): bumper absorbers, sound insulation, EMI shielding\n"
    "- IntermLite(PMC): automotive interior skin materials\n"
    "- SMC: exterior panels, battery pack cases\n"
    "Competitors: Toray, Hexcel, SGL Carbon\n\n"
    "Output format (single line JSON, all string values must not contain unescaped quotes or newlines):\n"
    '{"summary":"...","impact_score":"HIGH","analysis_period":"...","accuracy_summary":{"overall_score":80,"has_ai_inference":true,"note":"..."},'
    '"data_sources":[{"name":"...","type":"market"}],'
    '"sections":[{"title":"...","content":"...","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"}],'
    '"products_affected":["StrongLite (GMT)"],'
    '"actions":{"sales":"...","rd":"...","management":"..."},'
    '"timeline":{"short":"...","mid":"...","long":"..."}}'
)

TOPICS = {
    "weekly":    "Analyze major global automotive and EV industry trends from the past month and their impact on Hanwha Advanced Materials material demand. Include EV sales, OEM launches, battery tech, lightweighting trends, and policies. Write at least 6 sections. Respond in Korean.",
    "ev":        "Analyze the latest global EV market trends and policy changes (US IRA, EU carbon regulations, China NEV) and their impact on Hanwha Advanced Materials product demand. Write at least 6 sections. Respond in Korean.",
    "oem":       "Analyze recent new model launches, platform transitions, and material adoption announcements from major OEMs (Hyundai/Kia, BMW, GM, Toyota, Tesla, BYD) and business opportunities for Hanwha Advanced Materials. Write at least 6 sections. Respond in Korean.",
    "materials": "Analyze automotive and aerospace lightweight composite material technology trends, CFRP/GFRP market changes, and competitor moves (Toray, Hexcel, SGL Carbon), and assess Hanwha Advanced Materials technology positioning and R&D direction. Write at least 6 sections. Respond in Korean."
}

def extract_json(text):
    """JSON 추출 - 여러 방법 시도"""
    # 방법 1: 코드블록 제거 후 시도
    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()

    # 방법 2: { } 사이 추출
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 방법 3: 줄바꿈 제거 후 시도
    try:
        oneline = ' '.join(cleaned.split())
        match2 = re.search(r'\{.*\}', oneline)
        if match2:
            return json.loads(match2.group())
    except Exception:
        pass

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
            print(f"  ✓ JSON 파싱 성공")
            return result
        else:
            print(f"  ⚠ JSON 파싱 실패. 응답 앞부분: {text[:300]}")
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
