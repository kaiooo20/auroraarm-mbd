"""REQ-CTRL-AA-001..004 — controlador em malha fechada com a planta."""
import dataclasses

import numpy as np
import pytest

from auroraarm import controlador as ctl

CENARIOS = [(a, tl) for a in (10.0, -10.0, 2.0) for tl in (0.25, 0.0, -0.25)]


@pytest.mark.parametrize("amp,tl", CENARIOS)
def test_req_ctrl_001_a_004(p, amp, tl):
    m, res = ctl.ensaio_degrau(p, amp, T_carga=tl)
    assert m["erro_regime_rad"] < 1e-3 * abs(amp)       # REQ-CTRL-AA-001 (erro nulo)
    assert m["sobressinal_pct"] <= 8.0                    # REQ-CTRL-AA-002
    assert m["t_acomodacao_s"] <= 0.300                   # REQ-CTRL-AA-003
    assert np.abs(res.V).max() <= p.V_max + 1e-9          # REQ-CTRL-AA-004 (tensão)
    assert res.i_pico.max() <= p.i_max                    # REQ-CTRL-AA-004 (corrente)


@pytest.mark.parametrize("fator", [0.8, 1.2])
def test_robustez_inercia(p, fator):
    m, _ = ctl.ensaio_degrau(p, 10.0, planta_p=dataclasses.replace(p, J=p.J * fator))
    assert m["sobressinal_pct"] <= 8.0 and m["t_acomodacao_s"] <= 0.300


def test_anti_windup_e_necessario(p):
    m_sem, _ = ctl.ensaio_degrau(p, 10.0, coef=ctl.coeficientes(p, {"Kaw": 0.0}))
    assert m_sem["sobressinal_pct"] > 8.0                 # sem retrocálculo o requisito falha


def test_saturacao_nunca_passa_de_48V_mesmo_com_entrada_absurda(p):
    c = ctl.ControladorReferencia(ctl.coeficientes(p))
    rng = np.random.default_rng(0)
    for _ in range(5000):
        u = c.passo(rng.uniform(-1e3, 1e3), rng.uniform(-1e3, 1e3), True, rng.random() > 0.5)
        assert abs(u) <= p.V_max


def test_torque_zero_quando_desabilitado(p):
    c = ctl.ControladorReferencia(ctl.coeficientes(p))
    c.passo(10.0, 0.0, True)
    assert c.passo(10.0, 0.0, False) == 0.0
    assert c.estado["integ"] == 0.0                       # REQ-SAFE-AA-002: sem memória do erro


def test_modo_colaborativo_limita_velocidade(p):
    coef = ctl.coeficientes(p)
    wl = p.N * p.v_colab_max_m_s / p.braco_m
    res = ctl.simular_malha_fechada(p, coef, lambda t: 200.0 * t, t_final=1.0,
                                    lim_vel=lambda t: True)
    assert np.abs(res.w[100:]).max() <= wl              # REQ-SAFE-AA-004
