# T06 — Plano do Algoritmo ABR TB‑EMA — Conclusões

## Objetivo
Definir um algoritmo ABR simples, reprodutível e estável, priorizando redução de rebuffering e de oscilação de qualidade sem perda significativa de bitrate médio.

## Abordagem Selecionada
**TB‑EMA (Throughput‑Based com EMA)**: a qualidade é escolhida pelo maior bitrate ≤ orçamento calculado por **EMA do throughput** com **margem de segurança**. Inclui **histerese** e **cooldown** para reduzir trocas sucessivas.

## Funcionamento (alto nível)
- Estima o throughput por segmento e atualiza a **EMA**.
- Define um **orçamento efetivo** = `EMA × safety`.
- Seleciona a maior representação cujo bitrate ≤ orçamento.
- Aplica **histerese** e **cooldown** para suavizar subidas/descidas (±1 nível por decisão).

## Parâmetros Iniciais
- `alpha = 0.20` (EMA), `safety = 0.85`
- Histerese: `up_hys = 0.15`, `down_hys = 0.10`
- `cooldown_segments = 3`
- Inicialização conservadora no menor QI até a 1ª medição confiável.

## Decisão de Qualidade (resumo)
- **Subida** apenas se o próximo nível for ≥ `(1 + up_hys)` do nível atual e houver orçamento.
- **Descida** quando o nível atual exceder `(1 + down_hys) × orçamento`.
- Alterações limitadas a ±1 nível por segmento respeitando cooldown.

## KPIs de Avaliação
- **Rebuffer total**: reduzir ≥ **30%** frente ao baseline.
- **Average QI distance**: ≤ **4.5**.
- **Bitrate médio**: ≥ **−10%** do baseline (preferência: igual ou maior).
- **Startup delay**: semelhante ao baseline.

## Cenários de Teste (reprodutíveis)
- Perfil de rede: **L,M,H**, intervalo **5 s**, **seed = 1** (configuração atual).
- Rodadas adicionais (opcionais): **L**, **M**, **H** isolados com a mesma seed e passo.

## Evidências de Referência (Baseline — R2ARandom)
- **Rebufferings (n):** 18
- **Tempo médio de pausa (s):** 3.62 (total ≈ 65.16 s)
- **Average QI distance:** 6.84
- **Average QI:** 9.62

## Observação Final
A escolha do TB‑EMA privilegia simplicidade, transparência e controle fino por parâmetros, reduzindo risco de rebuffering e “ping‑pong” sem dependência de modelos complexos.
