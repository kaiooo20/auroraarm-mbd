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
#ifndef AURORAARM_JUNTA_H
#define AURORAARM_JUNTA_H

#ifdef __cplusplus
extern "C" {
#endif

#define AA_MODELO_HASH "1362dc10ae851da9"

/* Estado interno do controlador PID (persistente entre ciclos) */
typedef struct {
    float integ;
    float deriv;
    float y_prev;
    float r_prev;
    float v_prev;
} aa_ctrl_estado_t;

/* Estados do supervisor de segurança (REQ-SAFE-AA-001..004) */
typedef enum {
    AA_SUP_NORMAL = 0,
    AA_SUP_REDUZIDA = 1,
    AA_SUP_PARADA = 2,
    AA_SUP_AGUARDA_REARME = 3,
    AA_SUP_RETOMADA = 4
} aa_sup_estado_t;

typedef struct {
    aa_sup_estado_t estado;
    int ultima_transicao;   /* número da última transição disparada (0 = nenhuma) */
} aa_sup_t;

void  aa_ctrl_inicializar(aa_ctrl_estado_t *s);
/* Um ciclo do laço de posição. Retorna a tensão de comando [V].
 * r_cmd, y em rad no eixo do motor; habilita e lim_vel valem 0.0f ou 1.0f. */
float aa_ctrl_passo(aa_ctrl_estado_t *s, float r_cmd, float y, float habilita, float lim_vel);

void  aa_sup_inicializar(aa_sup_t *sv);
/* Um ciclo do supervisor. Entradas 0/1. Escreve habilita e lim_vel (0/1). */
void  aa_sup_passo(aa_sup_t *sv, int mao, int zona, int rearme, int chegou,
                   int *habilita, int *lim_vel);

#ifdef __cplusplus
}
#endif
#endif /* AURORAARM_JUNTA_H */
