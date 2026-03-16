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
    "당신은 한화첨단소재의 시장 인텔리전스 수석 분석가입니다.\n"
    "내부 참조 전용(레포트에 직접 인용 금지):\n"
    "- StrongLite(GMT): 세계1위, 범퍼빔·배터리 트레이 등\n"
    "- SuperLite(LWRT): 세계1위, 언더바디·헤드라이너 등\n"
    "- BuffLite(EPP): 범퍼 흡수재·차음재·전자파 차폐 등\n"
    "- IntermLite(PMC): 자동차 내장재 표피재\n"
    "- SMC: 외장 패널·배터리 팩 케이스 등\n"
    "경쟁사: 도레이, Hexcel, SGL Carbon\n\n"
    "작성 원칙:\n"
    "1. 실제 최신 시장 뉴스와 동향에 기반할 것\n"
    "2. sections 6개 이상 작성\n"
    "3. JSON만 출력 (마크다운 코드블록 없이)\n\n"
    "출력 형식:\n"
    '{"summary":"...","impact_score":"HIGH","analysis_period":"...","accuracy_summary":{"overall_score":80,"has_ai_inference":true,"note":"..."},'
    '"data_sources":[{"name":"...","type":"market"}],'
    '"sections":[{"title":"...","content":"...","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"}],'
    '"products_affected":["StrongLite (GMT)"],'
    '"actions":{"sales":"...","rd":"...","management":"..."},'
    '"timeline":{"short":"...","mid":"...","long":"..."}}'
)

TOPICS = {
    "weekly":    "최근 1개월 글로벌 자동차 및 전기차 산업 주요 동향을 분석하고 한화첨단소재 소재 수요 영향을 분석하세요. EV 판매, OEM 신차, 배터리 기술, 경량화 트렌드, 관련 정책 포함. sections 6개 이상.",
    "ev":        "글로벌 전기차 시장 최신 동향과 각국 EV 정책 변화(미국 IRA, EU 탄소규제, 중국 NEV)를 분석하고 한화첨단소재 제품 수요 영향을 분석하세요. sections 6개 이상.",
    "oem":       "현대기아 BMW GM Toyota Tesla BYD 등 주요 OEM의 최근 신차 출시 플랫폼 전환 소재 채용 발표를 분석하고 한화첨단소재 사업 기회를 분석하세요. sections 6개 이상.",
    "materials": "자동차 항공 경량복합소재 기술 트렌드 CFRP GFRP 시장 변화 도레이 Hexcel SGL Carbon 경쟁사 동향을 분석하고 한화첨단소재 기술 포지셔닝과 R&D 방향을 분석하세요. sections 6개 이상."
}

def call_claude(topic_id, prompt):
    print(f"▶ [{topic_id}] 분석 시작...")
    payload = {
        "model": "claude-sonnet-4-5",
        "max_tokens": 4000,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": f"오늘 날짜: {DATE_ONLY}\n\n{prompt}"}]
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
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            result = json.loads(match.group())
            result["generated_at"] = TIMESTAMP
            return result
        else:
            print(f"  ⚠ JSON 파싱 실패: {text[:200]}")
            return {"error": "parse_failed", "generated_at": TIMESTAMP, "summary": "분석 생성 실패"}
    except Exception as e:
        print(f"  ✗ 오류: {e}")
        return {"error": str(e), "generated_at": TIMESTAMP, "summary": "API 오류 발생"}

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
