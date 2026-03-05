# TikTok 콘텐츠 제작팀 — AI 지침

## 프로젝트 개요

비즈니스 인사이트를 공유하는 TikTok 인플루언서 채널을 위한 AI 기반 콘텐츠 파이프라인.
Phase 1(기획) → Phase 2(편집) → Phase 3(업로드) → Phase 4(분석) 순서로 구현.

## 에이전트 매핑 테이블

| 키워드 | 에이전트 | 파일 |
|---|---|---|
| 콘텐츠 전략, 방향, 브랜드, 주간 기획 | Content Director | `agents/content-director.md` |
| 트렌드, 리서치, 주제 발굴, 경쟁 채널 | Researcher | `agents/researcher.md` |
| 스크립트, 후크, CTA, 대사, 말투 | Scriptwriter | `agents/scriptwriter.md` |
| 편집, 자막, 썸네일, BGM, 영상 | Editor | `agents/editor.md` |
| 성과, 분석, 통계, 최적화, A/B | Analyst | `agents/analyst.md` |

## 작업 규칙

1. **출력 폴더**: 모든 생성 파일은 `outputs/YYYY-MM-DD/` 하위에 저장
2. **인코딩**: Python 실행 시 반드시 `-X utf8` 플래그 사용 (Windows cp949 우회)
3. **API 키**: `config/config.json`에서 환경변수명 참조 — 키 값은 절대 하드코딩 금지
4. **파일 네이밍**: `{인덱스}_{제목}` 형식 유지 (예: `01_창업자가몰랐던것.txt`)
5. **스크립트 형식**: 후크A / 후크B / 본문 / CTA 구분자 유지

## 디렉토리 구조

```
tiktok-content-team/
├── ROADMAP.md          ← 4단계 상세 로드맵
├── CLAUDE.md           ← 이 파일
├── README.md           ← 빠른 시작 가이드
├── agents/             ← 역할별 에이전트 정의
├── pipeline/           ← 단계별 실행 모듈
├── config/             ← 설정 파일 (API 키는 환경변수)
├── outputs/            ← 생성된 콘텐츠 (gitignore 권장)
└── scripts/            ← 환경 설정 스크립트
```

## 현재 구현 상태

- [x] 프로젝트 구조 생성
- [x] ROADMAP.md 작성
- [x] 에이전트 정의 (5개)
- [x] 설정 파일 템플릿
- [x] 파이프라인 스켈레톤
- [ ] Phase 1 실제 구현
- [ ] Phase 2 실제 구현
- [ ] Phase 3 실제 구현
- [ ] Phase 4 실제 구현
