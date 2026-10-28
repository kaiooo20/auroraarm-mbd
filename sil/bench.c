/* Medida de tempo de execução do código gerado (host x86-64, apenas ordem de grandeza).
 * O orçamento real (200 us no Cortex-M4) é verificado pela contagem de instruções do
 * binário ARM em scripts/memorial.py. Uso: gcc -O2 -ffp-contract=off sil/bench.c gen/auroraarm_junta.c */
#include <stdio.h>
#include <time.h>
#include "../gen/auroraarm_junta.h"

int main(void)
{
    aa_ctrl_estado_t s;
    aa_sup_t sv;
    int h, l;
    volatile float acc = 0.0f;
    const long N = 5000000L;
    struct timespec t0, t1;
    aa_ctrl_inicializar(&s);
    aa_sup_inicializar(&sv);
    clock_gettime(CLOCK_MONOTONIC, &t0);
    for (long k = 0; k < N; ++k) {
        float y = (float)(k % 1000) * 0.01f;
        aa_sup_passo(&sv, (int)(k % 97 == 0), (int)(k % 5 == 0), (int)(k % 13 == 0), 1, &h, &l);
        acc += aa_ctrl_passo(&s, 10.0f, y, (float)h, (float)l);
    }
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double ns = ((t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec)) / (double)N;
    printf("%.2f\n", ns);
    return acc > 1e30f;
}
