"""Model checking: REQ-SAFE-AA-001..004 (P1..P4) e o contraexemplo da versão v0."""
import pytest

from auroraarm import supervisor as sup
from auroraarm import verificacao as ver


@pytest.fixture(scope="module")
def r1():
    return ver.verificar(sup.TRANSICOES_V1, "v1")


def test_v1_satisfaz_todas_as_propriedades(r1):
    assert r1.p1_ok and r1.p2_ok and r1.p3_ok and r1.p4_ok
    assert r1.pior_latencia_parada_ms <= ver.PRAZO


def test_v1_exploracao_exaustiva_cobre_tudo(r1):
    assert r1.estados_cobertos == set(sup.ESTADOS)
    assert r1.transicoes_cobertas == {t[0] for t in sup.TRANSICOES}


def test_v0_tem_contraexemplo_de_prazo():
    r0 = ver.verificar(sup.TRANSICOES_V0, "v0")
    assert not r0.p1_ok and r0.propriedade_violada.startswith("P1")
    assert len(r0.contraexemplo) > ver.PRAZO


def test_checador_detecta_violacao_de_vivacidade():
    """Mutante: sem T9 a retomada nunca termina -> P3 deve falhar (testa o próprio checker)."""
    mut = [t for t in sup.TRANSICOES_V1 if t[0] != "T9"]
    r = ver.verificar(mut, "sem-T9")
    assert not r.p3_ok


def test_checador_detecta_religamento_sem_rearme():
    mut = [t if t[0] != "T5" else ("T5", "PARADA", {"mao": 0}, "RETOMADA", "") for t in sup.TRANSICOES_V1]
    r = ver.verificar(mut, "T5-errada")
    assert not r.p2_ok
