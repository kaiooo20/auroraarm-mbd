"""Identificação e validação (Unidade 1)."""
from auroraarm import identificacao as idf


def test_parametros_recuperados_com_erro_pequeno(p):
    r = idf.rodar(p)
    for k, e in r["erro_pct"].items():
        assert abs(e) < 2.0, f"{k}: erro {e:.2f} %"


def test_validacao_cruzada(p):
    r = idf.rodar(p)
    assert r["fit_w_pct"] > 95 and r["fit_i_pct"] > 95
