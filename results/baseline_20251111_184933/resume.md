# Baseline — R2ARandom (BigBuckBunny, 1s)

**Data/hora:** 20251111_215849  
**MPD:** `BigBuckBunny_1s_simple_2014_05_09.mpd`  
**Algoritmo:** `R2ARandom`

## Configuração

- `buffering_until`: **5 s**
- `max_buffer_size`: **60 s**
- `playbak_step`: **1 s**
- Perfil de rede: **L,M,H @ 5s (seed=1)**
- Arquivo de configuração: [`dash_client.json`](sandbox:/mnt/data/dash_client.json)

## Comando executado

```powershell
$env:PYTHONPATH = (Get-Location).Path
python .\main.py *> .\run.log
```

Log: [`run_20251111_184933.log`](sandbox:/mnt/data/run_20251111_184933.log)

## KPIs (extraídos do log)

- **Rebufferings (n):** 18
- **Tempo médio de pausa (s):** 3.62
- **Tempo total de pausa (s):** 65.16 <!-- 18 × 3.62 -->
- **Pausas — desvio-padrão / variância:** 2.33 / 5.44

- **Average QI:** 9.62
- **QI — desvio-padrão / variância:** 5.76 / 33.22

- **Average QI distance:** 6.84
- **QI distance — desvio-padrão / variância:** 4.70 / 22.08

## Gráficos

> Todos gerados em `results/` na execução atual.

- **Throughput Variation**  
  ![throughput](sandbox:/mnt/data/throughput.png)
- **Playback History**  
  ![playback](sandbox:/mnt/data/playback.png)
- **Buffer Size**  
  ![buffer](sandbox:/mnt/data/playback_buffer_size.png)
- **Pauses Size**  
  ![pauses](sandbox:/mnt/data/playback_pauses.png)
- **Quality Index (QI id)**  
  ![qi](sandbox:/mnt/data/playback_qi.png)
- **Quality QI (bitrate)**  
  ![quality_qi](sandbox:/mnt/data/playback_quality_qi.png)

## Observações rápidas

- Buffer atingiu picos na metade inicial e caiu próximo de 300–360s, com pausas esparsas subsequentes.
- QI variou amplamente ao longo de toda a sessão, coerente com a política aleatória.
- Throughput alternou entre valores baixos e altos conforme o perfil _L,M,H_.
