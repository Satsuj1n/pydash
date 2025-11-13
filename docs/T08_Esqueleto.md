# T08 — Esqueleto do ABR (R2ATBEMA)

## Objetivo

Validar a integração do algoritmo **R2ATBEMA** ao player (pipeline completo) com decisão mínima de qualidade.

## Integração

- **Classe/arquivo:** `R2ATBEMA` em `r2a/r2atbema.py`.
- **Config:** `dash_client.json` com `r2a_algorithm: "R2ATBEMA"` e MPD do BigBuckBunny.

## Execução (baseline) e arquivamento

```powershell
& .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$baseline = ".
esultsaseline_$ts"
New-Item -ItemType Directory $baseline -Force | Out-Null
python .\main.py *> "$baseline
un_$ts.log"
robocopy .
esults $baseline /E /XD $baseline > $null
Copy-Item .\dash_client.json $baseline
```

## Resultados (sanity check)

- **Playback:** contínuo, sem pausas.
- **Buffer:** ~60 s estável, queda apenas no término.
- **Qualidade:** QI fixo no menor nível (sem trocas).
- **Throughput:** varia (~0,5–4,5 Mbps), ainda não utilizado.

## Reprodutibilidade

- **Perfil/seed:** `traffic_shaping_profile_sequence = "L,M,H"`, `traffic_shaping_seed = 1`, `traffic_shaping_profile_interval = 5`.
- **Buffer:** `buffering_until = 5`, `max_buffer_size = 60`, `playbak_step = 1`.

## Aceite (T08)

- [x] Política carregada e executando sem erro.
- [x] QI válido definido por segmento.
- [x] Gráficos e log gerados e arquivados em `results/baseline_<timestamp>`.

## Próximo

T09 — Planejar cenários de teste (L/M/H, duração e seed).
