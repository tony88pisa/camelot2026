# ==============================================================================
# AI Trader - Environment Audit Script (PowerShell)
# Created: 2026-04-02 20:44
# Purpose: Verifica tutte le dipendenze e requisiti dell'ambiente locale
# Target: Windows 11 + Python 3.11 + Ollama + MCP
# ==============================================================================

param(
    [switch]$GenerateReport,
    [string]$ReportDir = (Join-Path $PSScriptRoot "..\docs")
)

$ErrorActionPreference = "Continue"
$script:Results = @()
$script:Problems = @()
$script:Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# --- Helper Functions ---
# Updated: 2026-04-02 20:44
function Add-CheckResult {
    param(
        [string]$Component,
        [string]$Status,   # OK, WARNING, FAIL, SKIP
        [string]$Detail,
        [string]$Version
    )
    $script:Results += [PSCustomObject]@{
        Component = $Component
        Status    = $Status
        Detail    = $Detail
        Version   = $Version
    }
    $icon = switch ($Status) {
        "OK"      { "[OK]" }
        "WARNING" { "[!!]" }
        "FAIL"    { "[XX]" }
        "SKIP"    { "[--]" }
    }
    $color = switch ($Status) {
        "OK"      { "Green" }
        "WARNING" { "Yellow" }
        "FAIL"    { "Red" }
        "SKIP"    { "DarkGray" }
    }
    Write-Host "  $icon " -ForegroundColor $color -NoNewline
    Write-Host "$Component" -ForegroundColor White -NoNewline
    if ($Version) { Write-Host " ($Version)" -ForegroundColor Cyan -NoNewline }
    Write-Host " - $Detail" -ForegroundColor Gray
}

function Add-Problem {
    param([string]$Description, [string]$Suggestion)
    $script:Problems += [PSCustomObject]@{
        Problem    = $Description
        Suggestion = $Suggestion
    }
}

function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# --- Banner ---
Write-Host ""
Write-Host "=" * 60 -ForegroundColor DarkCyan
Write-Host "  AI TRADER - Environment Audit" -ForegroundColor Cyan
Write-Host "  Timestamp: $script:Timestamp" -ForegroundColor Gray
Write-Host "=" * 60 -ForegroundColor DarkCyan
Write-Host ""

# =============================================================================
# 1. WINDOWS VERSION — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host "[SECTION] Windows" -ForegroundColor Magenta
try {
    $osInfo = [System.Environment]::OSVersion
    $winVer = (Get-CimInstance Win32_OperatingSystem).Caption
    $buildNumber = [System.Environment]::OSVersion.Version.Build
    Add-CheckResult -Component "Windows Version" -Status "OK" -Detail $winVer -Version "Build $buildNumber"
    if ($buildNumber -lt 22000) {
        Add-CheckResult -Component "Windows 11 Check" -Status "WARNING" -Detail "Build < 22000, potrebbe non essere Windows 11" -Version ""
        Add-Problem -Description "Windows build $buildNumber potrebbe non essere Windows 11" -Suggestion "Verifica di avere Windows 11 (build >= 22000)"
    } else {
        Add-CheckResult -Component "Windows 11 Check" -Status "OK" -Detail "Build compatibile con Windows 11" -Version ""
    }
} catch {
    Add-CheckResult -Component "Windows Version" -Status "FAIL" -Detail "Impossibile rilevare: $_" -Version ""
}

# =============================================================================
# 2. PYTHON — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] Python" -ForegroundColor Magenta
if (Test-CommandExists "python") {
    try {
        $pyVer = & python --version 2>&1
        $pyVerString = ($pyVer -replace "Python ", "").Trim()
        Add-CheckResult -Component "Python" -Status "OK" -Detail "Disponibile" -Version $pyVerString

        # Check if Python 3.11
        if ($pyVerString -match "^3\.11") {
            Add-CheckResult -Component "Python 3.11 Target" -Status "OK" -Detail "Versione target corretta" -Version ""
        } else {
            Add-CheckResult -Component "Python 3.11 Target" -Status "WARNING" -Detail "Versione trovata: $pyVerString (target: 3.11.x)" -Version ""
            Add-Problem -Description "Python $pyVerString trovato, ma il target e' 3.11.x" -Suggestion "Installa Python 3.11 da python.org o usa pyenv-win"
        }

        # Check python path
        $pyPath = (Get-Command python).Source
        Add-CheckResult -Component "Python Path" -Status "OK" -Detail $pyPath -Version ""
    } catch {
        Add-CheckResult -Component "Python" -Status "FAIL" -Detail "Errore esecuzione: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "Python" -Status "FAIL" -Detail "Non trovato nel PATH" -Version ""
    Add-Problem -Description "Python non trovato" -Suggestion "Installa Python 3.11 da https://python.org"
}

# =============================================================================
# 3. PIP — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] pip" -ForegroundColor Magenta
if (Test-CommandExists "pip") {
    try {
        $pipVer = & pip --version 2>&1
        $pipVerMatch = [regex]::Match($pipVer, "pip (\S+)")
        $pipVersion = if ($pipVerMatch.Success) { $pipVerMatch.Groups[1].Value } else { "unknown" }
        Add-CheckResult -Component "pip" -Status "OK" -Detail "Disponibile" -Version $pipVersion
    } catch {
        Add-CheckResult -Component "pip" -Status "FAIL" -Detail "Errore esecuzione: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "pip" -Status "FAIL" -Detail "Non trovato nel PATH" -Version ""
    Add-Problem -Description "pip non trovato" -Suggestion "Esegui: python -m ensurepip --upgrade"
}

# =============================================================================
# 4. VENV — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] venv" -ForegroundColor Magenta
if (Test-CommandExists "python") {
    try {
        $venvTest = & python -c "import venv; print('ok')" 2>&1
        if ($venvTest -match "ok") {
            Add-CheckResult -Component "venv" -Status "OK" -Detail "Modulo venv disponibile" -Version ""
        } else {
            Add-CheckResult -Component "venv" -Status "FAIL" -Detail "Modulo venv non funzionante" -Version ""
            Add-Problem -Description "venv non disponibile" -Suggestion "Reinstalla Python con l'opzione standard library completa"
        }
    } catch {
        Add-CheckResult -Component "venv" -Status "FAIL" -Detail "Errore test venv: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "venv" -Status "SKIP" -Detail "Python non disponibile, skip venv" -Version ""
}

# =============================================================================
# 5. NODE.JS — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] Node.js" -ForegroundColor Magenta
if (Test-CommandExists "node") {
    try {
        $nodeVer = (& node --version 2>&1).Trim()
        Add-CheckResult -Component "Node.js" -Status "OK" -Detail "Disponibile" -Version $nodeVer
    } catch {
        Add-CheckResult -Component "Node.js" -Status "FAIL" -Detail "Errore esecuzione: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "Node.js" -Status "WARNING" -Detail "Non trovato nel PATH" -Version ""
    Add-Problem -Description "Node.js non trovato" -Suggestion "Installa da https://nodejs.org (LTS consigliato)"
}

# =============================================================================
# 6. NPM — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] npm" -ForegroundColor Magenta
if (Test-CommandExists "npm") {
    try {
        $npmVer = (& npm --version 2>&1).Trim()
        Add-CheckResult -Component "npm" -Status "OK" -Detail "Disponibile" -Version $npmVer
    } catch {
        Add-CheckResult -Component "npm" -Status "FAIL" -Detail "Errore esecuzione: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "npm" -Status "WARNING" -Detail "Non trovato nel PATH" -Version ""
    Add-Problem -Description "npm non trovato" -Suggestion "Si installa automaticamente con Node.js"
}

# =============================================================================
# 7. GIT — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] Git" -ForegroundColor Magenta
if (Test-CommandExists "git") {
    try {
        $gitVer = (& git --version 2>&1).Trim()
        $gitVerClean = ($gitVer -replace "git version ", "")
        Add-CheckResult -Component "Git" -Status "OK" -Detail "Disponibile" -Version $gitVerClean
    } catch {
        Add-CheckResult -Component "Git" -Status "FAIL" -Detail "Errore esecuzione: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "Git" -Status "FAIL" -Detail "Non trovato nel PATH" -Version ""
    Add-Problem -Description "Git non trovato" -Suggestion "Installa da https://git-scm.com"
}

# =============================================================================
# 8. OLLAMA — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] Ollama" -ForegroundColor Magenta

# 8a. Binary check
if (Test-CommandExists "ollama") {
    try {
        $ollamaVer = (& ollama --version 2>&1).Trim()
        Add-CheckResult -Component "Ollama Binary" -Status "OK" -Detail "Disponibile" -Version $ollamaVer
    } catch {
        Add-CheckResult -Component "Ollama Binary" -Status "WARNING" -Detail "Trovato ma errore versione: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "Ollama Binary" -Status "FAIL" -Detail "Non trovato nel PATH" -Version ""
    Add-Problem -Description "Ollama non installato" -Suggestion "Installa da https://ollama.com/download"
}

# 8b. API health check
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5 -ErrorAction Stop
    $modelCount = if ($ollamaResponse.models) { $ollamaResponse.models.Count } else { 0 }
    Add-CheckResult -Component "Ollama API" -Status "OK" -Detail "Server risponde, modelli trovati: $modelCount" -Version ""
} catch {
    Add-CheckResult -Component "Ollama API" -Status "WARNING" -Detail "Server non raggiungibile (potrebbe non essere avviato)" -Version ""
    Add-Problem -Description "Ollama API non risponde su localhost:11434" -Suggestion "Avvia Ollama con: ollama serve"
}

# =============================================================================
# 9. PYTORCH — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] PyTorch / CUDA" -ForegroundColor Magenta
if (Test-CommandExists "python") {
    try {
        $torchCheck = & python -c "
import sys
try:
    import torch
    parts = []
    parts.append('version=' + torch.__version__)
    parts.append('cuda_available=' + str(torch.cuda.is_available()))
    if torch.cuda.is_available():
        parts.append('cuda_version=' + str(torch.version.cuda))
        parts.append('gpu_name=' + torch.cuda.get_device_name(0))
    print('|'.join(parts))
except ImportError:
    print('NOT_INSTALLED')
except Exception as e:
    print('ERROR=' + str(e))
" 2>&1

        if ($torchCheck -match "NOT_INSTALLED") {
            Add-CheckResult -Component "PyTorch" -Status "WARNING" -Detail "Non installato (non richiesto in questa fase)" -Version ""
        } elseif ($torchCheck -match "ERROR=") {
            $errMsg = ($torchCheck -replace "ERROR=", "")
            Add-CheckResult -Component "PyTorch" -Status "WARNING" -Detail "Errore rilevamento: $errMsg" -Version ""
        } else {
            $parts = @{}
            $torchCheck.Split("|") | ForEach-Object {
                $kv = $_.Split("=", 2)
                if ($kv.Count -eq 2) { $parts[$kv[0]] = $kv[1] }
            }
            $torchVer = $parts["version"]
            Add-CheckResult -Component "PyTorch" -Status "OK" -Detail "Installato" -Version $torchVer

            if ($parts["cuda_available"] -eq "True") {
                Add-CheckResult -Component "CUDA (via PyTorch)" -Status "OK" -Detail "GPU: $($parts['gpu_name'])" -Version "CUDA $($parts['cuda_version'])"
            } else {
                Add-CheckResult -Component "CUDA (via PyTorch)" -Status "WARNING" -Detail "PyTorch presente ma CUDA non disponibile (CPU-only)" -Version ""
            }
        }
    } catch {
        Add-CheckResult -Component "PyTorch" -Status "WARNING" -Detail "Errore verifica: $_" -Version ""
    }
} else {
    Add-CheckResult -Component "PyTorch" -Status "SKIP" -Detail "Python non disponibile" -Version ""
}

# =============================================================================
# 10. PATH ANALYSIS — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "[SECTION] PATH Analysis" -ForegroundColor Magenta
$pathEntries = $env:PATH -split ";"
$relevantPaths = $pathEntries | Where-Object {
    $_ -match "(?i)(python|node|npm|git|ollama|cuda|torch)"
}
if ($relevantPaths.Count -gt 0) {
    foreach ($p in $relevantPaths) {
        Add-CheckResult -Component "PATH" -Status "OK" -Detail $p -Version ""
    }
} else {
    Add-CheckResult -Component "PATH" -Status "WARNING" -Detail "Nessun path rilevante trovato per tool del progetto" -Version ""
}

# =============================================================================
# SUMMARY — Updated: 2026-04-02 20:44
# =============================================================================
Write-Host ""
Write-Host "=" * 60 -ForegroundColor DarkCyan
Write-Host "  RIEPILOGO" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor DarkCyan

$okCount = ($script:Results | Where-Object { $_.Status -eq "OK" }).Count
$warnCount = ($script:Results | Where-Object { $_.Status -eq "WARNING" }).Count
$failCount = ($script:Results | Where-Object { $_.Status -eq "FAIL" }).Count
$skipCount = ($script:Results | Where-Object { $_.Status -eq "SKIP" }).Count

Write-Host "  OK:      $okCount" -ForegroundColor Green
Write-Host "  WARNING: $warnCount" -ForegroundColor Yellow
Write-Host "  FAIL:    $failCount" -ForegroundColor Red
Write-Host "  SKIP:    $skipCount" -ForegroundColor DarkGray

if ($script:Problems.Count -gt 0) {
    Write-Host ""
    Write-Host "  PROBLEMI TROVATI:" -ForegroundColor Red
    foreach ($prob in $script:Problems) {
        Write-Host "    - $($prob.Problem)" -ForegroundColor Yellow
        Write-Host "      Fix: $($prob.Suggestion)" -ForegroundColor Gray
    }
}

# =============================================================================
# REPORT GENERATION — Updated: 2026-04-02 20:44
# =============================================================================
# Always generate reports
if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

# --- Markdown Report ---
$mdPath = Join-Path $ReportDir "ENVIRONMENT_STATUS.md"
$md = @"
# AI Trader — Environment Status Report

> Generated: $script:Timestamp
> Machine: $env:COMPUTERNAME
> User: $env:USERNAME

## Check Results

| Component | Status | Version | Detail |
|-----------|--------|---------|--------|
"@
foreach ($r in $script:Results) {
    $statusIcon = switch ($r.Status) {
        "OK"      { "✅" }
        "WARNING" { "⚠️" }
        "FAIL"    { "❌" }
        "SKIP"    { "⏭️" }
    }
    $md += "`n| $($r.Component) | $statusIcon $($r.Status) | $($r.Version) | $($r.Detail) |"
}

$md += "`n`n## Summary`n"
$md += "- **OK**: $okCount`n"
$md += "- **Warning**: $warnCount`n"
$md += "- **Fail**: $failCount`n"
$md += "- **Skip**: $skipCount`n"

if ($script:Problems.Count -gt 0) {
    $md += "`n## Problems & Recommendations`n"
    foreach ($prob in $script:Problems) {
        $md += "`n### ⚠️ $($prob.Problem)`n"
        $md += "**Suggestion**: $($prob.Suggestion)`n"
    }
}

$md | Out-File -FilePath $mdPath -Encoding utf8 -Force
Write-Host ""
Write-Host "  Report MD salvato: $mdPath" -ForegroundColor Green

# --- JSON Report ---
$jsonPath = Join-Path $ReportDir "environment_status.json"
$jsonData = @{
    timestamp    = $script:Timestamp
    machine      = $env:COMPUTERNAME
    user         = $env:USERNAME
    results      = $script:Results | ForEach-Object {
        @{
            component = $_.Component
            status    = $_.Status
            version   = $_.Version
            detail    = $_.Detail
        }
    }
    problems     = $script:Problems | ForEach-Object {
        @{
            problem    = $_.Problem
            suggestion = $_.Suggestion
        }
    }
    summary      = @{
        ok      = $okCount
        warning = $warnCount
        fail    = $failCount
        skip    = $skipCount
    }
} | ConvertTo-Json -Depth 4

$jsonData | Out-File -FilePath $jsonPath -Encoding utf8 -Force
Write-Host "  Report JSON salvato: $jsonPath" -ForegroundColor Green

Write-Host ""
Write-Host "=" * 60 -ForegroundColor DarkCyan
Write-Host "  Audit completato." -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor DarkCyan
Write-Host ""
