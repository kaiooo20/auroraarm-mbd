"""Modelo da planta: motor CC de ímã permanente + transmissão harmônica 100:1.

Leis de conservação (referidas ao eixo do motor):
    elétrica (Kirchhoff, malha da armadura):  L di/dt = V - R i - Ke w
    mecânica (2a lei de Newton na rotação):   J dw/dt = Kt i - b w - T_L
    cinemática:                               d(theta_m)/dt = w ,  theta_junta = theta_m / N

Estados do modelo de memorial (item a):  x = [i, w]^T,  u = V,  d = T_L,  y = w
Estados do modelo de posição (controle): x = [theta_m, i, w]^T
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from .parametros import Parametros


# ----------------------------------------------------------------- matrizes
def matrizes(p: Parametros):
    """Modelo de 2 estados x=[i, w] (memorial, item a).

    Retorna A, B (entrada V), E (entrada de perturbação T_L), C (saída w), D.
    """
    A = np.array([[-p.R / p.L, -p.Ke / p.L],
                  [p.Kt / p.J, -p.b / p.J]])
    B = np.array([[1.0 / p.L], [0.0]])
    E = np.array([[0.0], [-1.0 / p.J]])
    C = np.array([[0.0, 1.0]])
    D = np.array([[0.0]])
    return A, B, E, C, D


def matrizes_posicao(p: Parametros):
    """Modelo de 3 estados x=[theta_m, i, w] usado no laço de posição. Saída: theta_m."""
    A2, B2, E2, _, _ = matrizes(p)
    A = np.zeros((3, 3))
    A[0, 2] = 1.0
    A[1:, 1:] = A2
    B = np.vstack([[0.0], B2])
    E = np.vstack([[0.0], E2])
    C = np.array([[1.0, 0.0, 0.0]])
    return A, B, E, C


# ----------------------------------------------------------------- análise
def autovalores(p: Parametros):
    A, *_ = matrizes(p)
    return np.sort(np.linalg.eigvals(A).real)  # [polo elétrico (mais rápido), polo mecânico]


def constantes_de_tempo(p: Parametros):
    """tau_e e tau_m como inverso dos módulos dos autovalores de A."""
    lam = autovalores(p)
    return 1.0 / abs(lam[0]), 1.0 / abs(lam[1])


def matriz_controlabilidade(A, B):
    n = A.shape[0]
    return np.hstack([np.linalg.matrix_power(A, k) @ B for k in range(n)])


def matriz_observabilidade(A, C):
    n = A.shape[0]
    return np.vstack([C @ np.linalg.matrix_power(A, k) for k in range(n)])


def ponto_de_operacao(p: Parametros, w=None, T_L=None):
    """Regime permanente (dx/dt = 0):  Kt i = b w + T_L ;  V = R i + Ke w."""
    w = p.w_op if w is None else w
    T_L = p.T_carga if T_L is None else T_L
    i_ss = (p.b * w + T_L) / p.Kt
    V_ss = p.R * i_ss + p.Ke * w
    return i_ss, V_ss


# ----------------------------------------------------------------- discretização
def discretizar_zoh(A, B, Ts):
    """Discretização exata com segurador de ordem zero: [Ad Bd; 0 I] = expm([A B; 0 0] Ts)."""
    n, m = A.shape[0], B.shape[1]
    M = np.zeros((n + m, n + m))
    M[:n, :n] = A
    M[:n, n:] = B
    Md = expm(M * Ts)
    return Md[:n, :n], Md[:n, n:]


# ----------------------------------------------------------------- simulação
class SimuladorJunta:
    """Simulação exata (ZOH) da planta de 3 estados com sub-passos internos.

    Entre duas amostras do controlador a tensão é constante (ZOH), então a solução
    linear exata é usada em `sub` sub-passos só para registrar picos de corrente.
    """

    def __init__(self, p: Parametros, sub: int = 20):
        self.p = p
        self.sub = sub
        A, B, E, _ = matrizes_posicao(p)
        h = p.Ts / sub
        self.Ad, BE = discretizar_zoh(A, np.hstack([B, E]), h)
        self.Bd, self.Ed = BE[:, :1], BE[:, 1:]
        # Driver DESABILITADO (torque seguro desligado): a ponte deixa de impor tensão e a
        # corrente decai. Modelo conservador: L di/dt = -R i (decaimento só pela resistência,
        # sem ajuda da tensão do barramento nos diodos), então o torque some com tau_e.
        A_off = A.copy()
        A_off[1, 2] = 0.0
        self.Ad_off, Ed_off = discretizar_zoh(A_off, E, h)
        self.Ed_off = Ed_off[:, 0]
        self.x = np.zeros(3)

    def reset(self, x0=None):
        self.x = np.zeros(3) if x0 is None else np.asarray(x0, float).copy()

    def passo(self, V: float, T_L: float, habilitado: bool = True):
        """Avança um período Ts. Retorna (estado final, |i| máximo durante o período)."""
        imax = abs(self.x[1])
        for _ in range(self.sub):
            if habilitado:
                self.x = self.Ad @ self.x + self.Bd[:, 0] * V + self.Ed[:, 0] * T_L
            else:
                self.x = self.Ad_off @ self.x + self.Ed_off * T_L
            imax = max(imax, abs(self.x[1]))
        return self.x.copy(), imax


def simular_malha_aberta(p: Parametros, V, T_L, t_final, dt=None):
    """Resposta de malha aberta do modelo de 2 estados para V(t), T_L(t) (funções)."""
    A, B, E, _, _ = matrizes(p)
    dt = dt or p.L / p.R / 20
    Ad, BE = discretizar_zoh(A, np.hstack([B, E]), dt)
    n = int(round(t_final / dt)) + 1
    t = np.arange(n) * dt
    x = np.zeros((n, 2))
    for k in range(n - 1):
        x[k + 1] = Ad @ x[k] + BE[:, 0] * V(t[k]) + BE[:, 1] * T_L(t[k])
    return t, x[:, 0], x[:, 1]
