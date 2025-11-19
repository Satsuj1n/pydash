# r2a/r2atbema.py
from __future__ import annotations
from collections import deque
from r2a.ir2a import IR2A
from player.parser import parse_mpd  # base já fornece

class R2ATBEMA(IR2A):
    NAME = "R2ATBEMA"

    def __init__(self, id):
        super().__init__(id)

    def initialize(self):
        # ----- Qualidades / posição -----
        self.qi = []              # IDs/bitrates disponíveis (da base)
        self.qi_order = []        # IDs ordenados por bitrate (se possível)
        self.i_cur = None
        self.qi_cur = None

        # ----- MPD / bitrates -----
        self.parsed_mpd = None
        self.bitrate_map = {}     # dict opcional: id -> bitrate(bps)

        # ----- Throughput / filtragem -----
        self.alpha = 0.20
        self.safety = 0.85
        self.ema_bps = None
        self.th_samples = deque(maxlen=8)

        # ----- Estabilidade / histerese -----
        self.up_hys = 0.15
        self.down_hys = 0.10
        self.cooldown_segments = 3
        self.last_switch_seg = -10**9

        # ----- Contadores -----
        self.seg_idx = 0
        self.switches = 0
        self.switches_up = 0
        self.switches_down = 0

        self.qi_history = []        # QI (id/bitrate) escolhido por segmento
        self.qi_idx_history = []    # índice na lista ordenada
        self.bitrate_history = []   # bitrate escolhido (bps), se disponível
        self.budget_history = []    # orçamento usado (EMA*safety)
        self.th_full = []           # throughput amostrado (bps) por segmento


    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        """
        T12: parseia o MPD (payload da msg), extrai lista de QIs e,
        se possível, um mapeamento id->bitrate para ordenação.
        """
        try:
            self.parsed_mpd = parse_mpd(msg.get_payload())
        except Exception as e:
            print(f"[R2ATBEMA] ERRO parse MPD: {e}")
            # ainda assim deixa o fluxo seguir
            self.parsed_mpd = None
            self.qi = []
            self.qi_order = []
            self.i_cur = None
            self.qi_cur = None
            self.send_up(msg)
            return

        # --- extrair lista de QIs (IDs) conforme API da base ---
        qi_list = []
        if hasattr(self.parsed_mpd, "get_qi"):
            try:
                qi_list = list(self.parsed_mpd.get_qi())
            except Exception:
                qi_list = []
        self.qi = qi_list

        # --- tentar obter bitrates (opcional, depende da base) ---
        # Algumas bases expõem get_bitrate() (dict) ou get_bitrates().
        br_map = {}
        for attr in ("get_bitrate", "get_bitrates", "get_qi_bitrates"):
            if hasattr(self.parsed_mpd, attr):
                try:
                    br_map = getattr(self.parsed_mpd, attr)()
                    if isinstance(br_map, dict):
                        break
                except Exception:
                    br_map = {}
        self.bitrate_map = br_map if isinstance(br_map, dict) else {}

        # --- ordenar por bitrate crescente quando possível ---
        if self.qi and self.bitrate_map:
            def _key(qid):
                # Se faltar bitrate de algum id, empurra para o fim
                return self.bitrate_map.get(qid, float("inf"))
            self.qi_order = sorted(self.qi, key=_key)
        else:
            # fallback: mantém ordem vinda do MPD
            self.qi_order = list(self.qi)

        # posição inicial = menor QI (seguro). Decisão real entra no T13.
        self.i_cur = 0 if self.qi_order else None
        self.qi_cur = self.qi_order[self.i_cur] if self.i_cur is not None else None

        print(f"[R2ATBEMA] QIs carregados: {len(self.qi)}")
        if self.bitrate_map and self.qi_order:
            first = self.qi_order[0]
            last = self.qi_order[-1]
            print(f"[R2ATBEMA] Faixa bitrate: "
                  f"{self.bitrate_map.get(first,'?')} .. {self.bitrate_map.get(last,'?')} bps")

        self.send_up(msg)

    # --- helpers (adicione dentro da classe) ---
    def _br(self, qid):
        # bitrate do QI; 0 se desconhecido
        return (self.bitrate_map.get(qid, 0) if isinstance(self.bitrate_map, dict) else 0)

    def _best_idx_by_budget(self, budget_bps):
        # retorna o maior índice em qi_order com bitrate <= budget
        if not self.qi_order:
            return None
        if not self.bitrate_map:
            # sem bitrates: mantém índice atual ou 0
            return self.i_cur if self.i_cur is not None else 0
        idx = 0
        for i, q in enumerate(self.qi_order):
            if self._br(q) <= budget_bps:
                idx = i
            else:
                break
        return idx

    # --- SUBSTITUA ESTE MÉTODO NA CLASSE ---
    def handle_segment_size_request(self, msg):
        self.seg_idx += 1

        # Garantir QIs carregados (T12)
        if not self.qi_order:
            chosen = self.qi[0] if self.qi else None
        else:
            # Orçamento por EMA
            if self.ema_bps is None:
                target_idx = 0
            else:
                budget = self.ema_bps * self.safety
                target_idx = self._best_idx_by_budget(budget)

            cur = self.i_cur if self.i_cur is not None else 0
            tgt = target_idx if target_idx is not None else 0

            cur_q = self.qi_order[cur]
            cur_br = self._br(cur_q)

            if not self.bitrate_map:
                new_idx = tgt
            else:
                can_switch = (self.seg_idx - self.last_switch_seg) >= self.cooldown_segments
                if tgt > cur and can_switch:
                    nxt = min(cur + 1, tgt)
                    nxt_br = self._br(self.qi_order[nxt])
                    if self.ema_bps is not None and self.ema_bps >= (1 + self.up_hys) * nxt_br:
                        new_idx = nxt
                    else:
                        new_idx = cur
                elif tgt < cur:
                    if self.ema_bps is None or self.ema_bps <= (1 - self.down_hys) * cur_br:
                        new_idx = tgt
                    else:
                        new_idx = cur
                else:
                    new_idx = cur

            if new_idx != cur:
                self.switches += 1
                self.switches_up   += int(new_idx > cur)
                self.switches_down += int(new_idx < cur)
                self.last_switch_seg = self.seg_idx
                self.i_cur = new_idx
                self.qi_cur = self.qi_order[new_idx]

            chosen = self.qi_order[self.i_cur] if self.i_cur is not None else (self.qi_order[0] if self.qi_order else None)

        # >>> INJETAR O QI NA MENSAGEM <<<
        if chosen is not None:
            if hasattr(msg, 'add_quality_id'):
                msg.add_quality_id(chosen)
            elif hasattr(msg, 'set_quality_id'):
                msg.set_quality_id(chosen)
            elif hasattr(msg, 'set_quality'):
                msg.set_quality(chosen)

            # histórico
            self.qi_history.append(chosen)
            if self.i_cur is not None:
                self.qi_idx_history.append(self.i_cur)
            if isinstance(self.bitrate_map, dict):
                self.bitrate_history.append(self._br(chosen))
            if self.ema_bps is not None:
                self.budget_history.append(self.ema_bps * self.safety)

        self.send_down(msg)

    # --- helpers: coloque DENTRO da classe R2ATBEMA ---
    def _extract_transfer_stats(self, msg):
        """
        Retorna (bytes, dt_s) a partir de diferentes APIs possíveis da base.
        Se não encontrar, devolve (None, None).
        """
        # 1) tamanho em bytes
        size = None
        for attr in ("get_segment_size", "get_payload_size", "get_body_size", "get_size"):
            if hasattr(msg, attr):
                try:
                    v = getattr(msg, attr)()
                    if isinstance(v, (int, float)) and v > 0:
                        size = int(v)
                        break
                except Exception:
                    pass
        # 2) tempo decorrido (segundos)
        dt = None
        for attr in ("get_time_elapsed", "get_elapsed_time", "get_download_time"):
            if hasattr(msg, attr):
                try:
                    v = getattr(msg, attr)()
                    if isinstance(v, (int, float)) and v > 0:
                        dt = float(v)
                        break
                except Exception:
                    pass
        # 3) fallback: fim - início
        if dt is None:
            t0 = None; t1 = None
            for a in ("get_start_time", "start_time"):
                if hasattr(msg, a):
                    try:
                        t0 = getattr(msg, a)() if a.startswith("get_") else getattr(msg, a)
                        break
                    except Exception:
                        pass
            for a in ("get_end_time", "end_time"):
                if hasattr(msg, a):
                    try:
                        t1 = getattr(msg, a)() if a.startswith("get_") else getattr(msg, a)
                        break
                    except Exception:
                        pass
            if isinstance(t0, (int, float)) and isinstance(t1, (int, float)) and t1 > t0:
                dt = float(t1 - t0)

        return (size, dt) if (size and dt and dt > 0) else (None, None)

    def _update_ema(self, sample_bps):
        if sample_bps is None:
            return
        if self.ema_bps is None:
            self.ema_bps = float(sample_bps)
        else:
            self.ema_bps = self.alpha * float(sample_bps) + (1.0 - self.alpha) * self.ema_bps
        # guarda amostra recente
        try:
            self.th_samples.append(float(sample_bps))
        except Exception:
            pass


    def handle_segment_size_response(self, msg):
        size_bytes, dt_s = self._extract_transfer_stats(msg)
        if size_bytes is not None and dt_s is not None and dt_s > 0:
            thr_bps = 8.0 * float(size_bytes) / float(dt_s)
            self.th_full.append(thr_bps)   # <<< faltava registrar a série usada no finalization
            self._update_ema(thr_bps)
        self.send_up(msg)



    def finalization(self):
        def _avg(lst):
            return (sum(lst) / len(lst)) if lst else 0.0

        n_seg = int(self.seg_idx or 0)
        n_sw  = int(self.switches or 0)
        n_up  = int(self.switches_up or 0)
        n_dn  = int(self.switches_down or 0)

        avg_thr_mbps = _avg(self.th_full)/1e6
        ema_mbps     = (self.ema_bps or 0.0)/1e6
        avg_br_mbps  = (_avg(self.bitrate_history)/1e6) if self.bitrate_history else 0.0
        avg_qi_idx   = _avg(self.qi_idx_history) if self.qi_idx_history else 0.0

        last_qi  = self.qi_cur
        last_idx = self.i_cur if self.i_cur is not None else -1
        last_br  = self._br(self.qi_cur)/1e6 if self.qi_cur is not None else 0.0

        print("> Finalization module R2ATBEMA")
        print(f"Segments decided: {n_seg}")
        print(f"Switches total/up/down: {n_sw}/{n_up}/{n_dn}")
        print(f"Avg throughput: {avg_thr_mbps:.2f} Mbps  |  Final EMA: {ema_mbps:.2f} Mbps")
        print(f"Avg selected bitrate: {avg_br_mbps:.2f} Mbps  |  Avg QI index: {avg_qi_idx:.2f}")
        print(f"Last QI: id={last_qi} idx={last_idx} br={last_br:.2f} Mbps")

