"""Leitura dos parâmetros físicos da junta (fonte única de verdade: parametros.json)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_PADRAO = RAIZ / "parametros.json"


@dataclass(frozen=True)
class Parametros:
    R: float            # resistência de armadura [ohm]
    L: float            # indutância de armadura [H]
    Kt: float           # constante de torque [N m / A]
    Ke: float           # constante de f.c.e.m. [V s / rad]
    J: float            # inércia refletida no eixo do motor [kg m^2]
    b: float            # atrito viscoso refletido [N m s / rad]
    N: float            # relação de redução da harmônica
    V_max: float        # tensão máxima do barramento [V]
    i_max: float        # corrente máxima do driver [A]
    Ts: float           # período de amostragem do laço de posição [s]
    w_op: float         # velocidade do motor no ponto crítico [rad/s]
    T_carga: float      # torque de carga refletido no ponto crítico [N m]
    payload_kg: float
    braco_m: float
    orcamento_ciclo_s: float
    memoria_programa_bytes: int
    atraso_sensor_max_s: float
    ciclos_perdidos_max: int
    prazo_parada_s: float
    distancia_deteccao_m: float
    v_colab_max_m_s: float

    @classmethod
    def carregar(cls, caminho: str | Path = ARQUIVO_PADRAO) -> "Parametros":
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in dados.items() if k in nomes})


def hash_arquivo(caminho: str | Path) -> str:
    """SHA-256 curto de um arquivo — usado no bloco de rastreabilidade do código C."""
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()[:16]
