"""Supervisor de segurança colaborativa da junta (modelo formal).

O supervisor é uma máquina de estados finitos síncrona, executada a cada ciclo do laço
de controle (Ts = 2 ms). Ele é descrito como DADOS (tabela de transições ordenada por
prioridade); a mesma tabela alimenta:
    * a execução de referência em Python (`Supervisor`),
    * o model checker (`auroraarm.verificacao`),
    * o gerador de testes por percurso do grafo (`auroraarm.testes_modelo`),
    * o gerador de código C (`auroraarm.codegen`).

Entradas (amostradas no início do ciclo):
    mao     1 = scanner detecta a mão a menos de 500 mm do efetuador (campo de proteção)
    zona    1 = operador dentro da zona colaborativa (campo de alerta do scanner)
    rearme  1 = botão de rearme pressionado pelo operador
    chegou  1 = a referência limitada voltou a coincidir com a trajetória original
Saídas:
    habilita  1 = driver habilitado (torque permitido); 0 = torque zerado (STO)
    lim_vel   1 = modo colaborativo: velocidade do efetuador <= 250 mm/s
"""
from __future__ import annotations

ESTADOS = ["NORMAL", "REDUZIDA", "PARADA", "AGUARDA_REARME", "RETOMADA"]
ESTADO_INICIAL = "REDUZIDA"          # na partida, assume operador presente (lado seguro)
ENTRADAS = ["mao", "zona", "rearme", "chegou"]

SAIDAS = {
    #                  habilita, lim_vel
    "NORMAL":         (1, 0),
    "REDUZIDA":       (1, 1),
    "PARADA":         (0, 1),
    "AGUARDA_REARME": (0, 1),
    "RETOMADA":       (1, 1),
}

# (id, origem, guarda {entrada: valor exigido}, destino, requisito principal)
# Para cada estado de origem vale a PRIMEIRA transição cuja guarda for verdadeira;
# se nenhuma for, o supervisor permanece no estado.
TRANSICOES_V1 = [
    ("T1", "NORMAL",         {"mao": 1},    "PARADA",         "REQ-SAFE-AA-001"),
    ("T2", "NORMAL",         {"zona": 1},   "REDUZIDA",       "REQ-SAFE-AA-004"),
    ("T3", "REDUZIDA",       {"mao": 1},    "PARADA",         "REQ-SAFE-AA-001"),
    ("T4", "REDUZIDA",       {"zona": 0},   "NORMAL",         "REQ-SAFE-AA-004"),
    ("T5", "PARADA",         {"mao": 0},    "AGUARDA_REARME", "REQ-SAFE-AA-002"),
    ("T6", "AGUARDA_REARME", {"mao": 1},    "PARADA",         "REQ-SAFE-AA-001"),
    ("T7", "AGUARDA_REARME", {"rearme": 1}, "RETOMADA",       "REQ-SAFE-AA-002/003"),
    ("T8", "RETOMADA",       {"mao": 1},    "PARADA",         "REQ-SAFE-AA-001"),
    ("T9", "RETOMADA",       {"chegou": 1}, "REDUZIDA",       "REQ-SAFE-AA-003"),
]

# Versão PRELIMINAR (v0), mantida como evidência do contraexemplo encontrado pelo model
# checker: faltava a transição T8. A premissa implícita era "se o operador acabou de
# rearmar, a mão está longe" — exatamente a condição de borda entre movimento e parada
# que causou o quase-acidente do protótipo anterior.
TRANSICOES_V0 = [t for t in TRANSICOES_V1 if t[0] != "T8"]

TRANSICOES = TRANSICOES_V1


def proximo_estado(estado: str, entradas: dict, transicoes=TRANSICOES):
    """Função de transição pura. Retorna (novo estado, id da transição ou None)."""
    for tid, origem, guarda, destino, _ in transicoes:
        if origem == estado and all(entradas.get(k, 0) == v for k, v in guarda.items()):
            return destino, tid
    return estado, None


class Supervisor:
    """Execução de referência do supervisor (um passo por ciclo de controle)."""

    def __init__(self, transicoes=TRANSICOES):
        self.transicoes = transicoes
        self.estado = ESTADO_INICIAL

    def reset(self):
        self.estado = ESTADO_INICIAL

    def passo(self, mao=0, zona=0, rearme=0, chegou=0):
        entradas = {"mao": int(mao), "zona": int(zona), "rearme": int(rearme), "chegou": int(chegou)}
        self.estado, tid = proximo_estado(self.estado, entradas, self.transicoes)
        hab, lim = SAIDAS[self.estado]
        return hab, lim, tid
