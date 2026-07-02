# Prueba local tipo producción (Windows PowerShell)
# Ejecutar desde la raíz del repo:  .\scripts\local_prod_test.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Front = Join-Path $Root "front"

$env:PYTHONPATH = $Root
$env:API_ENABLE_SCHEDULER = "false"
$env:APP_ENV = "production"

Write-Host "=== 1/3 Benchmark poll (in-process) ===" -ForegroundColor Cyan
& $Py (Join-Path $Root "testing\benchmark_poll_optimizations.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n=== 2/3 Build frontend producción ===" -ForegroundColor Cyan
Write-Host "  (Si falla EPERM: detené 'npm run dev' antes de correr este script)" -ForegroundColor Yellow
Push-Location $Front
npm run build
$buildOk = $LASTEXITCODE -eq 0
Pop-Location
if (-not $buildOk) {
    Write-Host "  Build falló — probablemente .next bloqueado por dev server." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== 3/3 API live (opcional, puerto 8012) ===" -ForegroundColor Cyan
$apiProc = Start-Process -FilePath $Py `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8012" `
    -WorkingDirectory (Join-Path $Root "back") `
    -PassThru -WindowStyle Hidden `
    -Environment @{
        PYTHONPATH = $Root
        API_ENABLE_SCHEDULER = "false"
        APP_ENV = "production"
    }

Start-Sleep -Seconds 10
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8012/api/health" -TimeoutSec 5
    Write-Host "  Health: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
    & $Py (Join-Path $Root "testing\benchmark_poll_optimizations.py") --live "http://127.0.0.1:8012" --pid $apiProc.Id
} catch {
    Write-Host "  API no respondió en 8012: $_" -ForegroundColor Red
} finally {
    if (-not $apiProc.HasExited) {
        Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n=== Listo ===" -ForegroundColor Green
