# 한화첨단소재 Market Intelligence Dashboard

AI 기반 자동차 산업 시장 인텔리전스 리포트 시스템

---

## 🚀 GitHub Pages 배포 (5분, 완전 무료)

### 1단계 — GitHub 저장소 생성

1. [github.com](https://github.com) 로그인 (없으면 무료 가입)
2. 우측 상단 **`+`** → **New repository**
3. Repository name: `hanwha-intel` (또는 원하는 이름)
4. **Public** 선택 (Pages 무료 사용 조건)
5. **Create repository** 클릭

---

### 2단계 — 파일 업로드

1. 생성된 저장소에서 **`Add file`** → **`Upload files`** 클릭
2. `index.html` 파일을 드래그 앤 드롭
3. **`Commit changes`** 클릭

---

### 3단계 — GitHub Pages 활성화

1. 저장소 **Settings** 탭 클릭
2. 왼쪽 메뉴 **Pages** 클릭
3. **Source**: `Deploy from a branch` 선택
4. **Branch**: `main` / `/ (root)` 선택
5. **Save** 클릭
6. 1~2분 후 페이지 URL 발급:
   ```
   https://[your-username].github.io/hanwha-intel/
   ```

---

### 4단계 — 사용 시작

1. 발급된 URL 접속
2. [Anthropic Console](https://console.anthropic.com/settings/keys)에서 API 키 발급
3. 대시보드 상단 API 키 입력 → **저장**
4. 분석 버튼 클릭 → 완료!

---

## 💰 비용 안내

| 사용 패턴 | 월 예상 비용 |
|---|---|
| 주 1회 리포트 (Haiku 모델) | $0.20 ~ $0.50 |
| 주 3회 리포트 | $0.60 ~ $1.50 |
| 매일 리포트 | $3 ~ $7 |

- 신규 가입 시 **무료 크레딧 $5** 제공 (약 3~6개월 사용 가능)
- API 키는 브라우저 localStorage에만 저장, 서버 전송 없음

---

## 🔄 자동 정기 발송 추가 (선택)

GitHub Actions로 매주 월요일 자동 분석 + 이메일 발송을 추가하려면:

`.github/workflows/weekly-report.yml` 파일 생성:

```yaml
name: Weekly Intelligence Report

on:
  schedule:
    - cron: '0 22 * * 0'  # 매주 월요일 오전 7시 (KST = UTC+9)
  workflow_dispatch:       # 수동 실행 가능

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install anthropic
      - run: python scripts/weekly_report.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
```

GitHub 저장소 **Settings → Secrets → Actions**에서:
- `ANTHROPIC_API_KEY`: Anthropic API 키
- `EMAIL_TO`: 수신 이메일 주소

---

## 📊 분석 모듈

| 모듈 | 내용 |
|---|---|
| **주간 종합** | 최근 1주 글로벌 자동차/EV 시장 전체 동향 |
| **EV / 정책** | 전기차 판매 + 각국 규제 변화 (IRA, EU, 중국) |
| **OEM 동향** | 현대/BMW/GM/Tesla/BYD 신차·플랫폼 동향 |
| **소재 기술** | CFRP/GFRP 트렌드 + 도레이·Hexcel 경쟁사 동향 |
| **직접 질문** | 자유 형식 질문 입력 |

---

## 🛠 커스터마이징

`index.html` 내 `SYSTEM_PROMPT` 수정으로 분석 방향 조정 가능:

```javascript
const SYSTEM_PROMPT = `
  // 여기에 회사 특화 분석 지침 추가
  // 예: 특정 OEM 고객사 정보, 중점 관리 소재, 경쟁사 목록 등
`;
```
