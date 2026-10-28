# AuroraArm — Operação Linha Viva

Pacote de design baseado em modelos da **junta do cotovelo do braço colaborativo AuroraArm**:
modelo da planta, controlador, verificação formal do supervisor de segurança, código C
gerado a partir do modelo e matriz de rastreabilidade.

Trabalho da disciplina *Model Based Design for Cyber-Physical Systems* — UNIFECAF,
Engenharia da Computação. Autor: Kaio Santana Rodrigues Santos (RA 98328).

O relatório completo (parte teórica, parte prática e memorial de cálculo) está em
[`relatorio/AuroraArm_relatorio_tecnico.pdf`](relatorio/AuroraArm_relatorio_tecnico.pdf).

## Resultados principais

| Requisito | Exigido | Obtido |
|---|---|---|
| REQ-CTRL-AA-001 | erro em regime nulo | 1,2·10⁻⁴ rad (pior caso) |
| REQ-CTRL-AA-002 | sobressinal ≤ 8 % | 2,81 % (pior caso, 9 cenários) |
| REQ-CTRL-AA-003 | acomodação ≤ 300 ms | 218 ms (pior caso) |
| REQ-CTRL-AA-004 | \|V\| ≤ 48 V, \|i\| ≤ 8 A | \|i\| ≤ 7,33 A; \|V\| ≤ 48 V por construção |
| REQ-SAFE-AA-001 | torque zero ≤ 100 ms | 31,96 ms no pior caso (model checking + 64 320 combinações) |
| REQ-SAFE-AA-002 | religar só com rearme | verificado (P2) |
| REQ-SAFE-AA-003 | retomar a trajetória | verificado (vivacidade, P3) |
| REQ-SAFE-AA-004 | ≤ 250 mm/s na zona | 212 mm/s em regime; abaixo do limite em 666 ms |

- Modelo: τe = 1,55 ms, τm = 44,2 ms; ponto crítico exige 3,74 A e 41,24 V (folga de 6,76 V).
- O model checker encontrou um **contraexemplo real** na versão preliminar do supervisor
  (falta da transição RETOMADA → PARADA), corrigido na v1 — ver `resultados/contraexemplo_v0.txt`.
- Código C gerado: **bit a bit idêntico** ao modelo em float32; 692 bytes no Cortex-M4F;
  cota de 3,9 µs por ciclo (orçamento: 200 µs).

## Como rodar

```bash
pip install -r requirements.txt
python -m pytest                    # 42 testes (requisitos, MBT, SIL, model checking, codegen)
python scripts/memorial.py          # memorial de cálculo (a)..(e) + model checking
python scripts/figuras.py           # figuras em resultados/figuras/
python scripts/rastreabilidade.py   # docs/rastreabilidade.md
python relatorio/gerar_pdf.py       # relatório em PDF
python -m auroraarm.codegen         # regenera gen/auroraarm_junta.{h,c} a partir do modelo
```

Precisa de Python 3.10+ e de um compilador C (`gcc`) para o SIL. O `arm-none-eabi-gcc`
é opcional (medida de memória e de instruções no Cortex-M4).

## Estrutura

```
parametros.json            dados do enunciado (fonte única)
auroraarm/
  planta.py                espaço de estados, discretização ZOH, simulação
  identificacao.py         ensaio emulado, mínimos quadrados em duas etapas, validação cruzada
  controlador.py           PID 2-GDL + saturação + anti-windup (modelo executável PASSOS)
  supervisor.py            máquina de estados de segurança (v0 com defeito, v1 corrigida)
  verificacao.py           model checker explícito: P1..P4, contraexemplos
  testes_modelo.py         testes gerados a partir do grafo do supervisor
  codegen.py               gerador de C a partir do modelo
  sil.py                   software-in-the-loop (C via ctypes) e equivalência numérica
gen/                       código C GERADO — não editar à mão
sil/bench.c                medida de tempo no host
scripts/                   sintonia, memorial, figuras, rastreabilidade
tests/                     suíte pytest
resultados/                memorial.json/.txt, contraexemplo, figuras
docs/passo-a-passo.md      guia de estudo do projeto, do básico ao avançado
docs/rastreabilidade.md    matriz requisito → modelo → código → teste
relatorio/                 gerador e PDF do relatório
```
