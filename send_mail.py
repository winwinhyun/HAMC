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
except Exception:
    summary = "분석이 완료되었습니다."
    impact  = "MEDIUM"

subject = f"[한화첨단소재 Intelligence] 분석 갱신 완료 — {now}"

html = f"""
<html><body style="font-family:'Apple SD Gothic Neo',sans-serif;background:#faf8f4;margin:0;padding:20px">
<div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08)">
  <div style="background:#1a1814;padding:24px 28px">
    <div style="display:inline-block;width:36px;height:36px;border-radius:8px;background:#e8541a;text-align:center;line-height:36px;font-size:16px;color:#fff;font-weight:700;vertical-align:middle;margin-right:12px">H</div>
    <span style="color:#fff;font-size:15px;font-weight:700;vertical-align:middle">Hanwha Advanced Materials</span>
    <div style="color:#9c9288;font-size:10px;letter-spacing:.12em;text-transform:uppercase;margin-top:6px">Market Intelligence · AI Powered</div>
  </div>
  <div style="padding:28px">
    <div style="font-size:10px;font-weight:600;color:#e8541a;letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px">Intelligence Report</div>
    <div style="font-size:20px;font-weight:700;color:#1a1814;margin-bottom:4px">분석 갱신 완료</div>
    <div style="font-size:12px;color:#9c9288;margin-bottom:20px">{now} 기준</div>
    <div style="background:#fff4ef;border-left:3px solid #e8541a;border-radius:8px;padding:14px 16px;margin-bottom:20px">
      <div style="font-size:10px;font-weight:600;color:#e8541a;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px">Executive Summary</div>
      <div style="font-size:13px;color:#3d3830;line-height:1.7">{summary}</div>
    </div>
    <div style="display:flex;gap:10px;margin-bottom:24px">
      <div style="background:#f2ede6;border-radius:8px;padding:10px 14px;flex:1">
        <div style="font-size:10px;color:#9c9288;margin-bottom:4px">Impact Score</div>
        <div style="font-size:16px;font-weight:700;color:#dc2626">{impact}</div>
      </div>
      <div style="background:#f2ede6;border-radius:8px;padding:10px 14px;flex:1">
        <div style="font-size:10px;color:#9c9288;margin-bottom:4px">분석 모듈</div>
        <div style="font-size:14px;font-weight:600;color:#1a1814">4개 완료</div>
      </div>
      <div style="background:#f2ede6;border-radius:8px;padding:10px 14px;flex:1">
        <div style="font-size:10px;color:#9c9288;margin-bottom:4px">AI 모델</div>
        <div style="font-size:12px;font-weight:600;color:#1a1814">Claude Sonnet</div>
      </div>
    </div>
    <a href="https://winwinhyun.github.io/HAMC/" style="display:block;background:#e8541a;color:#fff;text-align:center;padding:14px;border-radius:10px;text-decoration:none;font-weight:600;font-size:14px">
      Intelligence Report 보기 →
    </a>
  </div>
  <div style="background:#f2ede6;padding:14px 28px;font-size:11px;color:#9c9288;text-align:center">
    자동 발송 · 3시간마다 갱신 · Powered by Claude AI
  </div>
</div>
</body></html>"""

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
