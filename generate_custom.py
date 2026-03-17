"""
generate_custom.py — 직접 질문 처리
repository_dispatch 이벤트로 호출됨
환경변수: CUSTOM_QUESTION, REQUEST_ID, ANTHROPIC_API_KEY
"""
import json, re, urllib.request, os
from datetime import datetime, timezone, timedelta

API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
QUESTION = os.environ.get("CUSTOM_QUESTION", "")
REQ_ID   = os.environ.get("REQUEST_ID", "")

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)
TIMESTAMP = now.strftime("%Y년 %m월 %d일 %H시 %M분")
DATE_ONLY = now.strftime("%Y년 %m월 %d일")

SYSTEM = """당신은 한화첨단소재의 시장 인텔리전스 수석 분석가입니다.
한화첨단소재 핵심 제품군:
- StrongLite(GMT): 유리섬유 매트 강화 열가소성. 세계 1위. 범퍼빔·배터리 트레이·언더커버.
- SuperLite(LWRT): 경량 다공성 열가소성. 세계 1위. 언더바디·헤드라이너·도어트림.
- BuffLite(EPP): 발포 폴리프로필렌. 범퍼 흡수재·차음재·전자파 차폐.
- IntermLite(PMC): 자동차 내장재 표피재. 인스트루먼트 패널·도어트림.
- SMC: 열경화성 복합소재. 외장패널·배터리팩 케이스·픽업트럭 베드.
- 태양광소재: Encapsulant(EVA/POE), Backsheet. 9GW/년 생산.
경쟁사: 도레이, Hexcel, SGL Carbon

웹 검색으로 최신 뉴스를 찾은 후 분석하세요.
JSON만 출력(마크다운 없이):
{"summary":"...","impact_score":"HIGH","analysis_period":"...","accuracy_summary":{"overall_score":85,"has_ai_inference":false,"note":"..."},"data_sources":[{"name":"...","type":"market"}],"sections":[{"title":"...","content":"...","tag":"EV동향","accuracy_level":"HIGH","source_type":"market"}],"products_affected":["StrongLite (GMT)"],"product_impact":{"StrongLite (GMT)":"HIGH","SuperLite (LWRT)":"MEDIUM","BuffLite (EPP)":"LOW","IntermLite (PMC)":"NONE","SMC":"MEDIUM","Encapsulant (EVA/POE)":"NONE"},"actions":{"sales":"...","rd":"...","management":"..."},"timeline":{"short":"...","mid":"...","long":"..."}}"""

WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}

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
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))

def fix_and_parse(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text).strip()
    s, e = text.find('{'), text.rfind('}')
    if s == -1 or e == -1: return None
    text = text[s:e+1]
    out, in_str, esc = [], False, False
    for ch in text:
        if esc: out.append(ch); esc = False
        elif ch == '\\': out.append(ch); esc = True
        elif ch == '"': in_str = not in_str; out.append(ch)
        elif in_str and ch in '\n\r\t': out.append(' ')
        else: out.append(ch)
    try: return json.loads(''.join(out))
    except: return None

def run():
    if not QUESTION:
        print("CUSTOM_QUESTION 없음, 종료")
        return

    print(f"질문: {QUESTION}")
    messages = [{"role": "user", "content": f"오늘: {DATE_ONLY}\n\n{QUESTION}\n\n한화첨단소재 관점에서 최신 뉴스를 검색하여 분석하세요."}]
    search_count = 0

    for loop in range(12):
        body   = api_request({"model":"claude-sonnet-4-5","max_tokens":5000,"system":SYSTEM,"tools":[WEB_SEARCH_TOOL],"messages":messages})
        stop   = body.get("stop_reason","")
        blocks = body.get("content",[])

        for b in blocks:
            if b.get("type")=="tool_use" and b.get("name")=="web_search":
                search_count += 1
                print(f"  🔍 {b.get('input',{}).get('query','')}")

        if stop == "end_turn":
            text = "".join(b.get("text","") for b in blocks if b.get("type")=="text")
            result = fix_and_parse(text)
            if result:
                result["generated_at"]  = TIMESTAMP
                result["search_powered"] = True
                result["request_id"]    = REQ_ID
                os.makedirs("data", exist_ok=True)
                with open("data/custom.json","w",encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✓ custom.json 저장 (검색 {search_count}회)")
            else:
                print("⚠ 파싱 실패")
            return

        elif stop == "tool_use":
            messages.append({"role":"assistant","content":blocks})
            messages.append({"role":"user","content":[
                {"type":"tool_result","tool_use_id":b["id"],"content":""}
                for b in blocks if b.get("type")=="tool_use"
            ]})
        else:
            print(f"unexpected stop: {stop}")
            break

run()
