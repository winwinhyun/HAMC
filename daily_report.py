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

SYSTEM_PROMPT = """당신은 한화첨단소재의 시장 인텔리전스 수석 분석가입니다.

한화첨단소재 주요 제품군:
- 경량복합소재: CFRP, GFRP, 열가소성 복합재
- 배터리 소재: 배터리 케이스, 팩 구조재, 열관리 소재
- 자동차 내외장: 범퍼빔, 도어모듈, 루프패널
- 방산/항공: 구조용 복합재

분석 시 반드시:
1. 각 트렌드가 어느 제품군에 영향을 주는지 명확히 매핑
2. 영향도를 HIGH/MEDIUM/LOW로 스코어링
3. 단기(6개월)/중기(2년)/장기(5년) 시사점 분리
4. 경쟁사(도레이, Hexcel, SGL) 대비 기회/위협 구분
5. 영업/R&D/경영진 관점 액션 아이템 제시

반드시 아래 JSON만 반환 (마크다운 없이):
{
  "summary": "3줄 이내 핵심 요약",
  "impact_score": "HIGH 또는 MEDIUM 또는 LOW",
  "sections": [
    {"title": "섹션 제목", "content": "분석 내용 2-3문장", "tag": "EV동향 또는 OEM동향 또는 정책변화 또는 소재기술 또는 경쟁사 또는 수요예측"}
  ],
  "products_affected": ["영향받는 제품군"],
  "actions": {"sales": "영업팀 액션", "rd": "R&D팀 액션", "management": "경영진 액션"},
  "timeline": {"short": "6개월 시사점", "mid": "2년 시사점", "long": "5년 시사점"}
}"""

PROMPT = """오늘 날짜 기준 최근 글로벌 자동차 및 전기차 산업의 주요 동향을 분석하고,
한화첨단소재 관점에서 소재 수요에 미치는 영향을 분석하세요.
EV 판매 동향, OEM 신차 발표, 배터리 기술 변화, 경량화 트렌드를 포함해주세요."""


def call_gemini():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1500}
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()
    raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw.replace("```json", "").replace("```", "").strip())


def build_html(data):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    impact_color = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#6b7280"}.get(data.get("impact_score",""), "#6b7280")
    tag_colors = {
        "EV동향":  {"bg":"#eff5ff","color":"#1e5fa8"},
        "OEM동향": {"bg":"#f5f3ff","color":"#5b21b6"},
        "정책변화": {"bg":"#ecfdf5","color":"#065f46"},
        "소재기술": {"bg":"#fff7ed","color":"#9a3412"},
        "경쟁사":  {"bg":"#fefce8","color":"#854d0e"},
        "수요예측": {"bg":"#f0fdf4","color":"#166534"},
    }

    sections_html = ""
    for s in data.get("sections", []):
        tc = tag_colors.get(s.get("tag",""), {"bg":"#f3f4f6","color":"#374151"})
        sections_html += f"""
        <div style="background:#fff;border:1px solid #e4ddd4;border-radius:12px;padding:16px 18px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <strong style="font-size:13px;color:#1a1814">{s.get('title','')}</strong>
            <span style="font-size:10px;background:{tc['bg']};color:{tc['color']};padding:2px 9px;border-radius:20px;font-weight:600">{s.get('tag','')}</span>
          </div>
          <p style="font-size:12.5px;color:#6b6359;line-height:1.7;margin:0">{s.get('content','')}</p>
        </div>"""

    products_html = "".join(
        f'<span style="font-size:11px;background:#eff5ff;border:1px solid #c5d9f7;border-radius:20px;padding:3px 11px;color:#1e5fa8;font-weight:500;margin-right:6px">{p}</span>'
        for p in data.get("products_affected", [])
    )

    return f"""
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#faf8f4;font-family:'Apple SD Gothic Neo',sans-serif">
<div style="max-width:640px;margin:0 auto;padding:32px 16px">

  <!-- Header -->
  <div style="background:#1a1814;border-radius:16px;padding:24px 28px;margin-bottom:20px">
    <div style="font-size:11px;color:#9c9288;letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px">Hanwha Advanced Materials</div>
    <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:4px">Daily Intelligence Report</div>
    <div style="font-size:12px;color:#6b6359">{today} 기준 · AI 자동 분석</div>
  </div>

  <!-- Impact + Summary -->
  <div style="background:#fff;border:1px solid #e4ddd4;border-radius:16px;padding:24px 28px;margin-bottom:14px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
      <div>
        <div style="font-size:10px;font-weight:600;color:#e8541a;letter-spacing:.15em;text-transform:uppercase;margin-bottom:4px">Impact Score</div>
        <div style="font-size:28px;font-weight:700;color:{impact_color}">{data.get('impact_score','–')}</div>
      </div>
      <div style="font-size:11px;color:#9c9288;text-align:right">Market Intelligence<br>Auto-generated</div>
    </div>
    <div style="background:linear-gradient(135deg,#fff4ef,#faf8f4);border-left:3px solid #e8541a;border-radius:8px;padding:14px 16px">
      <div style="font-size:10px;font-weight:600;color:#e8541a;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px">Executive Summary</div>
      <p style="font-size:13.5px;color:#3d3830;line-height:1.75;margin:0">{data.get('summary','')}</p>
    </div>
  </div>

  <!-- Products -->
  {f'<div style="margin-bottom:14px"><span style="font-size:11px;color:#9c9288;font-weight:500;margin-right:8px">영향 제품군</span>{products_html}</div>' if products_html else ''}

  <!-- Sections -->
  <div style="margin-bottom:14px">{sections_html}</div>

  <!-- Timeline -->
  <div style="background:#fff;border:1px solid #e4ddd4;border-radius:16px;padding:20px 24px;margin-bottom:14px">
    <div style="font-size:10px;font-weight:600;color:#9c9288;letter-spacing:.14em;text-transform:uppercase;margin-bottom:14px">시사점 타임라인</div>
    <table style="width:100%;border-collapse:separate;border-spacing:8px 0">
      <tr>
        <td style="width:33%;vertical-align:top;background:#f2ede6;border-radius:10px;padding:12px 14px">
          <div style="font-size:10px;font-weight:600;background:#dcfce7;color:#166534;padding:2px 8px;border-radius:20px;display:inline-block;margin-bottom:8px">단기 6개월</div>
          <p style="font-size:11.5px;color:#6b6359;line-height:1.6;margin:0">{data.get('timeline',{}).get('short','')}</p>
        </td>
        <td style="width:33%;vertical-align:top;background:#f2ede6;border-radius:10px;padding:12px 14px">
          <div style="font-size:10px;font-weight:600;background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:20px;display:inline-block;margin-bottom:8px">중기 2년</div>
          <p style="font-size:11.5px;color:#6b6359;line-height:1.6;margin:0">{data.get('timeline',{}).get('mid','')}</p>
        </td>
        <td style="width:33%;vertical-align:top;background:#f2ede6;border-radius:10px;padding:12px 14px">
          <div style="font-size:10px;font-weight:600;background:#ede9fe;color:#5b21b6;padding:2px 8px;border-radius:20px;display:inline-block;margin-bottom:8px">장기 5년</div>
          <p style="font-size:11.5px;color:#6b6359;line-height:1.6;margin:0">{data.get('timeline',{}).get('long','')}</p>
        </td>
      </tr>
    </table>
  </div>

  <!-- Actions -->
  <div style="background:#fff;border:1px solid #e4ddd4;border-radius:16px;padding:20px 24px;margin-bottom:24px">
    <div style="font-size:10px;font-weight:600;color:#9c9288;letter-spacing:.14em;text-transform:uppercase;margin-bottom:14px">액션 아이템</div>
    <table style="width:100%;border-collapse:separate;border-spacing:8px 0">
      <tr>
        <td style="width:33%;vertical-align:top;background:#f2ede6;border-radius:10px;padding:12px 14px">
          <div style="font-size:10px;font-weight:600;color:#1e5fa8;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">영업팀</div>
          <p style="font-size:11.5px;color:#6b6359;line-height:1.6;margin:0">{data.get('actions',{}).get('sales','')}</p>
        </td>
        <td style="width:33%;vertical-align:top;background:#f2ede6;border-radius:10px;padding:12px 14px">
          <div style="font-size:10px;font-weight:600;color:#7c3aed;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">R&amp;D팀</div>
          <p style="font-size:11.5px;color:#6b6359;line-height:1.6;margin:0">{data.get('actions',{}).get('rd','')}</p>
        </td>
        <td style="width:33%;vertical-align:top;background:#f2ede6;border-radius:10px;padding:12px 14px">
          <div style="font-size:10px;font-weight:600;color:#a05c00;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">경영진</div>
          <p style="font-size:11.5px;color:#6b6359;line-height:1.6;margin:0">{data.get('actions',{}).get('management','')}</p>
        </td>
      </tr>
    </table>
  </div>

  <!-- Footer -->
  <div style="text-align:center;font-size:11px;color:#c5bdb5">
    한화첨단소재 Market Intelligence System · AI 자동 생성<br>
    <a href="https://winwinhyun.github.io/HAMC/" style="color:#e8541a;text-decoration:none">대시보드 바로가기</a>
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
    print(f"분석 완료. Impact: {data.get('impact_score')}")
    html = build_html(data)
    send_email(html, today)
