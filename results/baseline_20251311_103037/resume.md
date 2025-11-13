# Baseline — R2ATBEMA (BigBuckBunny, 1s)

**Data/hora:** 20251311_103037  
**MPD:** `BigBuckBunny_1s_simple_2014_05_09.mpd`  
**Algoritmo:** `R2ATBEMA` (esqueleto — QI mínimo)

## Configuração

- `buffering_until`: **5 s**
- `max_buffer_size`: **60 s**
- `playbak_step`: **1 s**
- Perfil de rede: **L,M,H @ 5s (seed=1)**
- Arquivo de configuração: `dash_client.json`

## Comando executado

```powershell
$env:PYTHONPATH = (Get-Location).Path
python .\main.py *> .\results\baseline_20251311_103037\run_20251311_103037.log
```

Log: [`run_20251311_103037.log`](sandbox:/mnt/data/run_20251311_103037.log)

## KPIs (sanity)

- **Playback:** contínuo, sem pausas visíveis.
- **Buffer:** ~60 s estável até o fim.
- **Qualidade:** QI mínimo constante (sem trocas).
- **Throughput:** varia com o perfil L,M,H (ainda não usado pela política).

## Gráficos

- **Throughput Variation**  
  ![throughput](sandbox:/mnt/data/throughput.png)
- **Playback History**  
  ![playback](sandbox:/mnt/data/playback.png)
- **Buffer Size**  
  ![buffer](sandbox:/mnt/data/playback_buffer_size.png)
- **Quality Index (QI id)**  
  ![qi](sandbox:/mnt/data/playback_qi.png)
- **Quality QI (bitrate)**  
  ![quality_qi](sandbox:/mnt/data/playback_quality_qi.png)

## Observações rápidas

- Baseline para validar **integração e execução** do `R2ATBEMA` sem alterar a base.
- Servirá de referência para os cenários do **T09** e para a versão adaptativa no **T10+**.
