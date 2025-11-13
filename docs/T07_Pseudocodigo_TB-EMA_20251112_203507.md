# T07 — Pseudocódigo Detalhado (TB‑EMA) e Contratos IR2A

## Objetivo
Especificar o pseudocódigo do algoritmo TB‑EMA e os contratos dos métodos exigidos pela interface do player.

## Contratos da Interface (IR2A)
- `initialize()` — prepara estados internos (sem I/O de rede).
- `handle_xml_request(msg)` — encaminha a requisição do MPD **para baixo** (`send_down`).
- `handle_xml_response(msg)` — parseia o MPD, preenche `QI[]`, encaminha **para cima** (`send_up`).
- `handle_segment_size_request(msg)` — **decide o QI** do próximo segmento, define na `msg` e envia **para baixo** (`send_down`).
- `handle_segment_size_response(msg)` — mede desempenho do download, atualiza estimativas e envia **para cima** (`send_up`).
- `finalization()` — imprime/guarda KPIs resumidos.

## Estados Internos e Parâmetros
```
QI[]               # lista de bitrates (Mbps), crescente
i_cur              # índice do QI atual (int, inicia 0)
ema                # estimativa de throughput (Mbps) via EMA
alpha   = 0.20     # fator de suavização da EMA
safety  = 0.85     # margem de segurança
up_hys  = 0.15     # histerese para subida (+15%)
down_hys= 0.10     # histerese para descida (+10%)
cooldown_segments = 3  # mínimo de segmentos entre trocas
seg_idx = 0        # contador de segmentos decididos
last_switch_seg = -inf
```

## Pseudocódigo

### initialize()
```
i_cur ← 0
ema ← None
seg_idx ← 0
last_switch_seg ← -inf
```

### handle_xml_request(msg)
```
send_down(msg)     # encaminha MPD para a rede
```

### handle_xml_response(msg)
```
mpd ← parse_mpd(msg.payload)
QI[] ← extrair_bitrates_ordenados(mpd)        # Mbps, crescente
assert tamanho(QI[]) ≥ 1
send_up(msg)
```

### handle_segment_size_request(msg)   # decisão do próximo QI
```
se ema = None:
    budget ← QI[0] * 0.9                  # conservador antes da 1ª medição
senão:
    budget ← ema * safety

i_budget ← maior i tal que QI[i] ≤ budget  (se nenhum, i_budget = 0)
i_target ← i_budget

se (seg_idx - last_switch_seg) < cooldown_segments:
    i_target ← i_cur

se QI[i_target] > QI[i_cur]:                      # tentativa de subir
    se QI[i_target] ≥ (1 + up_hys) * QI[i_cur]:
        i_target ← min(i_cur + 1, i_target)
    senão:
        i_target ← i_cur
senão se QI[i_target] < QI[i_cur]:                # tentativa de descer
    se QI[i_cur] > (1 + down_hys) * budget:
        i_target ← max(i_cur - 1, i_target)
    senão:
        i_target ← i_cur

se i_target ≠ i_cur:
    last_switch_seg ← seg_idx
    i_cur ← i_target

msg.set_quality(QI[i_cur])
seg_idx ← seg_idx + 1
send_down(msg)
```

### handle_segment_size_response(msg)   # atualização pós-download
```
bytes ← tamanho_baixado(msg)            # bytes
dt    ← tempo_download(msg)             # segundos
tp    ← (8 * bytes / dt) / 1e6          # Mbps

se ema = None:
    ema ← tp
senão:
    ema ← alpha * tp + (1 - alpha) * ema

registrar_segmento(seg_idx-1, QI[i_cur], tp, ema)
send_up(msg)
```

### finalization()
```
imprimir_kpis_resumo()   # rebuffer total, #trocas, avg_QI, avg_QI_distance etc.
salvar_csvs_resumo()
```

## Logs Mínimos
Por segmento `k`:
```
k, t_wall, qi_idx, qi_mbps, tp_mbps, ema_mbps, decision="stay|up|down"
```
Resumo final:
```
num_switches, avg_qi, avg_qi_distance, pauses_count, pauses_time_total, startup_delay, avg_buffer
```
