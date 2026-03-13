import requests
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
EMAIL_TO       = os.environ["EMAIL_TO"]
EMAIL_FROM     = os.environ["EMAIL_FROM"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SYSTEM_PROMPT = """당신은 한화첨단소재의 시장 인텔리전스 수석 분석가입니다. 경영진에게 보고하는 수준의 상세하고 전문적인 분석을 제공합니다.

한화첨단소재 주요 제품군:
- 경량복합소재: CFRP, GFRP, 열가소성 복합재 (자동차·항공·방산용)
- 배터리 소재: 배터리 케이스, 팩 구조재, 열관리 소재 (EV용)
- 자동차 내외장: 범퍼빔, 도어모듈, 루프패널, 언더커버
- 방산/항공: 구조용 복합재, 레이돔, 탄체

경쟁사: 도레이(Toray), Hexcel, SGL Carbon, Solvay, Teijin

[매우 중요한 규칙]
- summary: 반드시 5문장 이상. 시장 전반 상황과 한화첨단소재 영향을 구체적으로 서술.
- sections: 반드시 5개 이상. 각 content는 반드시 4문장 이상. 구체적 수치·사례 포함.
- timeline의 short, mid, long: 각각 반드시 3문장 이상의 구체적인 분석 문장으로 작성.
  절대로 "6개월", "2년", "5년" 같은 단어 하나만 값으로 넣지 말 것.
- actions의 sales, rd, management: 각각 반드시 3문장 이상. 구체적 액션과 기대효과 포함.

반드시 아래 JSON 형식만 반환. 마크다운 코드블록(```) 없이 순수 JSON만 출력:
{
  "summary": "5문장 이상의 상세한 시장 요약",
  "impact_score": "HIGH 또는 MEDIUM 또는 LOW",
  "sections": [
    {"title": "섹션 제목", "content": "4문장 이상의 상세 분석", "tag": "EV동향 또는 OEM동향 또는 정책변화 또는 소재기술 또는 경쟁사 또는 수요예측"}
  ],
  "products_affected": ["영향받는 제품군 목록"],
  "actions": {
    "sales": "3문장 이상의 구체적 영업팀 액션",
    "rd": "3문장 이상의 구체적 R&D팀 액션",
    "management": "3문장 이상의 구체적 경영진 의사결정 사항"
  },
  "timeline": {
    "short": "3문장 이상. 향후 6개월 내 한화첨단소재가 취해야 할 구체적 행동과 예상 효과.",
    "mid": "3문장 이상. 2년 내 시장 변화와 한화첨단소재의 사업 기회·위협.",
    "long": "3문장 이상. 5년 후 산업 구조 변화와 한화첨단소재의 장기 포지셔닝 전략."
  }
}"""

PROMPT = """오늘 날짜 기준 글로벌 자동차 및 전기차 산업의 최신 동향을 심층 분석해주세요.

다음 항목을 반드시 포함하세요:
1. 글로벌 EV 판매 현황 및 주요 시장(중국·미국·유럽) 동향
2. 현대/기아, BMW, GM, Toyota, Tesla, BYD 등 주요 OEM 신차·플랫폼 발표
3. 각국 EV 정책 변화 (IRA, EU 탄소규제, 중국 보조금 등)
4. 배터리 기술 트렌드 (LFP vs NCM, 전고체 배터리 동향)
5. 자동차 경량화 트렌드 및 CFRP·복합소재 채용 사례
6. 도레이·Hexcel·SGL 등 경쟁사 최근 동향

각 섹션마다 한화첨단소재의 어떤 제품군에 어떤 영향을 주는지 구체적으로 분석하세요.
모든 분석은 최소 4문장 이상으로 상세하게 작성하세요."""


def call_gemini():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 4000,
            "responseMimeType": "application/json"
        }
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def build_html(data):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    impact_color = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#6b7280"}.get(data.get("impact_score", ""), "#6b7280")
    tag_colors = {
        "EV동향":  {"bg": "#eff5ff", "color": "#1e5fa8"},
        "OEM동향": {"bg": "#f5f3ff", "color": "#5b21b6"},
        "정책변화": {"bg": "#ecfdf5", "color": "#065f46"},
        "소재기술": {"bg": "#fff7ed", "color": "#9a3412"},
        "경쟁사":  {"bg": "#fefce8", "color": "#854d0e"},
        "수요예측": {"bg": "#f0fdf4", "color": "#166534"},
    }

    sections_html = ""
    for s in data.get("sections", []):
        tc = tag_colors.get(s.get("tag", ""), {"bg": "#f3f4f6", "color": "#374151"})
        sections_html += f"""
        <div style="background:#fff;border:1px solid #e4ddd4;border-radius:12px;padding:18px 20px;margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <strong style="font-size:14px;color:#1a1814">{s.get('title', '')}</strong>
            <span style="font-size:10px;background:{tc['bg']};color:{tc['color']};padding:3px 10px;border-radius:20px;font-weight:600;white-space:nowrap;margin-left:10px">{s.get('tag', '')}</span>
          </div>
          <p style="font-size:13px;color:#3d3830;line-height:1.85;margin:0">{s.get('content', '')}</p>
        </div>"""

    products_html = "".join(
        f'<span style="font-size:11px;background:#eff5ff;border:1px solid #c5d9f7;border-radius:20px;padding:4px 12px;color:#1e5fa8;font-weight:500;margin-right:6px;margin-bottom:6px;display:inline-block">{p}</span>'
        for p in data.get("products_affected", [])
    )

    tl = data.get("timeline", {})
    ac = data.get("actions", {})

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>한화첨단소재 Daily Intelligence Report</title>
</head>
<body style="margin:0;padding:0;background:#faf8f4;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif">
<div style="max-width:680px;margin:0 auto;padding:32px 16px">

  <!-- Header -->
  <div style="background:#1a1814;border-radius:16px;padding:28px 32px;margin-bottom:20px">
    <div style="font-size:10px;color:#6b6359;letter-spacing:.2em;text-transform:uppercase;margin-bottom:8px">Hanwha Advanced Materials · Market Intelligence System</div>
    <div style="font-size:26px;font-weight:700;color:#ffffff;margin-bottom:6px">Daily Intelligence Report</div>
    <div style="font-size:13px;color:#9c9288">{today} 기준 · AI 자동 분석 · 경영진 보고용</div>
  </div>

  <!-- Impact + Summary -->
  <div style="background:#fff;border:1px solid #e4ddd4;border-radius:16px;padding:26px 28px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.04)">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px">
      <div>
        <div style="font-size:10px;font-weight:600;color:#e8541a;letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px">Overall Impact Score</div>
        <div style="font-size:32px;font-weight:700;color:{impact_color};line-height:1">{data.get('impact_score', '–')}</div>
      </div>
      <div style="text-align:right">
        <div style="font-size:10px;color:#9c9288;margin-bottom:4px">자동 생성 리포트</div>
        <div style="font-size:11px;color:#c5bdb5">{today}</div>
      </div>
    </div>
    <div style="background:linear-gradient(135deg,#fff4ef,#faf8f4);border-left:3px solid #e8541a;border-radius:10px;padding:16px 18px">
      <div style="font-size:10px;font-weight:600;color:#e8541a;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px">Executive Summary</div>
      <p style="font-size:14px;color:#1a1814;line-height:1.85;margin:0">{data.get('summary', '')}</p>
    </div>
  </div>

  <!-- Products -->
  {f'<div style="background:#fff;border:1px solid #e4ddd4;border-radius:12px;padding:16px 20px;margin-bottom:16px"><div style="font-size:10px;font-weight:600;color:#9c9288;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px">영향 제품군</div><div>{products_html}</div></div>' if products_html else ''}

  <!-- Sections -->
  <div style="font-size:10px;font-weight:600;color:#9c9288;letter-spacing:.14em;text-transform:uppercase;margin-bottom:12px;padding-left:4px">상세 분석</div>
  <div style="margin-bottom:16px">{sections_html}</div>

  <!-- Timeline -->
  <div style="background:#fff;border:1px solid #e4ddd4;border-radius:16px;padding:22px 26px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.04)">
    <div style="font-size:10px;font-weight:600;color:#9c9288;letter-spacing:.14em;text-transform:uppercase;margin-bottom:18px">시사점 타임라인</div>
    <div style="margin-bottom:14px;padding:16px 18px;background:#f2ede6;border-radius:12px">
      <div style="font-size:10px;font-weight:600;background:#dcfce7;color:#166534;padding:3px 10px;border-radius:20px;display:inline-block;margin-bottom:10px">단기 · 향후 6개월</div>
      <p style="font-size:13px;color:#3d3830;line-height:1.85;margin:0">{tl.get('short', '')}</p>
    </div>
    <div style="margin-bottom:14px;padding:16px 18px;background:#f2ede6;border-radius:12px">
      <div style="font-size:10px;font-weight:600;background:#fef9c3;color:#854d0e;padding:3px 10px;border-radius:20px;display:inline-block;margin-bottom:10px">중기 · 2년 전망</div>
      <p style="font-size:13px;color:#3d3830;line-height:1.85;margin:0">{tl.get('mid', '')}</p>
    </div>
    <div style="padding:16px 18px;background:#f2ede6;border-radius:12px">
      <div style="font-size:10px;font-weight:600;background:#ede9fe;color:#5b21b6;padding:3px 10px;border-radius:20px;display:inline-block;margin-bottom:10px">장기 · 5년 전망</div>
      <p style="font-size:13px;color:#3d3830;line-height:1.85;margin:0">{tl.get('long', '')}</p>
    </div>
  </div>

  <!-- Actions -->
  <div style="background:#fff;border:1px solid #e4ddd4;border-radius:16px;padding:22px 26px;margin-bottom:28px;box-shadow:0 2px 12px rgba(0,0,0,.04)">
    <div style="font-size:10px;font-weight:600;color:#9c9288;letter-spacing:.14em;text-transform:uppercase;margin-bottom:18px">액션 아이템</div>
    <div style="margin-bottom:14px;padding:16px 18px;background:#eff5ff;border-radius:12px;border-left:3px solid #1e5fa8">
      <div style="font-size:10px;font-weight:600;color:#1e5fa8;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">영업팀</div>
      <p style="font-size:13px;color:#1a1814;line-height:1.85;margin:0">{ac.get('sales', '')}</p>
    </div>
    <div style="margin-bottom:14px;padding:16px 18px;background:#f5f3ff;border-radius:12px;border-left:3px solid #7c3aed">
      <div style="font-size:10px;font-weight:600;color:#7c3aed;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">R&amp;D팀</div>
      <p style="font-size:13px;color:#1a1814;line-height:1.85;margin:0">{ac.get('rd', '')}</p>
    </div>
    <div style="padding:16px 18px;background:#fffaed;border-radius:12px;border-left:3px solid #a05c00">
      <div style="font-size:10px;font-weight:600;color:#a05c00;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">경영진</div>
      <p style="font-size:13px;color:#1a1814;line-height:1.85;margin:0">{ac.get('management', '')}</p>
    </div>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:20px;border-top:1px solid #e4ddd4">
    <div style="font-size:12px;color:#9c9288;margin-bottom:8px">한화첨단소재 Market Intelligence System · AI 자동 생성</div>
    <a href="https://winwinhyun.github.io/HAMC/" style="font-size:12px;color:#e8541a;text-decoration:none;font-weight:500">대시보드에서 직접 분석하기 →</a>
  </div>

</div>
</body>
</html>"""


def send_email(html_content, today):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[한화첨단소재] Daily Intelligence Report · {today}"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO.split(","), msg.as_string())
    print("이메일 발송 완료!")


if __name__ == "__main__":
    today = datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today}] 리포트 생성 시작...")
    data = call_gemini()
    print(f"분석 완료. Impact: {data.get('impact_score')}, 섹션 수: {len(data.get('sections', []))}")
    html = build_html(data)
    send_email(html, today)
    print("완료!")
