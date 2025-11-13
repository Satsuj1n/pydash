# r2a/r2atbema.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import random  # pode ser útil depois
from player.parser import parse_mpd
from r2a.ir2a import IR2A


class R2ATBEMA(IR2A):
    NAME = "R2ATBEMA"

    def __init__(self, id):
        super().__init__(id)
        self.parsed_mpd = None
        self.qi = []          # lista REAL de quality_ids do MPD (ex.: [150000, 250000, ...])
        # estados para próximas etapas (T09+)
        self.i_cur = 0
        self.ema = None
        self.alpha = 0.20
        self.safety = 0.85
        self.up_hys = 0.15
        self.down_hys = 0.10
        self.cooldown_segments = 3
        self.seg_idx = 0
        self.last_switch_seg = -10**9

    def initialize(self):
        # nada especial no T08
        pass

    # MPD ↓ rede
    def handle_xml_request(self, msg):
        self.send_down(msg)

    # MPD ↑ player: parseia e extrai QIs exatamente como o R2ARandom
    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi() or []
        # print("[R2ATBEMA] QIs:", self.qi)  # debug opcional
        self.send_up(msg)

    # SEGMENTO (decisão) ↓ rede
    def handle_segment_size_request(self, msg):
        # Garantia: se por algum motivo ainda não temos QIs, não inventar — apenas não seta
        if not self.qi:
            # como no R2ARandom, só decide com base na lista do MPD
            # isso evita 'ValueError: X is not in list'
            self.send_down(msg)
            return

        # T08: política mínima — escolher o menor QI disponível
        # (ordena numericamente caso venham como strings)
        try:
            ordered = sorted(self.qi, key=lambda x: float(x))
        except Exception:
            ordered = list(self.qi)

        chosen_qi = ordered[0]
        msg.add_quality_id(chosen_qi)

        self.seg_idx += 1
        self.send_down(msg)

    # SEGMENTO (métricas) ↑ player
    def handle_segment_size_response(self, msg):
        self.send_up(msg)

    def finalization(self):
        # resumo mínimo
        print(f"[R2ATBEMA] segmentos decididos: {self.seg_idx}")
