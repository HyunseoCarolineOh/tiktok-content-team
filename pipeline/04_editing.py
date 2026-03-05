"""
Phase 2: 영상 편집 자동화

담당 에이전트: editor.md
역할: raw 영상 → Whisper 자막 → FFmpeg 편집 → 썸네일 A/B → B-roll 마킹

파이프라인:
  raw 영상(.mp4)
    → Whisper 음성 인식 → .srt 자막
    → FFmpeg 자막 burn-in
    → FFmpeg 무음 제거
    → FFmpeg 속도 조절 (1.1배)
    → FFmpeg BGM 믹싱
    → Pillow 썸네일 A/B 생성
    → Claude B-roll 마킹 분석

입력:
  outputs/{date}/raw/*.mp4           ← 사용자가 직접 촬영한 원본 영상

출력:
  outputs/{date}/subtitles/*.srt     ← 타임코드 포함 자막
  outputs/{date}/final/*_edited.mp4  ← 편집 완성본
  outputs/{date}/final/*_thumb_A.jpg ← 썸네일 A
  outputs/{date}/final/*_thumb_B.jpg ← 썸네일 B
  outputs/{date}/broll/*_broll.json  ← B-roll 교체 가이드

사용법:
  python -X utf8 pipeline/04_editing.py
  python -X utf8 pipeline/04_editing.py --date 2026-03-01
  python -X utf8 pipeline/04_editing.py --file 01_창업자가몰랐던것.mp4
"""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import load_config, setup_output_dir, load_agent_prompt, save_json
from pipeline import claude_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok 영상 편집 자동화")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--config", default="config/config.json")
    parser.add_argument("--file", help="특정 영상 파일만 처리")
    parser.add_argument("--skip-whisper", action="store_true")
    return parser.parse_args()


def transcribe_with_whisper(video_path: Path, srt_path: Path, config: dict) -> Path:
    """OpenAI Whisper로 음성 인식 → .srt 자막 생성."""
    import whisper

    cfg = config.get("editing", {}).get("whisper", {})
    model_name = cfg.get("model", "medium")
    language = cfg.get("language", "ko")

    print(f"    [Whisper] 모델 로드: {model_name}")
    model = whisper.load_model(model_name)

    print(f"    [Whisper] 음성 인식 중: {video_path.name}")
    result = model.transcribe(str(video_path), language=language, verbose=False)

    # SRT 형식으로 저장
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            start = _seconds_to_srt_time(seg["start"])
            end = _seconds_to_srt_time(seg["end"])
            f.write(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n\n")

    print(f"    → {srt_path}")
    return srt_path


def _seconds_to_srt_time(seconds: float) -> str:
    """초 → SRT 타임코드 형식 (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def burn_subtitles(video_path: Path, srt_path: Path, output_path: Path, config: dict) -> Path:
    """FFmpeg로 자막 burn-in."""
    cfg = config.get("editing", {}).get("ffmpeg", {})
    font = cfg.get("subtitle_font", "Malgun Gothic")
    size = cfg.get("subtitle_size", 28)
    color = cfg.get("subtitle_color", "white")
    outline = cfg.get("subtitle_outline_color", "black")
    outline_w = cfg.get("subtitle_outline_width", 2)
    margin_v = cfg.get("subtitle_margin_v", 150)

    # SRT 경로의 역슬래시를 이스케이프 (Windows FFmpeg)
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", (
            f"subtitles={srt_escaped}:force_style='"
            f"FontName={font},FontSize={size},"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"Outline={outline_w},MarginV={margin_v}'"
        ),
        "-c:a", "copy",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "자막 burn-in")
    return output_path


def remove_silence(video_path: Path, output_path: Path, config: dict) -> Path:
    """FFmpeg silencedetect로 무음 구간 감지 후 제거."""
    cfg = config.get("editing", {}).get("ffmpeg", {})
    threshold = cfg.get("silence_threshold_db", -50)
    min_dur = cfg.get("silence_min_duration", 0.5)

    # 1단계: 무음 구간 감지
    detect_cmd = [
        "ffmpeg", "-i", str(video_path),
        "-af", f"silencedetect=noise={threshold}dB:d={min_dur}",
        "-f", "null", "-",
    ]
    result = subprocess.run(detect_cmd, capture_output=True, text=True)
    stderr = result.stderr

    # 무음 구간 파싱
    import re
    starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", stderr)]

    if not starts:
        # 무음 없으면 그냥 복사
        import shutil
        shutil.copy2(str(video_path), str(output_path))
        return output_path

    # 유음 구간 계산
    keep_segments = []

    # 영상 전체 길이 추출
    duration_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True
    )
    total_duration = float(duration_result.stdout.strip() or "0")

    prev_end = 0.0
    for s, e in zip(starts, ends):
        if s > prev_end + 0.1:
            keep_segments.append((prev_end, s))
        prev_end = e
    if prev_end < total_duration - 0.1:
        keep_segments.append((prev_end, total_duration))

    if not keep_segments:
        import shutil
        shutil.copy2(str(video_path), str(output_path))
        return output_path

    # concat filter 생성
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        concat_file = f.name
        for start, end in keep_segments:
            f.write(f"file '{str(video_path).replace(chr(92), '/')}'\n")
            f.write(f"inpoint {start}\n")
            f.write(f"outpoint {end}\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", str(output_path)]
    _run_ffmpeg(cmd, "무음 제거")
    return output_path


def adjust_speed(video_path: Path, output_path: Path, config: dict) -> Path:
    """FFmpeg로 속도 조절."""
    cfg = config.get("editing", {}).get("ffmpeg", {})
    factor = cfg.get("speed_factor", 1.1)
    pts_factor = round(1.0 / factor, 6)

    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-filter_complex", f"[0:v]setpts={pts_factor}*PTS[v];[0:a]atempo={factor}[a]",
        "-map", "[v]", "-map", "[a]",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "속도 조절")
    return output_path


def mix_bgm(video_path: Path, output_path: Path, config: dict) -> Path:
    """
    BGM 없이 원본 오디오만 유지 (BGM 파일이 없는 경우 skip).

    실제 운영 시: outputs/{date}/bgm.mp3 파일을 수동으로 배치하면 믹싱.
    """
    cfg = config.get("editing", {}).get("ffmpeg", {})
    vocal_vol = cfg.get("vocal_volume", 0.7)
    bgm_vol = cfg.get("bgm_volume", 0.1)

    # BGM 파일 탐색
    bgm_candidates = list(video_path.parent.parent.glob("bgm.*"))
    if not bgm_candidates:
        # BGM 없으면 볼륨만 조절
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-af", f"volume={vocal_vol}",
            "-c:v", "copy",
            str(output_path),
        ]
    else:
        bgm_path = bgm_candidates[0]
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(bgm_path),
            "-filter_complex",
            f"[0:a]volume={vocal_vol}[vocal];[1:a]volume={bgm_vol}[bgm];[vocal][bgm]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy",
            str(output_path),
        ]
    _run_ffmpeg(cmd, "BGM 믹싱")
    return output_path


def generate_thumbnails(
    video_path: Path, title: str, output_dir: Path, config: dict, brand_guide: dict
) -> tuple[Path, Path]:
    """Pillow로 썸네일 A/B 2종 생성."""
    from PIL import Image, ImageDraw, ImageFont
    import struct

    cfg = config.get("editing", {}).get("thumbnail", {})
    colors = brand_guide.get("visual_style", {}).get("color_palette", {})
    width = cfg.get("width", 1080)
    height = cfg.get("height", 1920)
    font_size = cfg.get("font_size", 80)
    text_color = cfg.get("text_color", "white")

    primary_color = colors.get("primary", "#1A1A2E")
    highlight_color = colors.get("highlight", "#E94560")

    def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
        h = hex_str.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore

    # 중간 프레임 캡처 (B타입용)
    frame_path = output_dir / f"{video_path.stem}_frame.jpg"
    duration_result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True
    )
    try:
        total = float(duration_result.stdout.strip() or "30")
        mid = total / 2
    except ValueError:
        mid = 15.0

    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(mid), "-i", str(video_path),
         "-frames:v", "1", str(frame_path)],
        capture_output=True
    )

    # 폰트 로드
    try:
        font = ImageFont.truetype("malgunbd.ttf", font_size)
        small_font = ImageFont.truetype("malgunbd.ttf", 40)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # ── 썸네일 A: 그라디언트 배경 + 중앙 텍스트 ──
    img_a = Image.new("RGB", (width, height))
    draw_a = ImageDraw.Draw(img_a)
    p_rgb = hex_to_rgb(primary_color)
    h_rgb = hex_to_rgb(highlight_color)
    for y in range(height):
        ratio = y / height
        r = int(p_rgb[0] + (h_rgb[0] - p_rgb[0]) * ratio)
        g = int(p_rgb[1] + (h_rgb[1] - p_rgb[1]) * ratio)
        b = int(p_rgb[2] + (h_rgb[2] - p_rgb[2]) * ratio)
        draw_a.line([(0, y), (width, y)], fill=(r, g, b))

    # 텍스트 래핑 (15자 기준 줄바꿈)
    words = title
    wrapped = "\n".join([words[i:i+12] for i in range(0, len(words), 12)])
    bbox = draw_a.textbbox((0, 0), wrapped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2
    # 그림자
    draw_a.text((x + 3, y + 3), wrapped, font=font, fill=(0, 0, 0, 180))
    draw_a.text((x, y), wrapped, font=font, fill=text_color)

    thumb_a = output_dir / f"{video_path.stem}_thumb_A.jpg"
    img_a.save(str(thumb_a), "JPEG", quality=95)

    # ── 썸네일 B: 영상 프레임 배경 + 상단 텍스트 ──
    if frame_path.exists():
        img_b = Image.open(str(frame_path)).resize((width, height))
    else:
        img_b = Image.new("RGB", (width, height), hex_to_rgb(primary_color))

    draw_b = ImageDraw.Draw(img_b)
    # 상단 반투명 오버레이
    overlay = Image.new("RGBA", (width, 300), (0, 0, 0, 180))
    img_b.paste(overlay, (0, 0), overlay)
    draw_b.text((50, 50), title[:20], font=font, fill=text_color)

    thumb_b = output_dir / f"{video_path.stem}_thumb_B.jpg"
    img_b.save(str(thumb_b), "JPEG", quality=95)

    print(f"    → {thumb_a.name}")
    print(f"    → {thumb_b.name}")

    # 임시 프레임 파일 삭제
    frame_path.unlink(missing_ok=True)
    return thumb_a, thumb_b


def analyze_broll(srt_path: Path, config: dict) -> dict:
    """Claude API로 B-roll 필요 구간 분석."""
    if not srt_path or not srt_path.exists():
        return {"segments": []}

    system_prompt = load_agent_prompt("editor")
    srt_content = srt_path.read_text(encoding="utf-8")

    user_message = f"""
다음 자막 파일에서 B-roll 영상이 필요한 구간을 분석해주세요.

자막:
{srt_content}

B-roll이 필요한 구간 기준:
- 지시어 사용 구간 ("이것", "저런", "이렇게" 등)
- 추상 개념 설명 구간 (수치, 통계, 차트 필요)
- 감정 전환 구간

JSON 형식으로 반환:
{{
  "segments": [
    {{
      "start": "00:00:10,000",
      "end": "00:00:15,000",
      "reason": "이유",
      "suggested_broll": "추천 B-roll 유형"
    }}
  ]
}}

순수 JSON만 반환하세요.
"""
    try:
        return claude_client.call_json(system_prompt, user_message, max_tokens=2048)
    except Exception as e:
        print(f"  경고: B-roll 분석 실패 ({e})")
        return {"segments": []}


def _run_ffmpeg(cmd: list[str], step_name: str) -> None:
    """FFmpeg 명령 실행 (오류 시 경고 출력)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    경고: FFmpeg {step_name} 실패")
        print(f"    {result.stderr[-500:]}")


def process_video(video_path: Path, output_dir: Path, config: dict, brand_guide: dict, skip_whisper: bool = False) -> None:
    """단일 영상 전체 편집 파이프라인 실행."""
    stem = video_path.stem
    subtitles_dir = output_dir / "subtitles"
    final_dir = output_dir / "final"
    broll_dir = output_dir / "broll"
    for d in [subtitles_dir, final_dir, broll_dir]:
        d.mkdir(parents=True, exist_ok=True)

    srt_path = subtitles_dir / f"{stem}.srt"

    if not skip_whisper:
        print(f"  [Whisper] 음성 인식 중...")
        transcribe_with_whisper(video_path, srt_path, config)
    else:
        if not srt_path.exists():
            print(f"  경고: SRT 파일 없음 ({srt_path}), Whisper 단계 건너뜀")

    print(f"  [FFmpeg] 자막 합성 중...")
    sub_path = final_dir / f"{stem}_sub.mp4"
    if srt_path.exists():
        burn_subtitles(video_path, srt_path, sub_path, config)
    else:
        import shutil
        shutil.copy2(str(video_path), str(sub_path))

    print(f"  [FFmpeg] 무음 제거 중...")
    trimmed_path = final_dir / f"{stem}_trimmed.mp4"
    remove_silence(sub_path, trimmed_path, config)

    print(f"  [FFmpeg] 속도 조절 중...")
    speed_path = final_dir / f"{stem}_speed.mp4"
    adjust_speed(trimmed_path, speed_path, config)

    print(f"  [FFmpeg] BGM 믹싱 중...")
    final_path = final_dir / f"{stem}_edited.mp4"
    mix_bgm(speed_path, final_path, config)

    print(f"  [Pillow] 썸네일 A/B 생성 중...")
    generate_thumbnails(final_path, stem, final_dir, config, brand_guide)

    print(f"  [Claude] B-roll 분석 중...")
    broll = analyze_broll(srt_path, config)
    broll_path = broll_dir / f"{stem}_broll.json"
    save_json(broll, broll_path)
    print(f"    → {broll_path.name}")

    # 중간 파일 정리
    for temp in [sub_path, trimmed_path, speed_path]:
        temp.unlink(missing_ok=True)

    print(f"  ✓ 완료: {final_path.name}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    brand_guide = __import__("pipeline.utils", fromlist=["load_brand_guide"]).load_brand_guide()
    output_dir = setup_output_dir(config["pipeline"]["output_base_dir"], args.date)
    raw_dir = output_dir / "raw"

    print(f"[04_editing] 영상 편집 시작 — {args.date}")

    if not raw_dir.exists():
        print(f"오류: raw 영상 폴더가 없습니다 — {raw_dir}")
        print("촬영한 영상을 해당 폴더에 넣고 다시 실행하세요.")
        return

    if args.file:
        videos = [raw_dir / args.file]
    else:
        videos = list(raw_dir.glob("*.mp4"))

    if not videos:
        print(f"처리할 영상이 없습니다 — {raw_dir}")
        return

    print(f"처리할 영상: {len(videos)}개")
    for video in videos:
        print(f"\n[{video.name}] 편집 중...")
        process_video(video, output_dir, config, brand_guide, args.skip_whisper)

    print(f"\n[04_editing] 모든 편집 완료")
    print(f"  → {output_dir}/final/")


if __name__ == "__main__":
    main()
