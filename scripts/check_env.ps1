Write-Host "== MAT Engine • Windows environment check =="

$missing = @()

# --- Git ---
try { git --version | Out-Null; Write-Host "[OK] Git" -ForegroundColor Green }
catch { Write-Host "[X] Git missing" -ForegroundColor Red; $missing += "Git" }

# --- Docker ---
try { docker --version | Out-Null; Write-Host "[OK] Docker Desktop" -ForegroundColor Green }
catch { Write-Host "[X] Docker missing" -ForegroundColor Red; $missing += "Docker" }

# --- Java ---
try { java -version 2>&1 | Out-Null; Write-Host "[OK] Java (JDK 21+)" -ForegroundColor Green }
catch { Write-Host "[X] Java missing" -ForegroundColor Red; $missing += "Java" }

# --- Python ---
try { python --version | Out-Null; Write-Host "[OK] Python 3.11+" -ForegroundColor Green }
catch { Write-Host "[X] Python missing" -ForegroundColor Red; $missing += "Python" }

# --- Node.js ---
try { node -v | Out-Null; Write-Host "[OK] Node.js 20+" -ForegroundColor Green }
catch { Write-Host "[X] Node.js missing" -ForegroundColor Red; $missing += "Node.js" }

# --- npm ---
try { npm -v | Out-Null; Write-Host "[OK] npm" -ForegroundColor Green }
catch { Write-Host "[X] npm missing" -ForegroundColor Red; $missing += "npm" }

# --- Rust ---
try { rustc --version | Out-Null; Write-Host "[OK] Rust" -ForegroundColor Green }
catch { Write-Host "[X] Rust missing" -ForegroundColor Red; $missing += "Rust" }

# --- Cargo ---
try { cargo --version | Out-Null; Write-Host "[OK] Cargo" -ForegroundColor Green }
catch { Write-Host "[X] Cargo missing" -ForegroundColor Red; $missing += "Cargo" }

# --- CUDA / GPU ---
try { nvidia-smi | Out-Null; Write-Host "[OK] NVIDIA GPU detected" -ForegroundColor Green }
catch { Write-Host "[!] No GPU detected (ok for non-GPU systems)" -ForegroundColor Yellow }

# --- Summary ---
if ($missing.Count -eq 0) {
    Write-Host ""
    Write-Host "All critical tools are installed." -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "Missing tools: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Run .\scripts\install_env.ps1 to install missing components." -ForegroundColor Yellow
}
