# TikTok 콘텐츠 제작팀 — 환경 설정 스크립트
# 사용법: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

Write-Host "=== TikTok 콘텐츠 제작팀 환경 설정 ===" -ForegroundColor Cyan
Write-Host ""

# ─── 1. Python 버전 확인 ────────────────────────────────────────
Write-Host "[1/6] Python 버전 확인..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "오류: Python이 설치되지 않았습니다. Python 3.11+ 설치 후 다시 실행하세요." -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ $pythonVersion" -ForegroundColor Green

# ─── 2. pip 의존성 설치 ─────────────────────────────────────────
Write-Host "[2/6] Python 의존성 설치..." -ForegroundColor Yellow

$packages = @(
    "anthropic",           # Claude API
    "openai-whisper",      # 음성 인식
    "Pillow",              # 썸네일 생성
    "requests",            # HTTP 클라이언트
    "python-dotenv"        # 환경변수 로드
)

foreach ($pkg in $packages) {
    Write-Host "  설치 중: $pkg"
    pip install $pkg -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  경고: $pkg 설치 실패" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ $pkg" -ForegroundColor Green
    }
}

# ─── 3. FFmpeg 설치 확인 ────────────────────────────────────────
Write-Host "[3/6] FFmpeg 확인..." -ForegroundColor Yellow
$ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  경고: FFmpeg가 설치되지 않았습니다." -ForegroundColor Yellow
    Write-Host "  설치 방법: https://ffmpeg.org/download.html" -ForegroundColor Gray
    Write-Host "  또는 winget 사용: winget install Gyan.FFmpeg" -ForegroundColor Gray
} else {
    Write-Host "  ✓ FFmpeg 감지됨" -ForegroundColor Green
}

# ─── 4. CUDA (GPU) 확인 ─────────────────────────────────────────
Write-Host "[4/6] GPU(CUDA) 확인..." -ForegroundColor Yellow
$cudaCheck = python -c "import torch; print(torch.cuda.is_available())" 2>&1
if ($cudaCheck -eq "True") {
    Write-Host "  ✓ CUDA GPU 사용 가능 — Whisper 가속 활성화" -ForegroundColor Green
} else {
    Write-Host "  정보: CUDA GPU 없음 — Whisper CPU 모드로 실행 (느림)" -ForegroundColor Yellow
    Write-Host "  GPU 가속을 원하면 PyTorch CUDA 버전 설치 필요" -ForegroundColor Gray
}

# ─── 5. 출력 폴더 생성 ──────────────────────────────────────────
Write-Host "[5/6] 출력 폴더 생성..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "outputs" | Out-Null
Write-Host "  ✓ outputs/ 폴더 준비 완료" -ForegroundColor Green

# ─── 6. 환경변수 안내 ───────────────────────────────────────────
Write-Host "[6/6] 환경변수 설정 안내..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  다음 환경변수를 설정하세요:" -ForegroundColor Cyan
Write-Host "  (시스템 환경변수 또는 프로젝트 루트의 .env 파일)" -ForegroundColor Gray
Write-Host ""
Write-Host "  ANTHROPIC_API_KEY=sk-ant-..." -ForegroundColor White
Write-Host "  TIKTOK_CLIENT_KEY=..." -ForegroundColor White
Write-Host "  TIKTOK_CLIENT_SECRET=..." -ForegroundColor White
Write-Host ""
Write-Host "  .env 파일 예시:" -ForegroundColor Gray
Write-Host "  echo 'ANTHROPIC_API_KEY=your_key' > .env" -ForegroundColor Gray

# ─── 완료 ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== 설정 완료 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 명령으로 Phase 1을 시작하세요:" -ForegroundColor White
Write-Host "  python -X utf8 pipeline/01_research.py" -ForegroundColor Green
Write-Host ""
