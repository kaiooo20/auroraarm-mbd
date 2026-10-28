"""Software-in-the-loop: o código C GERADO roda no lugar do modelo (Unidade 4).

`compilar()` gera uma biblioteca compartilhada a partir de gen/auroraarm_junta.c e
`ControladorC` / `SupervisorC` a expõem via ctypes com a mesma interface das classes de
referência em Python. Assim os mesmos cenários rodam com o modelo e com o código.
"""
from __future__ import annotations

import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from . import controlador as ctl
from . import supervisor as sup
from .parametros import Parametros, RAIZ

FONTE = RAIZ / "gen" / "auroraarm_junta.c"
FLAGS = ["-std=c99", "-O2", "-ffp-contract=off", "-fno-fast-math", "-fPIC", "-shared",
         "-Wall", "-Wextra", "-Werror"]


class _CtrlEstado(ctypes.Structure):
    _fields_ = [(n, ctypes.c_float) for n in ctl.ESTADOS]


class _Sup(ctypes.Structure):
    _fields_ = [("estado", ctypes.c_int), ("ultima_transicao", ctypes.c_int)]


_lib_cache = {}


def compilar(fonte: Path = FONTE):
    """Compila o C gerado como .so (cacheado por processo)."""
    chave = (str(fonte), fonte.stat().st_mtime)
    if chave in _lib_cache:
        return _lib_cache[chave]
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        raise RuntimeError("compilador C não encontrado (instale gcc)")
    destino = Path(tempfile.mkdtemp(prefix="aa_sil_")) / "libauroraarm.so"
    subprocess.run([cc, *FLAGS, str(fonte), "-o", str(destino)], check=True)
    lib = ctypes.CDLL(str(destino))
    lib.aa_ctrl_passo.restype = ctypes.c_float
    lib.aa_ctrl_passo.argtypes = [ctypes.POINTER(_CtrlEstado)] + [ctypes.c_float] * 4
    lib.aa_ctrl_inicializar.argtypes = [ctypes.POINTER(_CtrlEstado)]
    lib.aa_sup_inicializar.argtypes = [ctypes.POINTER(_Sup)]
    lib.aa_sup_passo.argtypes = [ctypes.POINTER(_Sup)] + [ctypes.c_int] * 4 + \
        [ctypes.POINTER(ctypes.c_int)] * 2
    _lib_cache[chave] = lib
    return lib


class ControladorC:
    """Mesma interface de `ControladorReferencia`, executando o código C gerado."""

    def __init__(self, lib=None):
        self.lib = lib or compilar()
        self._s = _CtrlEstado()
        self.reset()

    def reset(self):
        self.lib.aa_ctrl_inicializar(ctypes.byref(self._s))

    @property
    def estado(self):
        return {n: getattr(self._s, n) for n in ctl.ESTADOS}

    def passo(self, r_cmd, y, habilita=True, lim_vel=False):
        return self.lib.aa_ctrl_passo(ctypes.byref(self._s), float(r_cmd), float(y),
                                      1.0 if habilita else 0.0, 1.0 if lim_vel else 0.0)


class SupervisorC:
    def __init__(self, lib=None):
        self.lib = lib or compilar()
        self._s = _Sup()
        self.reset()

    def reset(self):
        self.lib.aa_sup_inicializar(ctypes.byref(self._s))

    @property
    def estado(self):
        return sup.ESTADOS[self._s.estado]

    def passo(self, mao=0, zona=0, rearme=0, chegou=0):
        h, l = ctypes.c_int(), ctypes.c_int()
        self.lib.aa_sup_passo(ctypes.byref(self._s), int(mao), int(zona), int(rearme),
                              int(chegou), ctypes.byref(h), ctypes.byref(l))
        t = self._s.ultima_transicao
        return h.value, l.value, (f"T{t}" if t else None)


# ----------------------------------------------------------------- sequência de teste
def sequencia_teste(p: Parametros, n_aleat=3000, semente=7):
    """Sequência de entradas (r_cmd, y, habilita, lim_vel) para o teste de equivalência.

    Parte 1: entradas registradas de um ensaio em malha fechada (degraus, parada de
    segurança, modo colaborativo) — cobre a operação real e os ramos de saturação.
    Parte 2: entradas aleatórias em toda a faixa física — cobre combinações raras.
    """
    rng = np.random.default_rng(semente)
    coef = ctl.coeficientes(p)

    def ref(t):
        return 0.0 if t < 0.05 else (10.0 if t < 0.6 else (-10.0 if t < 1.1 else 40.0))

    def hab(t):
        return not (0.8 <= t < 0.9)

    def lim(t):
        return t >= 1.1

    res = ctl.simular_malha_fechada(p, coef, ref, t_final=1.6, habilita=hab, lim_vel=lim)
    seq = [(ref(t), y, hab(t), lim(t)) for t, y in zip(res.t, res.theta)]
    for _ in range(n_aleat):
        seq.append((rng.uniform(-60, 60), rng.uniform(-60, 60),
                    rng.random() > 0.1, rng.random() > 0.5))
    return seq


def equivalencia(p: Parametros | None = None):
    """Erro máximo absoluto entre modelo e código C ao longo da sequência de teste."""
    p = p or Parametros.carregar()
    coef = ctl.coeficientes(p)
    seq = sequencia_teste(p)
    c = ControladorC()
    m32 = ctl.ControladorReferencia(coef, np.float32)
    m64 = ctl.ControladorReferencia(coef, np.float64)
    uc, u32, u64 = [], [], []
    for r, y, h, l in seq:
        uc.append(c.passo(r, y, h, l))
        u32.append(float(m32.passo(r, y, h, l)))
        u64.append(float(m64.passo(r, y, h, l)))
    uc, u32, u64 = map(np.array, (uc, u32, u64))
    eps = float(np.finfo(np.float32).eps)
    escala = float(np.abs(u64).max())
    err32 = float(np.abs(uc - u32).max())
    err64 = float(np.abs(uc - u64).max())
    return {
        "n_amostras": len(seq),
        "erro_max_vs_modelo_float32_V": err32,
        "erro_max_vs_modelo_float64_V": err64,
        "bits_iguais_vs_float32": bool(np.array_equal(uc.astype(np.float32).view(np.uint32),
                                                     u32.astype(np.float32).view(np.uint32))),
        "eps_float32": eps,
        "escala_saida_V": escala,
        "erro_rel_vs_float64_em_eps": err64 / (escala * eps),
        "_series": (uc, u32, u64),
    }
