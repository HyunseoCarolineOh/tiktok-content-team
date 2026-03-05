# TikTok 어드민 — 개발 모드 시작
# FastAPI (8000) + Vite (5173) 동시 실행

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $PSScriptRoot "backend"
$FrontendDir = Join-Path $PSScriptRoot "frontend"

Write-Host "=== TikTok 콘텐츠 어드민 (개발 모드) ===" -ForegroundColor Cyan
Write-Host ""

# 의존성 확인
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "오류: Python이 설치되어 있지 않습니다." -ForegroundColor Red
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "오류: Node.js/npm이 설치되어 있지 않습니다." -ForegroundColor Red
    exit 1
}

# 프론트엔드 의존성 설치
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "프론트엔드 의존성 설치 중..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

# 백엔드 의존성 설치
Write-Host "백엔드 의존성 확인 중..." -ForegroundColor Yellow
Push-Location $BackendDir
pip install -r requirements.txt -q
Pop-Location

Write-Host ""
Write-Host "서버 시작 중..." -ForegroundColor Green
Write-Host "  백엔드: http://localhost:8000" -ForegroundColor White
Write-Host "  프론트엔드: http://localhost:5173" -ForegroundColor White
Write-Host "  API 문서: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "종료: Ctrl+C" -ForegroundColor Gray

# 두 서버 동시 시작
$BackendJob = Start-Job -ScriptBlock {
    param($dir, $root)
    Set-Location $dir
    $env:PYTHONPATH = $root
    python -X utf8 -m uvicorn main:app --reload --port 8000
} -ArgumentList $BackendDir, $ProjectRoot

$FrontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    npm run dev
} -ArgumentList $FrontendDir

# 로그 스트리밍
try {
    while ($true) {
        Receive-Job $BackendJob | ForEach-Object { Write-Host "[Backend] $_" -ForegroundColor Blue }
        Receive-Job $FrontendJob | ForEach-Object { Write-Host "[Frontend] $_" -ForegroundColor Green }
        Start-Sleep -Milliseconds 500
    }
} finally {
    Stop-Job $BackendJob, $FrontendJob
    Remove-Job $BackendJob, $FrontendJob
    Write-Host "서버 종료됨." -ForegroundColor Gray
}
