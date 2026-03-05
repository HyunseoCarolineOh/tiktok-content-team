"""
Phase 1 - Step 1: 트렌드 리서치

담당 에이전트: researcher.md
역할: 비즈니스 트렌드 수집 + 주제 풀 생성

파이프라인:
  WebSearch(비즈니스 트렌드) → Claude 분석 → 주제 평가 → 리서치 리포트 저장

입력:
  - 없음 (자동 실행)

출력:
  outputs/{date}/research_report.md   ← 트렌드 + 추천 주제 15개 이상
  outputs/{date}/topics_pool.json     ← 구조화된 주제 풀

사용법:
  python -X utf8 pipeline/01_research.py
  python -X utf8 pipeline/01_research.py --date 2026-03-01
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import load_config, setup_output_dir, load_agent_prompt, load_brand_guide, save_json
from pipeline import claude_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok 콘텐츠 트렌드 리서치")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--config", default="config/config.json")
    return parser.parse_args()


def search_business_trends(config: dict, target_date: str) -> list[dict]:
    """
    Claude API의 web_search 도구로 비즈니스 트렌드 수집.

    반환값:
        [{"title": str, "source": str, "summary": str}, ...]
    """
    sources = config.get("research", {}).get("sources", [])
    system_prompt = load_agent_prompt("researcher")

    user_message = f"""
오늘 날짜: {target_date}

다음 소스들에서 이번 주 주요 비즈니스/스타트업/경제 트렌드를 조사해주세요:
{', '.join(sources)}

트렌드 목록을 JSON 배열로 반환해주세요:
[
  {{
    "title": "트렌드 제목",
    "source": "출처",
    "summary": "2-3줄 요약",
    "keywords": ["키워드1", "키워드2"]
  }}
]

최소 20개의 트렌드를 수집해주세요. 순수 JSON만 반환하세요.
"""

    print("  [Claude] 비즈니스 트렌드 수집 중...")
    try:
        result = claude_client.call_json(system_prompt, user_message, max_tokens=8192)
        if isinstance(result, list):
            return result
        return result.get("trends", []) if isinstance(result, dict) else []
    except Exception as e:
        print(f"  경고: 트렌드 수집 실패 ({e}), 더미 데이터 사용")
        return _get_fallback_trends(target_date)


def _get_fallback_trends(target_date: str) -> list[dict]:
    """API 실패 시 사용할 기본 트렌드 목록."""
    return [
        {"title": "AI 스타트업 투자 급증", "source": "한국경제", "summary": "생성형 AI 스타트업에 대한 VC 투자가 전년 대비 3배 증가", "keywords": ["AI", "스타트업", "투자"]},
        {"title": "Z세대 소비 트렌드 변화", "source": "매일경제", "summary": "가성비보다 경험을 중시하는 Z세대 소비 패턴 분석", "keywords": ["Z세대", "소비", "트렌드"]},
        {"title": "SaaS 가격 전략 변화", "source": "TechCrunch", "summary": "사용량 기반 과금으로 전환하는 SaaS 기업 증가", "keywords": ["SaaS", "가격", "전략"]},
        {"title": "원격근무 생산성 연구", "source": "HBR", "summary": "하이브리드 근무 환경에서의 생산성 극대화 전략", "keywords": ["원격근무", "생산성", "하이브리드"]},
        {"title": "중소기업 디지털 전환", "source": "한국경제", "summary": "정부 지원 확대로 가속화되는 중소기업 디지털 전환", "keywords": ["디지털전환", "중소기업", "정부지원"]},
    ]


def evaluate_topics(trends: list[dict], config: dict) -> list[dict]:
    """
    Claude API로 주제 평가 (점수화).

    평가 기준: 시의성, 유니버설리티, 깊이, 바이럴성, 경쟁도 (각 5점)
    총점 20점 이상 → 우선 기획 추천

    반환값:
        [{"topic": str, "angle": str, "score": int, "priority": str, "keywords": list}, ...]
    """
    system_prompt = load_agent_prompt("researcher")
    min_score = config.get("research", {}).get("min_score_threshold", 20)
    topics_needed = config.get("research", {}).get("topics_per_week", 15)

    trends_json = json.dumps(trends, ensure_ascii=False, indent=2)
    user_message = f"""
다음 비즈니스 트렌드들을 TikTok 콘텐츠 주제로 평가해주세요.

트렌드 목록:
{trends_json}

각 트렌드에 대해 다음 기준으로 1~5점 평가:
- 시의성: 지금 이 주제가 뜨거운가?
- 유니버설리티: 많은 사람이 공감할 수 있는가?
- 깊이: 60초 안에 의미 있는 인사이트가 나오는가?
- 바이럴성: 공유·저장하고 싶은 내용인가?
- 경쟁도: 이미 많이 다뤄진 주제인가? (낮을수록 좋음, 낮으면 5점)

결과를 JSON 배열로 반환 (상위 {topics_needed}개, 점수 높은 순):
[
  {{
    "topic": "TikTok 콘텐츠 제목 (15자 이내)",
    "angle": "독특한 각도/관점",
    "keywords": ["핵심 키워드"],
    "scores": {{"시의성": 4, "유니버설리티": 5, "깊이": 4, "바이럴성": 4, "경쟁도": 3}},
    "score": 20,
    "priority": "high"
  }}
]

priority: score >= {min_score}이면 "high", 15~19면 "medium", 이하는 "low"
순수 JSON만 반환하세요.
"""

    print("  [Claude] 주제 평가 중...")
    try:
        result = claude_client.call_json(system_prompt, user_message, max_tokens=8192)
        if isinstance(result, list):
            return result
        return result.get("topics", []) if isinstance(result, dict) else []
    except Exception as e:
        print(f"  경고: 주제 평가 실패 ({e}), 기본 주제 생성")
        return _get_fallback_topics(trends)


def _get_fallback_topics(trends: list[dict]) -> list[dict]:
    """평가 실패 시 기본 주제 생성."""
    topics = []
    for i, trend in enumerate(trends[:15]):
        topics.append({
            "topic": trend.get("title", f"주제 {i+1}"),
            "angle": "실전 적용 관점",
            "keywords": trend.get("keywords", []),
            "scores": {"시의성": 4, "유니버설리티": 4, "깊이": 4, "바이럴성": 3, "경쟁도": 3},
            "score": 18,
            "priority": "medium",
        })
    return topics


def generate_research_report(topics: list[dict], trends: list[dict], target_date: str, output_dir: Path) -> None:
    """주간 리서치 리포트 마크다운 저장."""
    lines = [
        f"## 주간 트렌드 리포트 — {target_date}",
        "",
        "### 핫 트렌드 (Top 5)",
    ]
    for i, trend in enumerate(trends[:5], 1):
        lines.append(f"{i}. **{trend.get('title', '')}** — {trend.get('source', '')} — {trend.get('summary', '')}")

    lines += [
        "",
        "### 추천 주제 풀",
        "| # | 주제 | 각도 | 점수 | 우선순위 |",
        "|---|---|---|---|---|",
    ]
    for i, topic in enumerate(topics, 1):
        lines.append(
            f"| {i} | {topic.get('topic', '')} | {topic.get('angle', '')} "
            f"| {topic.get('score', 0)} | {topic.get('priority', '')} |"
        )

    report_path = output_dir / "research_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → {report_path}")


def save_topics_pool(topics: list[dict], output_dir: Path) -> None:
    """주제 풀 JSON 저장."""
    path = output_dir / "topics_pool.json"
    save_json(topics, path)
    print(f"  → {path}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    output_dir = setup_output_dir(config["pipeline"]["output_base_dir"], args.date)

    print(f"[01_research] 트렌드 리서치 시작 — {args.date}")

    trends = search_business_trends(config, args.date)
    print(f"  {len(trends)}개 트렌드 수집됨")

    topics = evaluate_topics(trends, config)
    print(f"  {len(topics)}개 주제 평가됨")

    generate_research_report(topics, trends, args.date, output_dir)
    save_topics_pool(topics, output_dir)

    print(f"[01_research] 완료 — {len(topics)}개 주제 발굴")


if __name__ == "__main__":
    main()
