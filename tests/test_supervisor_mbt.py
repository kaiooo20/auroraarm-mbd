"""Testes gerados a partir do grafo do supervisor, rodando no Python E no C gerado."""
import pytest

from auroraarm import sil, supervisor as sup, testes_modelo as tm

IMPLS = {"python": sup.Supervisor, "c_gerado": sil.SupervisorC}


@pytest.mark.parametrize("nome", IMPLS)
def test_cobertura_de_transicoes(nome):
    falhas, estados, trans = tm.executar(tm.gerar_casos_transicoes(), IMPLS[nome])
    assert not falhas
    assert trans == {t[0] for t in sup.TRANSICOES} and estados == set(sup.ESTADOS)


@pytest.mark.parametrize("nome", IMPLS)
def test_todos_os_pares_estado_entrada(nome):
    falhas, _, _ = tm.executar(tm.gerar_casos_pares(), IMPLS[nome])
    assert not falhas


@pytest.mark.parametrize("nome", IMPLS)
def test_invariantes_em_passeio_aleatorio(nome):
    assert tm.passeio_propriedades(IMPLS[nome]) == []


def test_mbt_pega_o_defeito_da_v0():
    falhas, _, _ = tm.executar(tm.gerar_casos_transicoes(), lambda: sup.Supervisor(sup.TRANSICOES_V0))
    assert [f[0] for f in falhas] == ["MBT-T8"]
