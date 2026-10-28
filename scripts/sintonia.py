"""Sintonia do PID (Unidade 2): ponto de partida analítico + refinamento por simulação.

1) Modelo reduzido (despreza tau_e, que é ~28x mais rápida que tau_m):
       theta_m(s)/V(s) = K / (s (tau s + 1)),  K = Kt/(R b + Kt Ke),  tau = R J/(R b + Kt Ke)
   Com PID, a equação característica é  tau s^3 + (1 + K Kd) s^2 + K Kp s + K Ki = 0.
   Impondo três polos em -p:  Kp = 3 p^2 tau / K,  Ki = p^3 tau / K,  Kd = (3 p tau - 1)/K.
2) Como o degrau de 0,1 rad (10 rad no motor) leva o laço ao limite de corrente, o desempenho
   real é não linear. Os ganhos (Kp, Ki, Kd, beta, Kaw) são refinados por Nelder-Mead
   minimizando o tempo de acomodação com penalidade de sobressinal acima de 4 % sobre um
   conjunto de cenários: degraus de +/-10 rad e 2 rad, carga de +0,25, 0 e -0,25 N m.

Uso:  python scripts/sintonia.py         (imprime ganhos analíticos e o resultado refinado)
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auroraarm.parametros import Parametros          # noqa: E402
from auroraarm import controlador as c               # noqa: E402

p = Parametros.carregar()
den = p.R * p.b + p.Kt * p.Ke
K, tau = p.Kt / den, p.R * p.J / den
A = c.DEGRAU_JUNTA * p.N
CENARIOS = [(a, tl) for a in (A, -A, 0.2 * A) for tl in (p.T_carga, 0.0, -p.T_carga)]


def analitico(pz):
    return dict(Kp=3 * pz**2 * tau / K, Ki=pz**3 * tau / K, Kd=(3 * pz * tau - 1) / K)


def ganhos(x):
    return dict(Kp=x[0], Ki=x[1], Kd=x[2], beta=x[3], Kaw=x[4], Tf=1e-3)


def custo(x):
    if min(x) <= 0 or x[3] > 1 or x[4] > 1:
        return 1e3
    coef = c.coeficientes(p, ganhos(x))
    pior_ts, pior_os, erro = 0.0, 0.0, 0.0
    for amp, tl in CENARIOS:
        m, _ = c.ensaio_degrau(p, amp, coef, T_carga=tl)
        ts = m["t_acomodacao_s"] if np.isfinite(m["t_acomodacao_s"]) else 2.0
        pior_ts, pior_os = max(pior_ts, ts), max(pior_os, m["sobressinal_pct"])
        erro += m["erro_regime_rad"] / abs(amp)
    return pior_ts + 0.02 * max(0.0, pior_os - 4.0) ** 2 + 50 * erro


if __name__ == "__main__":
    print(f"K = {K:.4f} rad/(V s)   tau = {1000*tau:.2f} ms")
    for pz in (20, 30, 42):
        print(f"polo triplo em -{pz}: ", {k: round(v, 4) for k, v in analitico(pz).items()})
    g0 = analitico(30)
    x0 = [g0["Kp"], g0["Ki"], g0["Kd"], 0.5, 0.3]
    r = minimize(custo, x0, method="Nelder-Mead",
                 options=dict(maxiter=int(sys.argv[1]) if len(sys.argv) > 1 else 300,
                              xatol=1e-3, fatol=1e-4))
    print("refinado:", {k: round(v, 4) for k, v in ganhos(r.x).items()}, "custo", round(r.fun, 4))
