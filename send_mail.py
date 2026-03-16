import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
now = datetime.now(KST).strftime("%Y년 %m월 %d일 %H시 %M분")

gmail_user     = os.environ.get("GMAIL_USER", "")
gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
to_email       = os.environ.get("NOTIFY_EMAIL", "")

if not all([gmail_user, gmail_password, to_email]):
    print("이메일 설정 없음, 스킵")
    exit(0)

try:
    with open("data/weekly.json", encoding="utf-8") as f:
        d = json.load(f)
    summary = d.get("summary", "분석 완료")
    impact  = d.get("impact_score", "MEDIUM")
    period  = d.get("analysis_period", "최근 동향")
    score   = d.get("accuracy_summary", {}).get("overall_score", 70)
    sections = d.get("sections", [])
except Exception:
    summary  = "분석이 완료되었습니다."
    impact   = "MEDIUM"
    period   = "최근 동향"
    score    = 70
    sections = []

# 임팩트 색상
impact_color = {"HIGH": "#dc2626", "MEDIUM": "#d97706", "LOW": "#6b7280"}.get(impact, "#d97706")

# 섹션 3개만 미리보기
section_html = ""
for s in sections[:3]:
    tag = s.get("tag", "")
    title = s.get("title", "")
    content = s.get("content", "")[:120] + "..."
    section_html += f"""
    <tr>
      <td style="padding:10px 0;border-bottom:1px solid #f2ede6">
        <div style="font-size:10px;color:#e8541a;font-weight:600;margin-bottom:3px">{tag}</div>
        <div style="font-size:13px;font-weight:600;color:#1a1814;margin-bottom:4px">{title}</div>
        <div style="font-size:12px;color:#6b6359;line-height:1.6">{content}</div>
      </td>
    </tr>"""

subject = f"[한화첨단소재 Intelligence] {now}"

html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#faf8f4;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#faf8f4;padding:20px 0">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)">

      <!-- 헤더 -->
      <tr>
        <td style="background:#1a1814;padding:20px 28px">
          <table cellpadding="0" cellspacing="0">
            <tr>
              <td style="width:36px;height:36px;background:#e8541a;border-radius:8px;text-align:center;vertical-align:middle">
                <span style="color:#fff;font-size:16px;font-weight:700">H</span>
              </td>
              <td style="padding-left:12px">
                <div style="color:#ffffff;font-size:14px;font-weight:700">Hanwha Advanced Materials</div>
                <div style="color:#9c9288;font-size:10px;letter-spacing:1px;margin-top:2px">MARKET INTELLIGENCE · AI POWERED</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- 본문 -->
      <tr>
        <td style="padding:24px 28px">

          <!-- 타이틀 -->
          <div style="font-size:10px;color:#e8541a;font-weight:600;letter-spacing:2px;margin-bottom:6px">INTELLIGENCE REPORT</div>
          <div style="font-size:22px;font-weight:700;color:#1a1814;margin-bottom:4px">주간 종합 분석</div>
          <div style="font-size:12px;color:#9c9288;margin-bottom:20px">{now} 기준 · {period}</div>

          <!-- 지표 -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
            <tr>
              <td width="33%" style="padding-right:6px">
                <div style="background:#f2ede6;border-radius:8px;padding:12px 14px">
                  <div style="font-size:10px;color:#9c9288;margin-bottom:4px">IMPACT SCORE</div>
                  <div style="font-size:18px;font-weight:700;color:{impact_color}">{impact}</div>
                </div>
              </td>
              <td width="33%" style="padding:0 3px">
                <div style="background:#f2ede6;border-radius:8px;padding:12px 14px">
                  <div style="font-size:10px;color:#9c9288;margin-bottom:4px">정확도</div>
                  <div style="font-size:18px;font-weight:700;color:#177a4a">{score}%</div>
                </div>
              </td>
              <td width="33%" style="padding-left:6px">
                <div style="background:#f2ede6;border-radius:8px;padding:12px 14px">
                  <div style="font-size:10px;color:#9c9288;margin-bottom:4px">분석 모듈</div>
                  <div style="font-size:18px;font-weight:700;color:#1a1814">4개</div>
                </div>
              </td>
            </tr>
          </table>

          <!-- 요약 -->
          <div style="background:#fff4ef;border-left:3px solid #e8541a;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:20px">
            <div style="font-size:10px;color:#e8541a;font-weight:600;letter-spacing:1px;margin-bottom:6px">EXECUTIVE SUMMARY</div>
            <div style="font-size:13px;color:#3d3830;line-height:1.7">{summary}</div>
          </div>

          <!-- 섹션 미리보기 -->
          {f'''
          <div style="font-size:10px;color:#9c9288;font-weight:600;letter-spacing:1px;margin-bottom:10px">주요 분석 항목</div>
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px">
            {section_html}
          </table>
          ''' if section_html else ''}

          <!-- CTA 버튼 -->
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="center">
                <a href="https://winwinhyun.github.io/HAMC/" style="display:inline-block;background:#e8541a;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:14px;font-weight:600">
                  Intelligence Report 전체 보기 →
                </a>
              </td>
            </tr>
          </table>

        </td>
      </tr>

      <!-- 푸터 -->
      <tr>
        <td style="background:#f2ede6;padding:14px 28px;text-align:center">
          <div style="font-size:11px;color:#9c9288">자동 발송 · 3시간마다 갱신 · Powered by Claude AI</div>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"]    = gmail_user
msg["To"]      = to_email
msg.attach(MIMEText(html, "html", "utf-8"))

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
    print("✓ 이메일 발송 완료")
except Exception as e:
    print(f"이메일 발송 실패: {e}")
