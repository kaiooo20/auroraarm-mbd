"""O código C versionado é exatamente o que o gerador produz a partir do modelo atual."""
import shutil
import subprocess
from pathlib import Path

import pytest

from auroraarm import codegen

RAIZ = Path(__file__).resolve().parent.parent


def test_codigo_versionado_esta_sincronizado_com_o_modelo(tmp_path, p):
    codegen.gerar(p, tmp_path)
    for nome in ("auroraarm_junta.h", "auroraarm_junta.c"):
        assert (tmp_path / nome).read_text() == (RAIZ / "gen" / nome).read_text(), \
            f"gen/{nome} desatualizado: rode python -m auroraarm.codegen"


def test_bloco_de_rastreabilidade(p):
    c = (RAIZ / "gen" / "auroraarm_junta.c").read_text()
    assert "BLOCO DE RASTREABILIDADE" in c and codegen.hash_modelo(
        __import__("auroraarm.controlador", fromlist=["x"]).coeficientes(p)) in c
    for req in ("REQ-CTRL-AA-004", "REQ-SAFE-AA-001", "REQ-SAFE-AA-004"):
        assert req in c


@pytest.mark.skipif(shutil.which("arm-none-eabi-gcc") is None, reason="sem toolchain ARM")
def test_compila_para_cortex_m4_e_cabe_na_memoria(tmp_path, p):
    obj = tmp_path / "m4.o"
    subprocess.run(["arm-none-eabi-gcc", "-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard",
                    "-mfpu=fpv4-sp-d16", "-O2", "-ffp-contract=off", "-std=c99", "-Wall",
                    "-Werror", "-c", str(RAIZ / "gen/auroraarm_junta.c"), "-o", str(obj)], check=True)
    out = subprocess.run(["arm-none-eabi-size", str(obj)], capture_output=True, text=True).stdout
    assert int(out.splitlines()[1].split()[0]) < p.memoria_programa_bytes
