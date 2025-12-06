<# 
    Script: Generate-BBA-Resumes.ps1
    Objetivo:
      - Para cada pasta em .\results que tenha run_bba.log
      - Ler KPIs do log
      - Listar PNGs
      - Gerar resume.md
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-KpiFromText {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Label
    )

    # Monta regex multiline: "Label : numero" (aceita . ou ,)
    $rx = "(?m)^\s*" + [regex]::Escape($Label) + "\s*:\s*([-+]?[0-9]+(?:[.,][0-9]+)?)\s*$"
    $m  = [regex]::Match($Text, $rx)

    if ($m.Success) {
        # normaliza virgula para ponto
        return ($m.Groups[1].Value -replace ',', '.')
    }

    return $null
}

Write-Host "=== Geracao de resume.md (BBA) ===" -ForegroundColor Cyan

$root       = Get-Location
$resultsDir = Join-Path $root "results"

if (-not (Test-Path $resultsDir)) {
    Write-Error "Pasta 'results' nao encontrada em: $resultsDir"
    exit 1
}

# Pastas que contem run_bba.log
$scenarioDirs = Get-ChildItem -Path $resultsDir -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "run_bba.log") } |
    Sort-Object Name

if (-not $scenarioDirs) {
    Write-Host "Nenhuma pasta com run_bba.log encontrada em '$resultsDir'."
    exit 0
}

$summary = @()

foreach ($dir in $scenarioDirs) {
    $scenarioName = $dir.Name
    $scenarioPath = $dir.FullName

    Write-Host ""
    Write-Host ("--- Processando pasta: {0} ---" -f $scenarioName) -ForegroundColor Yellow

    $logPath  = Join-Path $scenarioPath "run_bba.log"
    $dashPath = Join-Path $scenarioPath "dash.json"

    # Le texto do log
    $logText = Get-Content -Path $logPath -Raw

    # KPIs (inicialmente N/A)
    $kpiPausesNumber  = "N/A"
    $kpiAvgPauseTime  = "N/A"
    $kpiAvgQi         = "N/A"
    $kpiAvgQiDistance = "N/A"

    $tmp = Get-KpiFromText -Text $logText -Label "Pauses number"
    if ($tmp) { $kpiPausesNumber = $tmp }

    $tmp = Get-KpiFromText -Text $logText -Label "Average Time Pauses"
    if ($tmp) { $kpiAvgPauseTime = $tmp }

    $tmp = Get-KpiFromText -Text $logText -Label "Average QI"
    if ($tmp) { $kpiAvgQi = $tmp }

    $tmp = Get-KpiFromText -Text $logText -Label "Average QI distance"
    if ($tmp) { $kpiAvgQiDistance = $tmp }

    # PNGs
    $pngList = @(Get-ChildItem -Path $scenarioPath -Filter "*.png" -File | Sort-Object Name)

    if ($pngList.Count -gt 0) {
        $pngLines = $pngList | ForEach-Object { "- $($_.Name)" }
    } else {
        $pngLines = @("- N/A")
    }

    $kpiValues  = @($kpiPausesNumber, $kpiAvgPauseTime, $kpiAvgQi, $kpiAvgQiDistance)
    $hasMissing = $kpiValues -contains "N/A"

    $observacoes = @()
    $observacoes += "- Algoritmo utilizado: R2ABBA (BBA baseado em buffer)."

    if ($hasMissing) {
        $observacoes += "- Alguns KPIs nao foram encontrados no log e estao marcados como 'N/A'."
    } else {
        $observacoes += "- Todos os KPIs foram extraidos do run_bba.log."
    }

    if ($pngList.Count -eq 0) {
        $observacoes += "- Nenhum arquivo PNG encontrado nesta pasta."
    }

    if (Test-Path $dashPath) {
        $cfgName = "dash.json"
    } else {
        $cfgName = "N/A"
    }

    $resumePath = Join-Path $scenarioPath "resume.md"

    $md = @()
    $md += "# $scenarioName"
    $md += ""
    $md += ('**Arquivo de configuracao:** `{0}`' -f $cfgName)
    $md += '**Log principal:** `run_bba.log`'
    $md += ""
    $md += "## KPIs"
    $md += ""
    $md += "| KPI                       | Valor |"
    $md += "|---------------------------|-------|"
    $md += ("| Pauses number             | {0} |" -f $kpiPausesNumber)
    $md += ("| Average Time Pauses (s)   | {0} |" -f $kpiAvgPauseTime)
    $md += ("| Average QI                | {0} |" -f $kpiAvgQi)
    $md += ("| Average QI distance       | {0} |" -f $kpiAvgQiDistance)
    $md += ""
    $md += "## Graficos (PNGs)"
    $md += ""
    $md += $pngLines
    $md += ""
    $md += "## Observacoes"
    $md += ""
    $md += $observacoes

    $md -join "`r`n" | Set-Content -Path $resumePath -Encoding UTF8

    Write-Host ("resume.md gerado: {0}" -f $resumePath) -ForegroundColor Green

    $summary += [PSCustomObject]@{
        Pasta  = $scenarioName
        Resume = $resumePath
        Pngs   = $pngList.Count
    }
}

Write-Host ""
Write-Host "=== Resumo da geracao ===" -ForegroundColor Cyan
foreach ($s in $summary) {
    Write-Host ("- {0}: PNGs={1}; resume.md={2}" -f $s.Pasta, $s.Pngs, $s.Resume)
}
