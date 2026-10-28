"""Identificação e validação do modelo da junta (Unidade 1).

Como não temos a bancada física, o ensaio é *emulado*: a planta com os parâmetros da
tabela gera dados com ruído de medição (encoder e sensor de corrente), excitada por uma
sequência binária pseudoaleatória (PRBS) de tensão e por um degrau de carga.

Método: mínimos quadrados em duas etapas, aproveitando a separação de escalas de tempo
(ver `identificar`): equação elétrica na taxa do ensaio, com inversão exata da ZOH, e
equação mecânica na forma integral em janelas de 10 ms. Com Kt = Ke (motor de ímã
permanente em unidades SI) recuperam-se R, L, Ke, J e b.

Lição registrada: a primeira versão estimava tudo de uma vez, x[k+1] = Ad x[k] + Bd V[k],
a 10 kHz, e errou b em ~120 % por causa do ruído do encoder no regressor (erro nas
variáveis). O teste `tests/test_identificacao.py` impede que esse defeito volte.

Validação: simulação livre (sem realimentar a medição) em um segundo conjunto de dados,
gerado com outra semente e outro perfil de carga, e índice de ajuste NRMSE.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .parametros import Parametros
from .planta import discretizar_zoh, matrizes


@dataclass
class Ensaio:
    t: np.ndarray
    V: np.ndarray
    T_L: np.ndarray
    i: np.ndarray       # corrente medida (com ruído)
    w: np.ndarray       # velocidade medida (com ruído)


def prbs(n, bits_por_nivel, rng):
    niveis = rng.integers(0, 2, size=n // bits_por_nivel + 1) * 2 - 1
    return np.repeat(niveis, bits_por_nivel)[:n].astype(float)


def gerar_ensaio(p: Parametros, semente: int, t_final=1.0, h=1e-4,
                 amp_V=20.0, offset_V=10.0, carga=0.25, t_carga=0.5,
                 ruido_i=0.02, ruido_w=0.5) -> Ensaio:
    """Emula um ensaio de bancada: PRBS de tensão + degrau de carga + ruído de medição."""
    rng = np.random.default_rng(semente)
    n = int(round(t_final / h))
    t = np.arange(n) * h
    V = offset_V + amp_V * prbs(n, int(5e-3 / h), rng)        # nível mínimo de 5 ms
    T_L = np.where(t >= t_carga, carga, 0.0)
    A, B, E, _, _ = matrizes(p)
    Ad, BE = discretizar_zoh(A, np.hstack([B, E]), h)
    x = np.zeros((n, 2))
    for k in range(n - 1):
        x[k + 1] = Ad @ x[k] + BE[:, 0] * V[k] + BE[:, 1] * T_L[k]
    i_med = x[:, 0] + ruido_i * rng.standard_normal(n)
    w_med = x[:, 1] + ruido_w * rng.standard_normal(n)
    return Ensaio(t, V, T_L, i_med, w_med)


def identificar(e: Ensaio, janela_s=10e-3):
    """Identificação em duas etapas (dinâmicas de escalas de tempo separadas).

    1) Elétrica (rápida, tau_e ~ 1,5 ms): mínimos quadrados na amostragem do ensaio,
       i[k+1] = a11 i[k] + a12 w[k] + b1 V[k], e conversão exata para tempo contínuo
       pelo logaritmo matricial (inverso da ZOH)  ->  R, L, Ke.
    2) Mecânica (lenta, tau_m ~ 44 ms): forma integral da equação de Newton em janelas,
       w(t+Tw) - w(t) = (Kt/J) int(i) - (b/J) int(w) - (1/J) int(T_L).
       A integração filtra o ruído do encoder; a regressão direta na taxa de 10 kHz
       ficaria enviesada (erro nas variáveis: ruído no regressor w).
       Com Kt = Ke (ímã permanente, SI)  ->  J, b.
    """
    h = e.t[1] - e.t[0]
    # ---- etapa 1: equação elétrica
    Phi = np.column_stack([e.i[:-1], e.w[:-1], e.V[:-1]])
    th, *_ = np.linalg.lstsq(Phi, e.i[1:], rcond=None)
    # inverso da ZOH escalar: com w e V tratados como entradas constantes no passo h
    a11 = th[0]
    a_c = np.log(a11) / h                         # = -R/L
    fator = a_c / (a11 - 1.0)                     # converte ganhos discretos em contínuos
    c_w, c_V = th[1] * fator, th[2] * fator       # = -Ke/L e 1/L
    L = 1.0 / c_V
    R = -a_c * L
    Ke = -c_w * L
    Kt = Ke
    # ---- etapa 2: equação mecânica na forma integral
    m = int(round(janela_s / h))
    nj = (e.t.size - 1) // m
    linhas, alvo = [], []
    for j in range(nj):
        s = slice(j * m, (j + 1) * m + 1)
        int_i = np.trapezoid(e.i[s], dx=h)
        int_w = np.trapezoid(e.w[s], dx=h)
        int_T = np.trapezoid(e.T_L[s], dx=h)
        linhas.append([int_i, -int_w, -int_T])
        alvo.append(e.w[s][-1] - e.w[s][0])
    g, *_ = np.linalg.lstsq(np.array(linhas), np.array(alvo), rcond=None)
    # g = [Kt/J, b/J, 1/J]; Kt/J e 1/J são redundantes com Kt conhecido -> média ponderada
    J = 0.5 * (Kt / g[0] + 1.0 / g[2])
    b = g[1] * J
    return {"R": R, "L": L, "Ke": Ke, "Kt": Kt, "J": J, "b": b}


def simular_livre(param: dict, e: Ensaio):
    """Simulação livre do modelo identificado com as entradas do ensaio."""
    h = e.t[1] - e.t[0]
    A = np.array([[-param["R"] / param["L"], -param["Ke"] / param["L"]],
                  [param["Kt"] / param["J"], -param["b"] / param["J"]]])
    B = np.array([[1 / param["L"]], [0.0]])
    E = np.array([[0.0], [-1 / param["J"]]])
    Ad, BE = discretizar_zoh(A, np.hstack([B, E]), h)
    x = np.zeros((e.t.size, 2))
    for k in range(e.t.size - 1):
        x[k + 1] = Ad @ x[k] + BE[:, 0] * e.V[k] + BE[:, 1] * e.T_L[k]
    return x[:, 0], x[:, 1]


def nrmse_fit(y, yhat):
    """Índice de ajuste em % (100 = perfeito), como no System Identification Toolbox."""
    return 100.0 * (1.0 - np.linalg.norm(y - yhat) / np.linalg.norm(y - y.mean()))


def rodar(p: Parametros):
    est = gerar_ensaio(p, semente=1)
    val = gerar_ensaio(p, semente=2, amp_V=15.0, offset_V=5.0, carga=0.15, t_carga=0.3)
    par = identificar(est)
    i_hat, w_hat = simular_livre(par, val)
    nominal = {k: getattr(p, k) for k in ("R", "L", "Ke", "Kt", "J", "b")}
    erro_pct = {k: 100 * (par[k] - nominal[k]) / nominal[k] for k in nominal}
    return {
        "identificado": par,
        "nominal": nominal,
        "erro_pct": erro_pct,
        "fit_w_pct": nrmse_fit(val.w, w_hat),
        "fit_i_pct": nrmse_fit(val.i, i_hat),
        "_validacao": (val, i_hat, w_hat),
    }
