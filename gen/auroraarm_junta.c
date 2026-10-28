/*
 * ===================== BLOCO DE RASTREABILIDADE =====================
 * Arquivo GERADO AUTOMATICAMENTE — não editar à mão.
 * Gerador ........: auroraarm/codegen.py v1.0.0
 * Modelo de origem : auroraarm/controlador.py (PASSOS, coeficientes)
 *                    auroraarm/supervisor.py  (TRANSICOES v1)
 * Parâmetros ......: parametros.json  sha256[:16] = 5e0f44118198114b
 * Hash do modelo ..: 1362dc10ae851da9
 * Requisitos ......: REQ-CTRL-AA-001..004, REQ-SAFE-AA-001..004
 * Verificação .....: tests/test_sil.py (equivalência numérica SIL),
 *                    tests/test_supervisor_mbt.py (testes gerados do grafo),
 *                    auroraarm/verificacao.py (model checking P1..P4)
 * Alvo ............: ARM Cortex-M4F, float IEEE-754 binário32,
 *                    laço de posição a 500 Hz (Ts = 2 ms),
 *                    compilar com -ffp-contract=off
 * ====================================================================
 */
#include "auroraarm_junta.h"

/* ---------------- coeficientes (binário32; comentário = valor do modelo em float64) */
static const float AA_KP = 10.1000004f;  /* 10.1 */
static const float AA_BETA = 0.550000012f;  /* 0.55 */
static const float AA_KI_TS = 0.25f;  /* 0.25 */
static const float AA_AD = 0.333333343f;  /* 0.3333333333333333 */
static const float AA_BD = 76.6666641f;  /* 76.66666666666667 */
static const float AA_KAW = 0.300000012f;  /* 0.3 */
static const float AA_INV_TS = 500.0f;  /* 500.0 */
static const float AA_KE = 0.0850000009f;  /* 0.085 */
static const float AA_R_ILIM = 6.0f;  /* 6.0 */
static const float AA_V_MAX = 48.0f;  /* 48.0 */
static const float AA_V_MIN = -48.0f;  /* -48.0 */
static const float AA_ZERO = 0.0f;  /* 0.0 */
static const float AA_DMAX_COLAB = 0.121428572f;  /* 0.12142857142857143 */
static const float AA_DMAX_LIVRE = 1000.0f;  /* 1000.0 */
static const float AA_AMAX_COLAB = 0.00240000011f;  /* 0.0024 */
static const float AA_AMAX_LIVRE = 1000.0f;  /* 1000.0 */

void aa_ctrl_inicializar(aa_ctrl_estado_t *s)
{
    s->integ = 0.0f;
    s->deriv = 0.0f;
    s->y_prev = 0.0f;
    s->r_prev = 0.0f;
    s->v_prev = 0.0f;
}

float aa_ctrl_passo(aa_ctrl_estado_t *s, float r_cmd, float y, float habilita, float lim_vel)
{
    const float integ = s->integ;
    const float deriv = s->deriv;
    const float y_prev = s->y_prev;
    const float r_prev = s->r_prev;
    const float v_prev = s->v_prev;
    const float dr = r_cmd - r_prev;   /* REQ-SAFE-AA-004 */
    const float dmax = (lim_vel > 0.5f) ? AA_DMAX_COLAB : AA_DMAX_LIVRE;   /* REQ-SAFE-AA-004 */
    const float dmin = AA_ZERO - dmax;   /* REQ-SAFE-AA-004 */
    const float dr1 = (dr < dmax) ? dr : dmax;   /* REQ-SAFE-AA-004 */
    const float dr2 = (dr1 > dmin) ? dr1 : dmin;   /* REQ-SAFE-AA-004 */
    const float amax = (lim_vel > 0.5f) ? AA_AMAX_COLAB : AA_AMAX_LIVRE;   /* REQ-SAFE-AA-004 */
    const float amin = AA_ZERO - amax;   /* REQ-SAFE-AA-004 */
    const float dv = dr2 - v_prev;   /* REQ-SAFE-AA-004 */
    const float dv1 = (dv < amax) ? dv : amax;   /* REQ-SAFE-AA-004 */
    const float dv2 = (dv1 > amin) ? dv1 : amin;   /* REQ-SAFE-AA-004 */
    const float v = v_prev + dv2;   /* REQ-SAFE-AA-003/004 */
    const float r = r_prev + v;   /* REQ-SAFE-AA-003/004 */
    const float e = r - y;   /* REQ-CTRL-AA-001 */
    const float dy = y - y_prev;   /* REQ-CTRL-AA-002/004 */
    const float w_hat = dy * AA_INV_TS;   /* REQ-CTRL-AA-004 */
    const float t1 = AA_AD * deriv;   /* REQ-CTRL-AA-002 */
    const float t2 = AA_BD * dy;   /* REQ-CTRL-AA-002 */
    const float d_new = t1 - t2;   /* REQ-CTRL-AA-002 */
    const float br = AA_BETA * r;   /* REQ-CTRL-AA-002 */
    const float e_p = br - y;   /* REQ-CTRL-AA-002 */
    const float p_term = AA_KP * e_p;   /* REQ-CTRL-AA-002/003 */
    const float t3 = p_term + integ;   /* REQ-CTRL-AA-001..003 */
    const float u = t3 + d_new;   /* REQ-CTRL-AA-001..003 */
    const float fcem = AA_KE * w_hat;   /* REQ-CTRL-AA-004 */
    const float v_hi0 = fcem + AA_R_ILIM;   /* REQ-CTRL-AA-004 */
    const float v_lo0 = fcem - AA_R_ILIM;   /* REQ-CTRL-AA-004 */
    const float t4 = (u < v_hi0) ? u : v_hi0;   /* REQ-CTRL-AA-004 */
    const float t4b = (t4 > v_lo0) ? t4 : v_lo0;   /* REQ-CTRL-AA-004 */
    const float t4c = (t4b < AA_V_MAX) ? t4b : AA_V_MAX;   /* REQ-CTRL-AA-004 */
    const float u_sat = (t4c > AA_V_MIN) ? t4c : AA_V_MIN;   /* REQ-CTRL-AA-004 */
    const float t5 = AA_KI_TS * e;   /* REQ-CTRL-AA-001 */
    const float t6 = u_sat - u;   /* REQ-CTRL-AA-003 (anti-windup) */
    const float t7 = AA_KAW * t6;   /* REQ-CTRL-AA-003 (anti-windup) */
    const float t8 = integ + t5;   /* REQ-CTRL-AA-001 */
    const float i_new = t8 + t7;   /* REQ-CTRL-AA-001/003 */
    const float u_out = (habilita > 0.5f) ? u_sat : AA_ZERO;   /* REQ-SAFE-AA-001/002 */
    const float integ_n = (habilita > 0.5f) ? i_new : AA_ZERO;   /* REQ-SAFE-AA-002 */
    const float deriv_n = (habilita > 0.5f) ? d_new : AA_ZERO;   /* REQ-SAFE-AA-002 */
    const float r_prev_n = (habilita > 0.5f) ? r : y;   /* REQ-SAFE-AA-003 */
    const float v_prev_n = (habilita > 0.5f) ? v : AA_ZERO;   /* REQ-SAFE-AA-003 */
    const float y_prev_n = y;   /* REQ-CTRL-AA-002/004 */
    s->integ = integ_n;
    s->deriv = deriv_n;
    s->y_prev = y_prev_n;
    s->r_prev = r_prev_n;
    s->v_prev = v_prev_n;
    return u_out;
}

void aa_sup_inicializar(aa_sup_t *sv)
{
    sv->estado = AA_SUP_REDUZIDA;
    sv->ultima_transicao = 0;
}

void aa_sup_passo(aa_sup_t *sv, int mao, int zona, int rearme, int chegou,
                  int *habilita, int *lim_vel)
{
    sv->ultima_transicao = 0;
    switch (sv->estado) {
    case AA_SUP_NORMAL:
        if ((mao == 1)) { sv->estado = AA_SUP_PARADA; sv->ultima_transicao = 1; break; }  /* T1: REQ-SAFE-AA-001 */
        if ((zona == 1)) { sv->estado = AA_SUP_REDUZIDA; sv->ultima_transicao = 2; break; }  /* T2: REQ-SAFE-AA-004 */
        break;
    case AA_SUP_REDUZIDA:
        if ((mao == 1)) { sv->estado = AA_SUP_PARADA; sv->ultima_transicao = 3; break; }  /* T3: REQ-SAFE-AA-001 */
        if ((zona == 0)) { sv->estado = AA_SUP_NORMAL; sv->ultima_transicao = 4; break; }  /* T4: REQ-SAFE-AA-004 */
        break;
    case AA_SUP_PARADA:
        if ((mao == 0)) { sv->estado = AA_SUP_AGUARDA_REARME; sv->ultima_transicao = 5; break; }  /* T5: REQ-SAFE-AA-002 */
        break;
    case AA_SUP_AGUARDA_REARME:
        if ((mao == 1)) { sv->estado = AA_SUP_PARADA; sv->ultima_transicao = 6; break; }  /* T6: REQ-SAFE-AA-001 */
        if ((rearme == 1)) { sv->estado = AA_SUP_RETOMADA; sv->ultima_transicao = 7; break; }  /* T7: REQ-SAFE-AA-002/003 */
        break;
    case AA_SUP_RETOMADA:
        if ((mao == 1)) { sv->estado = AA_SUP_PARADA; sv->ultima_transicao = 8; break; }  /* T8: REQ-SAFE-AA-001 */
        if ((chegou == 1)) { sv->estado = AA_SUP_REDUZIDA; sv->ultima_transicao = 9; break; }  /* T9: REQ-SAFE-AA-003 */
        break;
    default:   /* estado corrompido: lado seguro (REQ-SAFE-AA-001) */
        sv->estado = AA_SUP_PARADA;
        break;
    }
    switch (sv->estado) {
    case AA_SUP_NORMAL: *habilita = 1; *lim_vel = 0; break;
    case AA_SUP_REDUZIDA: *habilita = 1; *lim_vel = 1; break;
    case AA_SUP_PARADA: *habilita = 0; *lim_vel = 1; break;
    case AA_SUP_AGUARDA_REARME: *habilita = 0; *lim_vel = 1; break;
    case AA_SUP_RETOMADA: *habilita = 1; *lim_vel = 1; break;
    default: *habilita = 0; *lim_vel = 1; break;
    }
}
