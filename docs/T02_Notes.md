# T02 — Notas de Leitura do Repositório (pyDash)

> Objetivo: entender a arquitetura mínima para implementar um novo ABR em `r2a/` e executá-lo via `dash_client.json`.

---

## 1) Diretórios e responsabilidades

- **`r2a/`**
  - Contém a **interface IR2A** (classe base do ABR).
  - Exemplos de políticas: **`R2AFixed`** e **`R2ARandom`**.
  - **Sua implementação** ficará aqui (nova classe que herda `IR2A`).
  - Regra: **não** alterar `Player`/`ConnectionHandler`.

- **`client/`**
  - Cliente DASH: orquestra o fluxo **MPD → segmentos**.
  - Instancia a classe do ABR definida em `r2a_algorithm` (arquivo `dash_client.json`).
  - Encaminha mensagens para baixo (rede) e para cima (player/algoritmo).

- **`whiteboard/`** (ou equivalente)
  - API para **métricas em tempo de execução**: buffer, pausas, histórico de QI, etc.
  - Útil para o ABR ler o estado do player ao decidir a qualidade.

- **`results/`**
  - Saídas da execução: **CSVs, gráficos e resumos**.

- **Parser de MPD / utilitários**
  - Funções para **parsear o MPD** e obter **representações (QIs)** e o `SegmentTemplate`.

---

## 2) Ciclo de execução (onde cada método entra)

1. **`initialize()`**
   - Inicializa estado interno do ABR (janelas, contadores, parâmetros).

2. **MPD — requisição**: `handle_xml_request(msg)`
   - O player solicita o MPD; o ABR apenas encaminha **para baixo** (rede).

3. **MPD — resposta**: `handle_xml_response(msg)`
   - Recebe o MPD; **parseia** o XML; extrai **lista de QIs** (bitrate/ID).
   - Armazena em `self.qi` (ordenada por bitrate).
   - Encaminha **para cima** (player).

4. **Segmento — requisição**: `handle_segment_size_request(msg)`
   - **Decisão de qualidade (QI)** por segmento com base no estado (throughput, buffer, etc.).
   - Define a representação escolhida na mensagem; envia **para baixo** (rede).

5. **Segmento — resposta**: `handle_segment_size_response(msg)`
   - Recebe o segmento; calcula **métricas de rede** (tempo, bytes); atualiza médias (ex.: EMA).
   - Registra decisão/estado; envia **para cima** (player).

6. **`finalization()`**
   - Consolida estatísticas, imprime/salva **resumo** (KPIs) e encerra.

---

## 3) Medição de throughput/latência

- **Timestamps**: marque o tempo ao enviar a requisição do segmento e ao receber a resposta.
- **Tamanho do segmento**: utilize o **tamanho efetivo do corpo** recebido (bytes).
- **Throughput (bps)**: `throughput = 8 * bytes_recebidos / Δt`.
- **Latência** (opcional): se disponível, considere **TTFB** (tempo até 1º byte).
- Armazene a série temporal (por segmento) para uso no ABR (ex.: EMA) e em gráficos.

---

## 4) MPD e lista de qualidades (QIs)

- Parseie o **MPD** da resposta XML para obter:
  - **Representations** com **`bandwidth`** (bitrate alvo) e **IDs**.
  - **`SegmentTemplate`** (padrão de nomes/URLs dos segmentos).
- Construa `self.qi` como **lista ordenada por bitrate crescente**.
- A decisão do ABR deve sempre selecionar um QI **existente** em `self.qi`.

---

## 5) Leitura de métricas (whiteboard)

- **Buffer**: `get_playback_buffer_size()` → tamanho do buffer (s) ao longo do tempo.
- **Pausas**: `get_playback_pauses()` → ocorrência/duração de rebuffering.
- **Histórico**: `get_playback_history()` → reprodução/ocioso por instante.
- **Qualidades**: `get_playback_qi()` → QI efetivamente reproduzido por tempo.
- Use essas leituras no ABR para políticas **baseadas em buffer** e para validar resultados.

---

## 6) Configuração via `dash_client.json`

Campos típicos (nomes podem variar conforme a versão):
- **`r2a_algorithm`**: nome **exato** da classe do seu algoritmo (e arquivo homônimo em `r2a/`).
- **`url_mpd`**: URL do MPD de teste.
- **`buffering_until`**, **`max_buffer_size`**: parâmetros de buffer do player.
- **Traffic shaping** (se disponível):
  - `traffic_shaping_profile_interval`
  - `traffic_shaping_profile_sequence` (ex.: L/M/H)
  - `traffic_shaping_seed` (reprodutibilidade)

> **Regra de carregamento**: classe e arquivo em `r2a/` devem seguir nomes coerentes com `r2a_algorithm`.

---

## 7) Escopo e restrições

- **Não alterar** `Player`/`ConnectionHandler`.
- Todo o trabalho do **ABR** deve ficar em **`r2a/`**, herdando `IR2A`.
- Objetivo: **maximizar qualidade** e **minimizar rebuffering**, adaptando a condições de rede.

---

## 8) Checklist do T02

- [X] Arquivos/diretórios e **papéis** (1–2 linhas cada).
- [X] **Momento** de chamada de cada `handle_*` e direção (`send_down`/`send_up`).
- [X] **Como parsear** MPD e montar `self.qi`.
- [X] **Onde** medir throughput/latência (requisição ↔ resposta do segmento).
- [X] **Quais métricas** o whiteboard oferece e como usá-las.
- [X] **Quais chaves** do `dash_client.json` serão ajustadas no T03.

---


