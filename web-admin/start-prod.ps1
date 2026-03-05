# TikTok 어드민 — 프로덕션 모드
# React 빌드 → FastAPI 단일 프로세스

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $PSScriptRoot "backend"
$FrontendDir = Join-Path $PSScriptRoot "frontend"

Write-Host "=== TikTok 콘텐츠 어드민 (프로덕션 모드) ===" -ForegroundColor Cyan
Write-Host ""

# 1. React 빌드
Write-Host "[1/3] React 빌드 중..." -ForegroundColor Yellow
Push-Location $FrontendDir

if (-not (Test-Path "node_modules")) {
    Write-Host "  npm install 실행 중..."
    npm install
}

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "오류: React 빌드 실패" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

Write-Host "  ✓ 빌드 완료 → backend/static/" -ForegroundColor Green

# 2. 백엔드 의존성 설치
Write-Host "[2/3] 백엔드 의존성 설치 중..." -ForegroundColor Yellow
Push-Location $BackendDir
pip install -r requirements.txt -q
Pop-Location
Write-Host "  ✓ 완료" -ForegroundColor Green

# 3. FastAPI 실행
Write-Host "[3/3] FastAPI 서버 시작..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  어드민 URL: http://localhost:8000" -ForegroundColor White
Write-Host "  API 문서: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  종료: Ctrl+C" -ForegroundColor Gray
Write-Host ""

Push-Location $BackendDir
$env:PYTHONPATH = $ProjectRoot
python -X utf8 -m uvicorn main:app --host 0.0.0.0 --port 8000
Pop-Location
