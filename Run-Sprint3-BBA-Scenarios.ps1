<# 
    Script: Run-Sprint3-BBA-Scenarios-text.ps1
    Ideia:
      - Nao parseia JSON em PowerShell
      - So substitui as strings dos campos:
        "r2a_algorithm"
        "traffic_shaping_profile_sequence"
      - Sempre parte do dash_client.base.json (backup)
#>

param(
    [string]$PythonExe = "python",
    [string]$AlgorithmName = "R2ABBA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== Sprint 3 - Execucao automatica (BBA, replace de texto) ===" -ForegroundColor Cyan

$root       = Get-Location
$configPath = Join-Path $root "dash_client.json"
$backupPath = Join-Path $root "dash_client.base.json"

if (-not (Test-Path $configPath)) {
    Write-Error "dash_client.json nao encontrado em: $configPath"
    exit 1
}

# Garante backup do JSON original
if (-not (Test-Path $backupPath)) {
    Write-Host "Criando backup de dash_client.json em: $backupPath"
    Copy-Item $configPath $backupPath -Force
} else {
    Write-Host "Backup ja existe em: $backupPath"
}

# Conteudo base (o mesmo que voce usa manualmente)
$baseText = Get-Content $backupPath -Raw

# Definicao dos cenarios
$scenarios = @(
    @{ Name = "C1_L";   Profile = "L,M,H" },
    @{ Name = "C2_M";   Profile = "M"     },
    @{ Name = "C3_H";   Profile = "H"     },
    @{ Name = "C4_LMH"; Profile = "L,M,H" }
)

$executed = @()

foreach ($s in $scenarios) {
    $name    = $s.Name
    $profile = $s.Profile

    Write-Host ""
    Write-Host "--- Executando cenario $name (perfil $profile) ---" -ForegroundColor Yellow

    # Sempre recomeça do texto base
    $txt = $baseText

    # 1) Algoritmo: "r2a_algorithm": "..."
    $txt = [System.Text.RegularExpressions.Regex]::Replace(
        $txt,
        '"r2a_algorithm"\s*:\s*"(.*?)"',
        '"r2a_algorithm": "' + $AlgorithmName + '"'
    )

    # 2) Perfil: "traffic_shaping_profile_sequence": "..."
    $txt = [System.Text.RegularExpressions.Regex]::Replace(
        $txt,
        '"traffic_shaping_profile_sequence"\s*:\s*"(.*?)"',
        '"traffic_shaping_profile_sequence": "' + $profile + '"'
    )

    # Opcional: se existir "scenario_name", atualiza
    if ($txt -match '"scenario_name"\s*:') {
        $txt = [System.Text.RegularExpressions.Regex]::Replace(
            $txt,
            '"scenario_name"\s*:\s*"(.*?)"',
            '"scenario_name": "' + $name + '"'
        )
    }

    # Escreve o dash_client.json (apenas texto, sem mexer no formato)
    Set-Content -Path $configPath -Value $txt -Encoding UTF8

    # Executa main.py
    & $PythonExe .\main.py
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "Cenario $name finalizado (exit code 0)." -ForegroundColor Green
        $executed += $name
    } else {
        Write-Warning "Cenario $name terminou com exit code $exitCode."
    }
}

# Restaura o dash_client.json original
Write-Host ""
Write-Host "Restaurando dash_client.json a partir do backup..." -ForegroundColor Cyan
Copy-Item $backupPath $configPath -Force

Write-Host ""
Write-Host "=== Resumo da execucao ===" -ForegroundColor Cyan
Write-Host ("Cenarios definidos : {0}" -f $scenarios.Count)
Write-Host ("Cenarios com exit code 0: {0}" -f $executed.Count)
if ($executed.Count -gt 0) {
    Write-Host ("Executados OK: {0}" -f ($executed -join ", "))
}
Write-Host ""
Write-Host "Verifique a pasta '.\results' para as novas pastas com logs e imagens." -ForegroundColor Cyan
