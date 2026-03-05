# TikTok 콘텐츠 제작팀 — 로드맵

> 비즈니스 인사이트를 공유하는 TikTok 인플루언서 채널을 위한
> AI 기반 콘텐츠 기획·편집·업로드·분석 자동화 시스템

---

## 전체 구조

```
Phase 1 (2주)  →  Phase 2 (3주)  →  Phase 3 (2주)  →  Phase 4 (상시)
콘텐츠 기획        편집 자동화          API 업로드         분석·최적화
```

---

## Phase 1: 콘텐츠 기획 시스템

**목표**: 주간 5개 영상 패키지를 AI가 자동 생성

### 구현 항목

| 모듈 | 파일 | 설명 |
|---|---|---|
| 트렌드 리서치 | `pipeline/01_research.py` | WebSearch + Claude로 비즈니스 트렌드 수집 |
| 주제 선정 | `pipeline/02_planning.py` | 주간 콘텐츠 캘린더 자동 생성 |
| 스크립트 작성 | `pipeline/03_scripting.py` | 후크A/B + 본문 + CTA 자동 생성 |

### 출력 구조

```
outputs/YYYY-MM-DD/
├── scripts/
│   ├── 01_제목.txt      ← 프롬프터 형식 (후크A / 후크B / 본문 / CTA)
│   └── 02_제목.txt
├── metadata/
│   ├── 01_제목.json     ← 캡션, 해시태그(30개), 최적 발행 시간
│   └── 02_제목.json
└── schedule.json        ← 주간 발행 스케줄
```

### 스크립트 형식 (60초 기준)

```
[후크 A] 5초 — 강렬한 질문 또는 반전 진술
[후크 B] 5초 — A의 대안 (A/B 테스트용)
[본문]   45초 — 핵심 3포인트 (포인트당 15초)
[CTA]    10초 — 팔로우 유도 + 댓글 질문
```

### 마일스톤

- [ ] `01_research.py` 구현 — WebSearch 연동, 비즈니스 트렌드 수집
- [ ] `02_planning.py` 구현 — 5개 주제 선정 + 캘린더 생성
- [ ] `03_scripting.py` 구현 — Claude API로 스크립트 자동 생성
- [ ] 첫 번째 주간 패키지 생성 테스트

---

## Phase 2: 편집 자동화 시스템

**목표**: 촬영 raw 영상 → 업로드 가능한 완성본 자동 생성

**입력**: 사용자가 직접 촬영한 raw 영상 파일 (.mp4 등)

### 자동화 파이프라인

```
raw 영상
    ↓ (1) 음성 인식 — Whisper 로컬 실행
타임코드 포함 .srt 자막
    ↓ (2) 자막 합성 — FFmpeg burn-in
자막 입힌 영상
    ↓ (3) 무음 구간 제거 — FFmpeg silencedetect
트리밍된 영상
    ↓ (4) 속도 최적화 — 1.05~1.15배 가속
속도 조정된 영상
    ↓ (5) BGM 믹싱 — Pixabay 무료 BGM + FFmpeg
BGM 포함 영상
    ↓ (6) 썸네일 생성 — Pillow 제목 오버레이 A/B 2종
최종 영상 + 썸네일 A/B
    ↓ (7) B-roll 마킹 — 스크립트 분석 → 타임코드 JSON
편집 가이드
```

### 구현 항목

| 단계 | 기술 | 설명 |
|---|---|---|
| 음성 인식 | OpenAI Whisper (로컬) | GPU 가속, 인터넷 불필요 |
| 자막 합성 | FFmpeg `subtitles` 필터 | TikTok 최적: 맑은고딕 28pt, 흰색, 하단 중앙 |
| 무음 제거 | FFmpeg `silencedetect` | -50dB 이하 0.5초 이상 구간 트리밍 |
| 속도 조절 | FFmpeg `setpts`, `atempo` | 1.05~1.15배 (시청 완료율 향상) |
| BGM 믹싱 | FFmpeg `amix` | 보컬 -3dB, BGM -20dB |
| 썸네일 | Pillow + FontTools | 제목 오버레이 A/B 2종 |
| B-roll 마킹 | Claude API 분석 | 교체 필요 구간 타임코드 JSON |

### 출력 구조

```
outputs/YYYY-MM-DD/
├── final/
│   ├── 01_제목_edited.mp4       ← 업로드 바로 가능한 최종 영상
│   ├── 01_제목_thumbnail_A.jpg  ← 썸네일 A
│   └── 01_제목_thumbnail_B.jpg  ← 썸네일 B
├── subtitles/
│   └── 01_제목.srt              ← 자막 파일
└── broll/
    └── 01_제목_broll.json       ← B-roll 교체 가이드
```

### 마일스톤

- [ ] Whisper 로컬 설치 + .srt 생성 테스트
- [ ] FFmpeg 자막 burn-in 테스트 (한글 폰트 설정)
- [ ] 무음 제거 + 속도 조절 파이프라인
- [ ] BGM 믹싱 (Pixabay 다운로더 + 믹서)
- [ ] Pillow 썸네일 A/B 생성
- [ ] `04_editing.py` 전체 파이프라인 통합

---

## Phase 3: TikTok API 업로드 자동화

**목표**: 완성된 영상을 스케줄에 맞춰 자동 업로드

### 구현 항목

| 항목 | 설명 |
|---|---|
| TikTok for Developers 앱 등록 | Content Posting API 권한 신청 (앱 심사 필요) |
| 업로드 자동화 | `pipeline/05_upload.py` — 영상 + 캡션 + 해시태그 |
| 발행 스케줄 | `schedule.json` 기반 자동 예약 발행 |
| 에러 처리 | 업로드 실패 시 자동 재시도 (최대 3회) |

### TikTok API 절차

```
1. developers.tiktok.com 앱 등록
2. Content Posting API 권한 신청
3. OAuth 2.0 인증 구현
4. Video Upload API 연동
5. 영상 처리 완료 폴링
6. 발행 완료 확인
```

### 마일스톤

- [ ] TikTok 개발자 앱 등록 (수동)
- [ ] OAuth 인증 구현
- [ ] 영상 업로드 테스트
- [ ] 예약 발행 스케줄러 구현
- [ ] 에러 처리 + 알림 시스템

---

## Phase 4: 분석 및 전략 최적화

**목표**: 성과 데이터 → 다음 주 전략 자동 피드백

### 구현 항목

| 항목 | 설명 |
|---|---|
| Analytics 수집 | TikTok Analytics API — 조회수, 좋아요, 팔로워 |
| 주간 리포트 | `pipeline/06_analytics.py` — 자동 생성 마크다운 리포트 |
| A/B 테스트 분석 | 후크 A vs B 성과 비교 |
| 패턴 추출 | 고성과 영상 공통 요소 → 다음 주 기획 피드백 |

### 리포트 구조

```
outputs/YYYY-MM-DD/
└── report.md
    ├── 주간 성과 요약
    ├── 영상별 성과 (조회수, 좋아요, 댓글, 공유)
    ├── 후크 A/B 비교 분석
    ├── 고성과 패턴 분석
    └── 다음 주 전략 제안
```

### 마일스톤

- [ ] TikTok Analytics API 연동
- [ ] 주간 자동 리포트 생성
- [ ] A/B 테스트 자동 분석
- [ ] 전략 피드백 루프 구현

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| 언어 | Python 3.11+ |
| AI/LLM | Anthropic API (`claude-opus-4-6`, thinking 모드) |
| 음성 인식 | OpenAI Whisper (로컬, GPU 지원) |
| 영상 편집 | FFmpeg |
| 이미지 생성 | Pillow |
| 업로드 | TikTok Content Posting API v2 |
| 분석 | TikTok Analytics API |
| 설정 | JSON + 환경변수 |
| 인코딩 | UTF-8 (`-X utf8` 플래그, Windows cp949 우회) |

---

## 전체 마일스톤 타임라인

```
Week 1-2  : Phase 1 — 콘텐츠 기획 파이프라인 구축
Week 3-5  : Phase 2 — 편집 자동화 시스템 구축
Week 6-7  : Phase 3 — TikTok API 업로드 연동
Week 8+   : Phase 4 — 분석 + 최적화 (상시 운영)
```
