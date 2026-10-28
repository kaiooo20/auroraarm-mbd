"""Equivalência numérica modelo x código C gerado (software-in-the-loop) — item (e)."""
import numpy as np

from auroraarm import controlador as ctl, sil


def test_c_bit_a_bit_igual_ao_modelo_float32(p):
    r = sil.equivalencia(p)
    assert r["bits_iguais_vs_float32"] and r["erro_max_vs_modelo_float32_V"] == 0.0


def test_erro_vs_float64_dentro_da_cota_de_arredondamento(p):
    r = sil.equivalencia(p)
    coef = ctl.coeficientes(p)
    cota = (coef["BD"] + coef["KP"]) * 60.0 * np.finfo(np.float32).eps
    assert r["erro_max_vs_modelo_float64_V"] <= cota
    assert r["erro_max_vs_modelo_float64_V"] < 2 * p.V_max / 4096   # < 1 LSB de PWM 12 bits


def test_malha_fechada_com_codigo_c(p):
    m_c, _ = ctl.ensaio_degrau(p, 10.0, controlador=sil.ControladorC())
    m_m, _ = ctl.ensaio_degrau(p, 10.0)
    assert m_c["sobressinal_pct"] <= 8 and m_c["t_acomodacao_s"] <= 0.3
    assert abs(m_c["t_acomodacao_s"] - m_m["t_acomodacao_s"]) <= p.Ts
