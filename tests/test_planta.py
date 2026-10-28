"""Modelo da planta — memorial itens (a), (b), (c)."""
import numpy as np

from auroraarm import planta as pl


def test_matrizes_a_partir_dos_parametros(p):
    A, B, E, C, _ = pl.matrizes(p)
    assert np.allclose(A, [[-p.R / p.L, -p.Ke / p.L], [p.Kt / p.J, -p.b / p.J]])
    assert np.allclose(B.ravel(), [1 / p.L, 0]) and np.allclose(E.ravel(), [0, -1 / p.J])
    assert np.allclose(C, [[0, 1]])


def test_autovalores_e_constantes_de_tempo(p):
    lam = pl.autovalores(p)
    assert np.allclose(lam, [-644.409, -22.615], atol=1e-2)
    te, tm = pl.constantes_de_tempo(p)
    assert abs(te * 1e3 - 1.5518) < 1e-3 and abs(tm * 1e3 - 44.218) < 1e-2
    assert tm / te > 20                      # separação de escalas de tempo


def test_controlavel_e_observavel(p):
    A, B, _, C, _ = pl.matrizes(p)
    assert np.linalg.matrix_rank(pl.matriz_controlabilidade(A, B)) == 2
    assert np.linalg.matrix_rank(pl.matriz_observabilidade(A, C)) == 2


def test_ponto_de_operacao(p):
    i, V = pl.ponto_de_operacao(p)
    assert abs(i - 3.7353) < 1e-3 and abs(V - 41.238) < 1e-3
    assert V < p.V_max and i < p.i_max


def test_regime_da_simulacao_bate_com_o_balanco(p):
    i_ss, V_ss = pl.ponto_de_operacao(p)
    t, i, w = pl.simular_malha_aberta(p, lambda t: V_ss, lambda t: p.T_carga, 0.5)
    assert abs(w[-1] - p.w_op) < 0.05 and abs(i[-1] - i_ss) < 1e-3


def test_amostragem(p):
    _, tm = pl.constantes_de_tempo(p)
    assert 10 <= tm / p.Ts <= 30


def test_discretizacao_zoh_bate_com_expm(p):
    A, B, *_ = pl.matrizes(p)
    Ad, Bd = pl.discretizar_zoh(A, B, p.Ts)
    # ganho estático preservado: (I-Ad)^-1 Bd == -A^-1 B
    assert np.allclose(np.linalg.solve(np.eye(2) - Ad, Bd), -np.linalg.solve(A, B), rtol=1e-9)
