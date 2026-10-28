"""Controlador de posição da junta: PID discreto com saturação, limite de corrente e anti-windup.

O controlador é descrito como um MODELO executável: uma lista de passos de fluxo de dados
(representação intermediária, "IR"). O mesmo modelo é
    * interpretado em Python (referência, em float64 ou float32), e
    * traduzido para C por `auroraarm.codegen` (nada de C escrito à mão).
Assim a equivalência modelo-código (memorial, item e) compara duas execuções da mesma
especificação.

Estrutura (forma paralela, Ts = 2 ms):
    r      = limitador de velocidade e aceleração aplicado a r_cmd (modo colaborativo)
    e      = r - y                                   erro de posição (rad no eixo do motor)
    P      = Kp (beta r - y)                         ponderação de referência (PID 2-GDL)
    D[k]   = ad D[k-1] - bd (y[k] - y[k-1])          derivada SÓ da medição, com filtro (Tf)
    u      = P + I + D
    janela de tensão que mantém |i| <= i_lim, depois o limite do barramento (REQ-CTRL-AA-004):
        u_i    = sat(u, Ke w_hat - R i_lim, Ke w_hat + R i_lim)
        u_sat  = sat(u_i, -V_max, +V_max)
    (versão anterior saturava com min/max combinados; o teste aleatório do SIL mostrou que,
     se |Ke w_hat| > V_max + R i_lim, a janela se invertia e a saída passava de 48 V.)
    I[k+1] = I[k] + Ki Ts e + Kaw (u_sat - u)          anti-windup por retrocálculo
    se habilita == 0: u_sat = 0, I = 0, D = 0          (torque desligado pelo supervisor)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .parametros import Parametros
from .planta import SimuladorJunta

# --------------------------------------------------------------------------- ganhos
# Sintonia final (ver scripts/sintonia.py): ponto de partida analítico por alocação de
# polos no modelo reduzido + refinamento por simulação do laço não linear.
GANHOS_PADRAO = {"Kp": 10.1, "Ki": 125.0, "Kd": 0.23, "Tf": 1.0e-3, "beta": 0.55, "Kaw": 0.30}
I_LIM = 7.5        # A: margem de 0,5 A abaixo de i_max = 8 A (atraso da estimativa de w)
A_COLAB = 600.0     # rad/s^2 no eixo do motor, aceleração máxima da referência colaborativa
DEGRAU_JUNTA = 0.1  # rad na junta = 10 rad no eixo do motor (premissa do ensaio de degrau)


def coeficientes(p: Parametros, ganhos: dict | None = None) -> dict:
    """Constantes do controlador já combinadas (o que vai para o código C)."""
    g = {**GANHOS_PADRAO, **(ganhos or {})}
    Ts, Tf = p.Ts, g["Tf"]
    Kaw = g["Kaw"]                       # ganho de retrocálculo (adimensional, por amostra)
    return {
        "KP": g["Kp"],
        "BETA": g["beta"],
        "KI_TS": g["Ki"] * Ts,
        "AD": Tf / (Tf + Ts),
        "BD": g["Kd"] / (Tf + Ts),
        "KAW": Kaw,
        "INV_TS": 1.0 / Ts,
        "KE": p.Ke,
        "R_ILIM": p.R * I_LIM,
        "V_MAX": p.V_max,
        "V_MIN": -p.V_max,
        "ZERO": 0.0,
        # velocidade máxima do motor em modo colaborativo (REQ-SAFE-AA-004), com 15 % de folga:
        # v_efetuador = (w_motor / N) * r_braco  ->  w_motor <= N v_max / r_braco
        "DMAX_COLAB": 0.85 * p.N * p.v_colab_max_m_s / p.braco_m * Ts,
        "DMAX_LIVRE": 1.0e3,
        # desaceleração máxima da referência em modo colaborativo: 600 rad/s^2 no motor
        # (< (Kt i_lim - T_L)/J = 923 rad/s^2, o que o motor consegue com folga de corrente)
        "AMAX_COLAB": A_COLAB * Ts * Ts,
        "AMAX_LIVRE": 1.0e3,
    }


# --------------------------------------------------------------------------- modelo (IR)
ENTRADAS = ["r_cmd", "y", "habilita", "lim_vel"]
ESTADOS = ["integ", "deriv", "y_prev", "r_prev", "v_prev"]
SAIDA = "u_out"

# (destino, operação, operando1, operando2[, operando3])
PASSOS = [
    # --- limitador de velocidade E de aceleração da referência (REQ-SAFE-AA-003 e 004)
    #     v_prev = passo de referência do ciclo anterior (rad/amostra = velocidade * Ts).
    #     Em modo colaborativo a velocidade cai até DMAX_COLAB com desaceleração limitada
    #     (AMAX_COLAB); sem o limite de aceleração a referência "freava" instantaneamente,
    #     o motor ultrapassava a referência e oscilava (v de pico 0,42 m/s > 0,25 m/s).
    ("dr",      "sub", "r_cmd", "r_prev"),
    ("dmax",    "sel", "lim_vel", "DMAX_COLAB", "DMAX_LIVRE"),
    ("dmin",    "sub", "ZERO", "dmax"),
    ("dr1",     "min", "dr", "dmax"),
    ("dr2",     "max", "dr1", "dmin"),
    ("amax",    "sel", "lim_vel", "AMAX_COLAB", "AMAX_LIVRE"),
    ("amin",    "sub", "ZERO", "amax"),
    ("dv",      "sub", "dr2", "v_prev"),
    ("dv1",     "min", "dv", "amax"),
    ("dv2",     "max", "dv1", "amin"),
    ("v",       "add", "v_prev", "dv2"),
    ("r",       "add", "r_prev", "v"),
    # --- PID 2-GDL: P com ponderação beta, D só na medição (filtrado), I com anti-windup
    ("e",       "sub", "r", "y"),
    ("dy",      "sub", "y", "y_prev"),
    ("w_hat",   "mul", "dy", "INV_TS"),
    ("t1",      "mul", "AD", "deriv"),
    ("t2",      "mul", "BD", "dy"),
    ("d_new",   "sub", "t1", "t2"),
    ("br",      "mul", "BETA", "r"),
    ("e_p",     "sub", "br", "y"),
    ("p_term",  "mul", "KP", "e_p"),
    ("t3",      "add", "p_term", "integ"),
    ("u",       "add", "t3", "d_new"),
    # --- saturação: janela de tensão que respeita V_max e i_lim (REQ-CTRL-AA-004)
    ("fcem",    "mul", "KE", "w_hat"),
    ("v_hi0",   "add", "fcem", "R_ILIM"),
    ("v_lo0",   "sub", "fcem", "R_ILIM"),
    ("t4",      "min", "u", "v_hi0"),       # janela de corrente
    ("t4b",     "max", "t4", "v_lo0"),
    ("t4c",     "min", "t4b", "V_MAX"),     # limite do barramento por ÚLTIMO: prevalece
    ("u_sat",   "max", "t4c", "V_MIN"),     # mesmo se a janela de corrente se inverter
    # --- integrador com retrocálculo (anti-windup)
    ("t5",      "mul", "KI_TS", "e"),
    ("t6",      "sub", "u_sat", "u"),
    ("t7",      "mul", "KAW", "t6"),
    ("t8",      "add", "integ", "t5"),
    ("i_new",   "add", "t8", "t7"),
    # --- habilita (0/1), vindo do supervisor: operação normal ou torque zero
    #     com torque desligado a referência "segue" a medição, para retomar sem salto
    ("u_out",   "sel", "habilita", "u_sat", "ZERO"),
    ("integ",   "sel", "habilita", "i_new", "ZERO"),
    ("deriv",   "sel", "habilita", "d_new", "ZERO"),
    ("r_prev",  "sel", "habilita", "r", "y"),
    ("v_prev",  "sel", "habilita", "v", "ZERO"),
    ("y_prev",  "mov", "y"),
]


class ControladorReferencia:
    """Intérprete do modelo (PASSOS) — é a implementação de referência do SIL."""

    def __init__(self, coef: dict, dtype=np.float64):
        self.dt = dtype
        self.coef = {k: dtype(v) for k, v in coef.items()}
        self.reset()

    def reset(self):
        self.estado = {k: self.dt(0.0) for k in ESTADOS}

    def passo(self, r_cmd, y, habilita=True, lim_vel=False) -> float:
        dt = self.dt
        v = {**self.coef, **self.estado,
             "r_cmd": dt(r_cmd), "y": dt(y),
             "habilita": dt(1.0 if habilita else 0.0), "lim_vel": dt(1.0 if lim_vel else 0.0)}
        for passo in PASSOS:
            dest, op, *a = passo
            x = [v[n] for n in a]
            if op == "add":
                v[dest] = dt(x[0] + x[1])
            elif op == "sub":
                v[dest] = dt(x[0] - x[1])
            elif op == "mul":
                v[dest] = dt(x[0] * x[1])
            elif op == "min":
                v[dest] = x[0] if x[0] < x[1] else x[1]
            elif op == "max":
                v[dest] = x[0] if x[0] > x[1] else x[1]
            elif op == "sel":
                v[dest] = x[1] if x[0] > dt(0.5) else x[2]
            elif op == "mov":
                v[dest] = x[0]
            else:  # pragma: no cover
                raise ValueError(op)
        for k in ESTADOS:
            self.estado[k] = v[k]
        self.ultimo = v
        return v[SAIDA]


# --------------------------------------------------------------------------- simulação
@dataclass
class Resultado:
    t: np.ndarray
    r: np.ndarray
    theta: np.ndarray
    w: np.ndarray
    i: np.ndarray
    i_pico: np.ndarray
    V: np.ndarray
    integ: np.ndarray
    extra: dict = field(default_factory=dict)


def simular_malha_fechada(p: Parametros, coef: dict, referencia, t_final=0.6,
                          T_L=None, habilita=None, controlador=None, planta_p=None,
                          lim_vel=None):
    """Laço fechado: controlador discreto (Ts) + planta exata entre amostras.

    referencia(t) -> posição desejada no eixo do motor [rad]; T_L(t) -> carga [N m].
    `planta_p` permite simular uma planta diferente da usada no projeto (robustez).
    """
    T_L = T_L or (lambda t: p.T_carga)
    habilita = habilita or (lambda t: True)
    lim_vel = lim_vel or (lambda t: False)
    ctrl = controlador or ControladorReferencia(coef)
    sim = SimuladorJunta(planta_p or p)
    n = int(round(t_final / p.Ts)) + 1
    out = {k: np.zeros(n) for k in ("t", "r", "theta", "w", "i", "i_pico", "V", "integ")}
    for k in range(n):
        t = k * p.Ts
        th, i_, w_ = sim.x
        en = habilita(t)
        V = float(ctrl.passo(referencia(t), th, en, lim_vel(t)))
        out["t"][k], out["r"][k], out["theta"][k] = t, referencia(t), th
        out["w"][k], out["i"][k], out["V"][k] = w_, i_, V
        out["integ"][k] = float(ctrl.estado["integ"])
        _, ipk = sim.passo(V, T_L(t), en)
        out["i_pico"][k] = ipk
    return Resultado(**out)


def metricas_degrau(res: Resultado, amplitude: float, faixa=0.02):
    """Sobressinal (%), tempo de acomodação (faixa de 2 %) e erro em regime (últimos 50 ms).

    Funciona para degraus positivos e negativos (normaliza pelo sinal da amplitude).
    """
    s = 1.0 if amplitude >= 0 else -1.0
    y, t, a = s * res.theta, res.t, abs(amplitude)
    os_pct = max(0.0, 100.0 * (y.max() - a) / a)
    fora = np.abs(y - a) > faixa * a
    idx = np.nonzero(fora)[0]
    if not idx.size:
        ts = 0.0
    elif idx[-1] + 1 < t.size:
        ts = float(t[idx[-1] + 1])
    else:
        ts = float("inf")
    n_reg = max(1, int(0.05 / (t[1] - t[0])))
    erro_reg = abs(a - y[-n_reg:].mean())
    return {"sobressinal_pct": os_pct, "t_acomodacao_s": ts, "erro_regime_rad": erro_reg,
            "V_max_abs": float(np.abs(res.V).max()), "i_max_abs": float(res.i_pico.max())}


def ensaio_degrau(p: Parametros, amplitude: float, coef: dict | None = None, t0=0.3,
                  duracao=0.6, T_carga=None, planta_p=None, controlador=None):
    """Degrau de posição aplicado em t0, com a junta já em equilíbrio sob carga.

    Retorna (métricas, resultado completo). Tempos das métricas contados a partir de t0.
    """
    coef = coef or coeficientes(p)
    TL = p.T_carga if T_carga is None else T_carga
    res = simular_malha_fechada(p, coef, lambda t: amplitude if t >= t0 else 0.0,
                                t_final=t0 + duracao, T_L=lambda t: TL,
                                planta_p=planta_p, controlador=controlador)
    m = res.t >= t0
    sub = Resultado(res.t[m] - t0, res.r[m], res.theta[m], res.w[m], res.i[m],
                    res.i_pico[m], res.V[m], res.integ[m])
    return metricas_degrau(sub, amplitude), res
