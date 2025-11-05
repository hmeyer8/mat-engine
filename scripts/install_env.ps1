Write-Host "== MAT Engine • Environment Installer =="

function Install-IfMissing {
    param(
        [string]$name,
        [string]$wingetId
    )

    try {
        Write-Host "Checking $name..."
        if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
            Write-Host "Installing $name..." -ForegroundColor Yellow
            winget install --id $wingetId -e --accept-package-agreements --accept-source-agreements
        }
        else {
            Write-Host "$name already installed." -ForegroundColor Green
        }
    }
    catch {
        Write-Host "Error installing ${name}: $_" -ForegroundColor Red
    }
}

# --- Install key dependencies ---
Install-IfMissing "node" "OpenJS.NodeJS.LTS"
Install-IfMissing "npm" "OpenJS.NodeJS.LTS"
Install-IfMissing "rustc" "Rustlang.Rust.MSVC"

Write-Host "`nEnvironment installation complete. ✅" -ForegroundColor Green
Write-Host "You may need to restart PowerShell or VS Code for PATH changes to take effect."
