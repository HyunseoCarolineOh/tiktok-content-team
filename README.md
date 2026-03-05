# TikTok 콘텐츠 제작팀

> 비즈니스 인사이트를 공유하는 TikTok 인플루언서를 위한 AI 기반 콘텐츠 파이프라인

---

## 개요

이 프로젝트는 비즈니스 트렌드 리서치부터 영상 편집, 업로드, 성과 분석까지 TikTok 콘텐츠 제작의 전 과정을 자동화합니다.

```
트렌드 리서치 → 스크립트 생성 → 편집 자동화 → TikTok 업로드 → 성과 분석
```

---

## 빠른 시작

### 1. 환경 설정

```powershell
# 의존성 설치 (Windows PowerShell)
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

### 2. 환경변수 설정

```bash
# .env 파일 생성 또는 시스템 환경변수 설정
ANTHROPIC_API_KEY=your_key_here
TIKTOK_CLIENT_KEY=your_key_here
TIKTOK_CLIENT_SECRET=your_key_here
```

### 3. Phase 1 실행 — 주간 콘텐츠 기획

```bash
# 트렌드 리서치
python -X utf8 pipeline/01_research.py

# 주간 콘텐츠 캘린더 생성
python -X utf8 pipeline/02_planning.py

# 스크립트 자동 생성
python -X utf8 pipeline/03_scripting.py --date 2026-03-01
```

### 4. Phase 2 실행 — 편집 자동화

```bash
# raw 영상을 outputs/2026-03-01/raw/ 폴더에 넣은 후:
python -X utf8 pipeline/04_editing.py --date 2026-03-01
```

---

## 출력 구조

```
outputs/YYYY-MM-DD/
├── scripts/          ← 스크립트 텍스트 파일
├── metadata/         ← 캡션·해시태그·발행시간 JSON
├── subtitles/        ← .srt 자막 파일
├── final/            ← 편집 완성본 영상 + 썸네일 A/B
├── broll/            ← B-roll 교체 가이드 JSON
└── report.md         ← 주간 성과 리포트
```

---

## 에이전트 팀

| 에이전트 | 역할 |
|---|---|
| Content Director | 브랜드 일관성 + 주간 전략 |
| Researcher | 트렌드 수집 + 주제 발굴 |
| Scriptwriter | 후크·본문·CTA 작성 |
| Editor | 자막·썸네일·BGM·편집 |
| Analyst | 성과 분석 + 전략 피드백 |

자세한 내용은 `agents/` 폴더 참조.

---

## 기술 스택

- **Python 3.11+**
- **Claude API** (`claude-opus-4-6`, thinking 모드)
- **Whisper** — 음성 인식 (로컬 실행)
- **FFmpeg** — 영상 편집
- **Pillow** — 썸네일 생성
- **TikTok API v2** — 업로드 + Analytics

---

## 로드맵

상세 내용은 [ROADMAP.md](ROADMAP.md) 참조.
