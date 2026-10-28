"""Gerador automático de código C (Unidade 4).

Entrada: o MODELO validado — coeficientes do controlador (`controlador.coeficientes`),
a lista de passos do controlador (`controlador.PASSOS`) e a tabela de transições do
supervisor (`supervisor.TRANSICOES`). Saída: `gen/auroraarm_junta.h` e `gen/auroraarm_junta.c`.

Regras da geração (pensadas para o Cortex-M4F e para a equivalência bit a bit):
  * tipo único `float` (IEEE-754 binário32, a FPU do M4 é de precisão simples);
  * uma operação por linha, na MESMA ordem do modelo (sem reassociação);
  * constantes impressas com 9 dígitos significativos (ida e volta exata em binário32);
  * sem alocação dinâmica, sem laços, sem recursão (tempo de execução constante);
  * compilar com -ffp-contract=off (proíbe FMA, que mudaria o arredondamento).

O bloco de rastreabilidade do cabeçalho registra o hash dos artefatos de origem; o teste
`tests/test_codegen.py` regenera o código e falha se o arquivo versionado divergir.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import controlador as ctl
from . import supervisor as sup
from .parametros import ARQUIVO_PADRAO, Parametros, RAIZ, hash_arquivo

VERSAO_GERADOR = "1.0.0"
DIR_SAIDA = RAIZ / "gen"

# Requisito associado a cada passo do controlador (vai como comentário no C)
REQ_POR_PASSO = {
    "dr": "REQ-SAFE-AA-004", "dmax": "REQ-SAFE-AA-004", "dmin": "REQ-SAFE-AA-004",
    "dr1": "REQ-SAFE-AA-004", "dr2": "REQ-SAFE-AA-004", "r": "REQ-SAFE-AA-003/004",
    "amax": "REQ-SAFE-AA-004", "amin": "REQ-SAFE-AA-004", "dv": "REQ-SAFE-AA-004",
    "dv1": "REQ-SAFE-AA-004", "dv2": "REQ-SAFE-AA-004", "v": "REQ-SAFE-AA-003/004",
    "v_prev": "REQ-SAFE-AA-003",
    "e": "REQ-CTRL-AA-001", "t5": "REQ-CTRL-AA-001", "t8": "REQ-CTRL-AA-001",
    "br": "REQ-CTRL-AA-002", "e_p": "REQ-CTRL-AA-002", "p_term": "REQ-CTRL-AA-002/003",
    "t1": "REQ-CTRL-AA-002", "t2": "REQ-CTRL-AA-002", "d_new": "REQ-CTRL-AA-002",
    "fcem": "REQ-CTRL-AA-004", "v_hi0": "REQ-CTRL-AA-004", "v_lo0": "REQ-CTRL-AA-004",
    "t4": "REQ-CTRL-AA-004", "t4b": "REQ-CTRL-AA-004", "t4c": "REQ-CTRL-AA-004",
    "u_sat": "REQ-CTRL-AA-004", "t6": "REQ-CTRL-AA-003 (anti-windup)",
    "t7": "REQ-CTRL-AA-003 (anti-windup)", "i_new": "REQ-CTRL-AA-001/003",
    "u_out": "REQ-SAFE-AA-001/002", "integ": "REQ-SAFE-AA-002", "deriv": "REQ-SAFE-AA-002",
    "r_prev": "REQ-SAFE-AA-003",
    "dy": "REQ-CTRL-AA-002/004", "w_hat": "REQ-CTRL-AA-004", "t3": "REQ-CTRL-AA-001..003",
    "u": "REQ-CTRL-AA-001..003", "y_prev": "REQ-CTRL-AA-002/004",
}


def f32(x: float) -> str:
    """Literal C float que reproduz exatamente o valor binário32 de x."""
    v = np.float32(x)
    s = f"{float(v):.9g}"
    if "e" not in s and "." not in s:
        s += ".0"
    return s + "f"


def hash_modelo(coef: dict) -> str:
    conteudo = json.dumps({"coef": coef, "passos": ctl.PASSOS,
                           "transicoes": [t[:4] for t in sup.TRANSICOES]},
                          sort_keys=True, default=str)
    return hashlib.sha256(conteudo.encode()).hexdigest()[:16]


def _expr(op, a):
    if op == "add":
        return f"{a[0]} + {a[1]}"
    if op == "sub":
        return f"{a[0]} - {a[1]}"
    if op == "mul":
        return f"{a[0]} * {a[1]}"
    if op == "min":
        return f"({a[0]} < {a[1]}) ? {a[0]} : {a[1]}"
    if op == "max":
        return f"({a[0]} > {a[1]}) ? {a[0]} : {a[1]}"
    if op == "sel":
        return f"({a[0]} > 0.5f) ? {a[1]} : {a[2]}"
    if op == "mov":
        return a[0]
    raise ValueError(op)


def _nome(n, coef):
    if n in coef:
        return f"AA_{n}"
    if n in ctl.ESTADOS:
        return f"s->{n}"
    return n


def gerar(p: Parametros | None = None, saida: Path = DIR_SAIDA) -> dict:
    p = p or Parametros.carregar()
    coef = ctl.coeficientes(p)
    h_par = hash_arquivo(ARQUIVO_PADRAO)
    h_mod = hash_modelo(coef)
    trace = f"""/*
 * ===================== BLOCO DE RASTREABILIDADE =====================
 * Arquivo GERADO AUTOMATICAMENTE — não editar à mão.
 * Gerador ........: auroraarm/codegen.py v{VERSAO_GERADOR}
 * Modelo de origem : auroraarm/controlador.py (PASSOS, coeficientes)
 *                    auroraarm/supervisor.py  (TRANSICOES v1)
 * Parâmetros ......: parametros.json  sha256[:16] = {h_par}
 * Hash do modelo ..: {h_mod}
 * Requisitos ......: REQ-CTRL-AA-001..004, REQ-SAFE-AA-001..004
 * Verificação .....: tests/test_sil.py (equivalência numérica SIL),
 *                    tests/test_supervisor_mbt.py (testes gerados do grafo),
 *                    auroraarm/verificacao.py (model checking P1..P4)
 * Alvo ............: ARM Cortex-M4F, float IEEE-754 binário32,
 *                    laço de posição a {1/p.Ts:.0f} Hz (Ts = {p.Ts*1e3:.0f} ms),
 *                    compilar com -ffp-contract=off
 * ====================================================================
 */"""
    # ------------------------------------------------------------ cabeçalho .h
    campos = "\n".join(f"    float {e};" for e in ctl.ESTADOS)
    estados_enum = ",\n".join(f"    AA_SUP_{e} = {i}" for i, e in enumerate(sup.ESTADOS))
    h = f"""{trace}
#ifndef AURORAARM_JUNTA_H
#define AURORAARM_JUNTA_H

#ifdef __cplusplus
extern "C" {{
#endif

#define AA_MODELO_HASH "{h_mod}"

/* Estado interno do controlador PID (persistente entre ciclos) */
typedef struct {{
{campos}
}} aa_ctrl_estado_t;

/* Estados do supervisor de segurança (REQ-SAFE-AA-001..004) */
typedef enum {{
{estados_enum}
}} aa_sup_estado_t;

typedef struct {{
    aa_sup_estado_t estado;
    int ultima_transicao;   /* número da última transição disparada (0 = nenhuma) */
}} aa_sup_t;

void  aa_ctrl_inicializar(aa_ctrl_estado_t *s);
/* Um ciclo do laço de posição. Retorna a tensão de comando [V].
 * r_cmd, y em rad no eixo do motor; habilita e lim_vel valem 0.0f ou 1.0f. */
float aa_ctrl_passo(aa_ctrl_estado_t *s, float r_cmd, float y, float habilita, float lim_vel);

void  aa_sup_inicializar(aa_sup_t *sv);
/* Um ciclo do supervisor. Entradas 0/1. Escreve habilita e lim_vel (0/1). */
void  aa_sup_passo(aa_sup_t *sv, int mao, int zona, int rearme, int chegou,
                   int *habilita, int *lim_vel);

#ifdef __cplusplus
}}
#endif
#endif /* AURORAARM_JUNTA_H */
"""
    # ------------------------------------------------------------ fonte .c
    consts = "\n".join(f"static const float AA_{k} = {f32(v)};  /* {v!r} */"
                       for k, v in coef.items())
    inits = "\n".join(f"    s->{e} = 0.0f;" for e in ctl.ESTADOS)
    corpo = []
    for dest, op, *a in ctl.PASSOS:
        args = [_nome(x, coef) for x in a]
        req = REQ_POR_PASSO.get(dest, "")
        if dest in ctl.ESTADOS:
            corpo.append(f"    const float {dest}_n = {_expr(op, args)};   /* {req} */")
        else:
            corpo.append(f"    const float {dest} = {_expr(op, args)};   /* {req} */")
    commit = "\n".join(f"    s->{e} = {e}_n;" for e in ctl.ESTADOS)
    # Os estados lidos depois de atualizados no modelo? Não: no modelo os estados só são
    # escritos nos últimos passos e não são relidos — a escrita adiada é equivalente.
    sup_cases = []
    for est in sup.ESTADOS:
        linhas = []
        for tid, origem, guarda, destino, req in sup.TRANSICOES:
            if origem != est:
                continue
            cond = " && ".join(f"({k} == {v})" for k, v in guarda.items())
            linhas.append(f"        if ({cond}) {{ sv->estado = AA_SUP_{destino}; "
                          f"sv->ultima_transicao = {int(tid[1:])}; break; }}  /* {tid}: {req} */")
        corpo_case = "\n".join(linhas) if linhas else ""
        sup_cases.append(f"    case AA_SUP_{est}:\n{corpo_case}\n        break;")
    saidas = "\n".join(
        f"    case AA_SUP_{e}: *habilita = {hb}; *lim_vel = {lv}; break;"
        for e, (hb, lv) in sup.SAIDAS.items())
    c = f"""{trace}
#include "auroraarm_junta.h"

/* ---------------- coeficientes (binário32; comentário = valor do modelo em float64) */
{consts}

void aa_ctrl_inicializar(aa_ctrl_estado_t *s)
{{
{inits}
}}

float aa_ctrl_passo(aa_ctrl_estado_t *s, float r_cmd, float y, float habilita, float lim_vel)
{{
    const float integ = s->integ;
    const float deriv = s->deriv;
    const float y_prev = s->y_prev;
    const float r_prev = s->r_prev;
    const float v_prev = s->v_prev;
{chr(10).join(corpo).replace("s->integ", "integ").replace("s->deriv", "deriv").replace("s->y_prev", "y_prev").replace("s->r_prev", "r_prev").replace("s->v_prev", "v_prev")}
{commit}
    return u_out;
}}

void aa_sup_inicializar(aa_sup_t *sv)
{{
    sv->estado = AA_SUP_{sup.ESTADO_INICIAL};
    sv->ultima_transicao = 0;
}}

void aa_sup_passo(aa_sup_t *sv, int mao, int zona, int rearme, int chegou,
                  int *habilita, int *lim_vel)
{{
    sv->ultima_transicao = 0;
    switch (sv->estado) {{
{chr(10).join(sup_cases)}
    default:   /* estado corrompido: lado seguro (REQ-SAFE-AA-001) */
        sv->estado = AA_SUP_PARADA;
        break;
    }}
    switch (sv->estado) {{
{saidas}
    default: *habilita = 0; *lim_vel = 1; break;
    }}
}}
"""
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "auroraarm_junta.h").write_text(h, encoding="utf-8")
    (saida / "auroraarm_junta.c").write_text(c, encoding="utf-8")
    return {"hash_parametros": h_par, "hash_modelo": h_mod,
            "arquivos": ["gen/auroraarm_junta.h", "gen/auroraarm_junta.c"]}


if __name__ == "__main__":
    print(gerar())
