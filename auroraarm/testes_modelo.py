"""Testes baseados em modelo (MBT) gerados a partir do grafo do supervisor (Unidade 3).

Três geradores, todos lendo `supervisor.TRANSICOES` (o modelo), nunca o código:
  1. COBERTURA DE TRANSIÇÕES — para cada transição Tk, o caminho mais curto (busca em
     largura) do estado inicial até a origem de Tk, seguido da entrada que dispara Tk.
  2. COBERTURA DE PARES (estado, entrada) — todos os 5 x 16 pares: leva ao estado e aplica
     cada uma das 16 combinações de entradas; o oráculo é a função de transição do modelo.
     Cobre também as "não transições" (entradas que NÃO devem mudar o estado).
  3. PROPRIEDADES em passeios aleatórios — invariantes derivados dos requisitos:
       I1 (REQ-SAFE-AA-001) mao = 1 em estado com torque  => no mesmo ciclo habilita = 0
       I2 (REQ-SAFE-AA-002) sem torque e rearme = 0       => continua sem torque
       I3 (REQ-SAFE-AA-004) zona = 1 e habilita = 1       => lim_vel = 1
"""
from __future__ import annotations

import itertools
from collections import deque

import numpy as np

from . import supervisor as sup

COMBINACOES = [dict(zip(sup.ENTRADAS, bits)) for bits in itertools.product((0, 1), repeat=4)]


def _caminho_ate(destino):
    """Menor sequência de entradas que leva do estado inicial a `destino`."""
    fila = deque([(sup.ESTADO_INICIAL, [])])
    vistos = {sup.ESTADO_INICIAL}
    while fila:
        est, cam = fila.popleft()
        if est == destino:
            return cam
        for ent in COMBINACOES:
            prox, _ = sup.proximo_estado(est, ent)
            if prox not in vistos:
                vistos.add(prox)
                fila.append((prox, cam + [ent]))
    raise ValueError(f"estado {destino} inalcançável")


def gerar_casos_transicoes():
    """Um caso por transição: (id, sequência de entradas, estado final esperado, Tk final)."""
    casos = []
    for tid, origem, guarda, destino, req in sup.TRANSICOES:
        prefixo = _caminho_ate(origem)
        # entrada que satisfaz a guarda e NÃO é capturada por uma transição de maior prioridade
        for ent in COMBINACOES:
            if all(ent[k] == v for k, v in guarda.items()):
                if sup.proximo_estado(origem, ent)[1] == tid:
                    casos.append({"id": f"MBT-{tid}", "requisito": req,
                                  "entradas": prefixo + [ent],
                                  "estado_esperado": destino, "transicao_esperada": tid})
                    break
    return casos


def gerar_casos_pares():
    casos = []
    for est in sup.ESTADOS:
        prefixo = _caminho_ate(est)
        for ent in COMBINACOES:
            esperado, tid = sup.proximo_estado(est, ent)
            casos.append({"id": f"PAR-{est}-{''.join(str(ent[k]) for k in sup.ENTRADAS)}",
                          "entradas": prefixo + [ent], "estado_esperado": esperado,
                          "transicao_esperada": tid})
    return casos


def executar(casos, fabrica_impl):
    """Roda os casos numa implementação (Python ou C). Devolve falhas e cobertura."""
    falhas, estados, transicoes = [], set(), set()
    for caso in casos:
        impl = fabrica_impl()
        estados.add(impl.estado)
        tid = None
        for ent in caso["entradas"]:
            _, _, tid = impl.passo(**ent)
            estados.add(impl.estado)
            if tid:
                transicoes.add(tid)
        if impl.estado != caso["estado_esperado"] or tid != caso["transicao_esperada"]:
            falhas.append((caso["id"], impl.estado, caso["estado_esperado"]))
    return falhas, estados, transicoes


def passeio_propriedades(fabrica_impl, n_passos=20000, semente=3):
    """Passeio aleatório longo verificando I1..I3 a cada ciclo. Devolve violações."""
    rng = np.random.default_rng(semente)
    impl = fabrica_impl()
    viol = []
    hab_ant = sup.SAIDAS[impl.estado][0]
    for k in range(n_passos):
        ent = {"mao": int(rng.random() < 0.2), "zona": int(rng.random() < 0.5),
               "rearme": int(rng.random() < 0.2), "chegou": int(rng.random() < 0.3)}
        hab, lim, _ = impl.passo(**ent)
        if ent["mao"] == 1 and hab == 1:
            viol.append((k, "I1", ent))
        if hab_ant == 0 and ent["rearme"] == 0 and hab == 1:
            viol.append((k, "I2", ent))
        if ent["zona"] == 1 and hab == 1 and lim == 0:
            viol.append((k, "I3", ent))
        hab_ant = hab
    return viol


def relatorio_cobertura(fabrica_impl, nome="impl"):
    ct, cp = gerar_casos_transicoes(), gerar_casos_pares()
    f1, e1, t1 = executar(ct, fabrica_impl)
    f2, e2, t2 = executar(cp, fabrica_impl)
    viol = passeio_propriedades(fabrica_impl)
    todas_t = {t[0] for t in sup.TRANSICOES}
    return {
        "implementacao": nome,
        "casos_transicao": len(ct), "falhas_transicao": f1,
        "casos_pares": len(cp), "falhas_pares": f2,
        "estados_cobertos": sorted(e1 | e2), "cobertura_estados_pct":
            100 * len(e1 | e2) / len(sup.ESTADOS),
        "transicoes_cobertas": sorted(t1 | t2, key=lambda s: int(s[1:])),
        "cobertura_transicoes_pct": 100 * len((t1 | t2) & todas_t) / len(todas_t),
        "cobertura_pares_pct": 100.0 * len(cp) / (len(sup.ESTADOS) * len(COMBINACOES)),
        "violacoes_propriedades": viol,
    }
