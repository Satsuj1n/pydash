# r2a/r2abba.py
from __future__ import annotations

from r2a.ir2a import IR2A
from player.parser import parse_mpd  # mesma base usada no R2ATBEMA


class R2ABBA(IR2A):
    """
    BBA (Huang et al., 2014) – decisão baseada apenas no nível de buffer:
    - buffer <= R          -> menor qualidade
    - buffer >= R + C      -> maior qualidade
    - R < buffer < R + C   -> mapeamento linear para bitrate alvo
    """

    NAME = "R2ABBA"

    def __init__(self, id):
        super().__init__(id)

        # será inicializado em initialize()
        self.qi = []
        self.qi_order = []
        self.i_cur = None
        self.qi_cur = None

        self.parsed_mpd = None
        self.bitrate_map = {}

        self.buffer_sec = 0.0
        self.reservoir_sec = 5.0   # R
        self.cushion_sec = 15.0    # C

        self.seg_idx = 0
        self.qi_history = []
        self.qi_idx_history = []
        self.buf_history = []

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def initialize(self):
        # nada especial além do que já foi criado no __init__
        # mantemos aqui por compatibilidade com a interface
        self.buffer_sec = 0.0
        self.seg_idx = 0
        self.qi_history = []
        self.qi_idx_history = []
        self.buf_history = []

    # ------------------------------------------------------------------
    # XML / MPD
    # ------------------------------------------------------------------

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        """
        Parse MPD e extrai QIs e bitrates, no mesmo estilo do R2ATBEMA.
        """
        try:
            self.parsed_mpd = parse_mpd(msg.get_payload())
        except Exception as e:
            print(f"[R2ABBA] ERRO parse MPD: {e}")
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
                return self.bitrate_map.get(qid, float("inf"))
            self.qi_order = sorted(self.qi, key=_key)
        else:
            self.qi_order = list(self.qi)

        # posição inicial = menor QI
        self.i_cur = 0 if self.qi_order else None
        self.qi_cur = self.qi_order[self.i_cur] if self.i_cur is not None else None

        print(f"[R2ABBA] QIs carregados: {len(self.qi)}")
        if self.bitrate_map and self.qi_order:
            first = self.qi_order[0]
            last = self.qi_order[-1]
            print(f"[R2ABBA] Faixa bitrate: "
                  f"{self.bitrate_map.get(first,'?')} .. {self.bitrate_map.get(last,'?')} bps")

        self.send_up(msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _br(self, qid):
        return (self.bitrate_map.get(qid, 0)
                if isinstance(self.bitrate_map, dict) else 0)

    def _get_buffer_level(self):
        """
        Lê o nível de buffer pelo Whiteboard:
        whiteboard.get_playback_buffer_size() -> lista de (t, buffer_s)
        Usa o último valor disponível. Se nada vier, mantém o valor anterior.
        """
        try:
            if not hasattr(self, "whiteboard") or self.whiteboard is None:
                return self.buffer_sec

            buf_list = self.whiteboard.get_playback_buffer_size()
            if not buf_list:
                return self.buffer_sec

            # cada entrada: (tempo, buffer_em_segundos)
            last_t, last_buf = buf_list[-1]
            if isinstance(last_buf, (int, float)):
                return float(last_buf)
        except Exception as e:
            print(f"[R2ABBA] Erro ao ler buffer do Whiteboard: {e}")

        return self.buffer_sec

    def _select_index_bba(self, buffer_sec: float):
        """
        Regra BBA: mapeia buffer -> índice em qi_order.
        """
        if not self.qi_order:
            return None

        R = self.reservoir_sec
        C = self.cushion_sec
        B = max(buffer_sec, 0.0)

        # Sem bitrates: usa apenas posição
        if not self.bitrate_map:
            if B <= R:
                return 0
            elif B >= R + C:
                return len(self.qi_order) - 1
            else:
                frac = (B - R) / C
                frac = max(0.0, min(1.0, frac))
                idx = int(round(frac * (len(self.qi_order) - 1)))
                return idx

        # Com bitrates
        min_br = self._br(self.qi_order[0])
        max_br = self._br(self.qi_order[-1])

        if B <= R:
            return 0
        if B >= R + C:
            return len(self.qi_order) - 1

        if max_br <= min_br:
            return 0

        frac = (B - R) / C
        frac = max(0.0, min(1.0, frac))
        target_br = min_br + frac * (max_br - min_br)

        idx = 0
        for i, q in enumerate(self.qi_order):
            if self._br(q) <= target_br:
                idx = i
            else:
                break
        return idx

    # ------------------------------------------------------------------
    # Segmento: decisão BBA
    # ------------------------------------------------------------------

    def handle_segment_size_request(self, msg):
        """
        Decide o QI com base no nível de buffer atual (BBA).
        """
        self.seg_idx += 1

        # atualiza buffer a partir do Whiteboard
        self.buffer_sec = self._get_buffer_level()

        if not self.qi_order:
            chosen = self.qi[0] if self.qi else None
        else:
            idx = self._select_index_bba(self.buffer_sec)
            if idx is None:
                idx = self.i_cur if self.i_cur is not None else 0
            idx = max(0, min(idx, len(self.qi_order) - 1))
            self.i_cur = idx
            self.qi_cur = self.qi_order[idx]
            chosen = self.qi_cur

        if chosen is not None:
            if hasattr(msg, 'add_quality_id'):
                msg.add_quality_id(chosen)
            elif hasattr(msg, 'set_quality_id'):
                msg.set_quality_id(chosen)
            elif hasattr(msg, 'set_quality'):
                msg.set_quality(chosen)

            self.qi_history.append(chosen)
            if self.i_cur is not None:
                self.qi_idx_history.append(self.i_cur)
            self.buf_history.append(self.buffer_sec)

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        """
        Atualiza buffer novamente (se houver novos dados) e sobe a mensagem.
        """
        self.buffer_sec = self._get_buffer_level()
        self.send_up(msg)

    # ------------------------------------------------------------------
    # Finalização
    # ------------------------------------------------------------------

    def finalization(self):
        def _avg(lst):
            return (sum(lst) / len(lst)) if lst else 0.0

        n_seg = int(self.seg_idx or 0)
        avg_buf = _avg(self.buf_history)
        avg_qidx = _avg(self.qi_idx_history) if self.qi_idx_history else 0.0

        last_qi = self.qi_cur
        last_idx = self.i_cur if self.i_cur is not None else -1
        last_buf = self.buffer_sec

        print("> Finalization module R2ABBA (BBA)")
        print(f"Segments decided: {n_seg}")
        print(f"Avg buffer level: {avg_buf:.2f} s  |  Avg QI index: {avg_qidx:.2f}")
        print(f"Last QI: id={last_qi} idx={last_idx}  |  Last buffer={last_buf:.2f} s")
