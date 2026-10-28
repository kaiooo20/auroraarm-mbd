# Passo a passo: entendendo o projeto AuroraArm

Guia de estudo do repositório, do básico ao avançado. Cada etapa diz **o que estudar**,
**onde está no código**, **o que rodar** e um **exercício**. Faça na ordem: cada etapa usa
a anterior.

---

## Nível 1 — Python para engenharia (base)

### Etapa 1 · Um arquivo de dados como fonte única
- **Ideia:** todos os números do enunciado ficam em `parametros.json`. Nenhum script
  repete `0.8` ou `48` à mão: se um dado mudar, muda em um lugar só.
- **Código:** `auroraarm/parametros.py`. Repare em `@dataclass(frozen=True)`: cria uma
  classe só com atributos, e `frozen` impede alterar um parâmetro sem querer.
- **Rode:** `python -c "from auroraarm.parametros import Parametros; print(Parametros.carregar())"`
- **Exercício:** mude `T_carga` para `0.30` no JSON, rode `python scripts/memorial.py` e veja
  o item (b) mudar. Depois volte para `0.25`.

### Etapa 2 · NumPy: matrizes e autovalores
- **Ideia:** o modelo é `dx/dt = A x + B u`. Em Python, `A` é um `np.array` 2x2.
- **Código:** `auroraarm/planta.py::matrizes`, `autovalores`, `constantes_de_tempo`.
- **Conceitos de Python:** `np.array`, `@` (produto de matrizes), `np.linalg.eigvals`,
  `np.linalg.matrix_rank`.
- **Exercício:** calcule à mão (memorial, item a) o traço e o determinante de A e confira
  com `np.trace(A)` e `np.linalg.det(A)`.

### Etapa 3 · Testes com pytest
- **Ideia:** um teste é uma função que começa com `test_` e usa `assert`. Se a conta mudar
  sem querer, o teste avisa.
- **Código:** `tests/test_planta.py` (o mais simples) e `tests/conftest.py` (o *fixture* `p`
  é criado uma vez e entregue a todos os testes).
- **Rode:** `python -m pytest tests/test_planta.py -v`
- **Exercício:** escreva um teste que confira `V_ss < V_max` para `w = 500 rad/s`.

---

## Nível 2 — Simulação e controle

### Etapa 4 · Discretização e simulação
- **Ideia:** o computador trabalha em passos. Com tensão constante durante o passo (ZOH), a
  solução exata é `x[k+1] = Ad x[k] + Bd u[k]`, com `Ad = expm(A·h)`.
- **Código:** `planta.py::discretizar_zoh` e a classe `SimuladorJunta`.
- **Exercício:** troque `sub=20` por `sub=2` em `SimuladorJunta` e compare o pico de
  corrente. Por que ele muda? (Dica: τe ≈ 1,5 ms e Ts = 2 ms.)

### Etapa 5 · Identificação (de dados para modelo)
- **Ideia:** mínimos quadrados (`np.linalg.lstsq`) acham os parâmetros que melhor explicam
  os dados. Validar é testar o modelo em dados que ele **não** viu.
- **Código:** `auroraarm/identificacao.py`. Leia a docstring: ela conta o erro da primeira
  versão (atrito 119 % errado) e por que a forma integral resolve.
- **Exercício:** aumente `ruido_w` para `5.0` e veja quanto o erro de `b` cresce.

### Etapa 6 · O PID como lista de passos
- **Ideia:** o controlador é uma lista de operações (`PASSOS`). Um "intérprete" executa a
  lista; o gerador de código traduz a mesma lista para C.
- **Código:** `auroraarm/controlador.py`. Leia os comentários de cada bloco: limitador de
  referência, PID, saturação, anti-windup, habilita.
- **Rode:** `python scripts/sintonia.py 40` (otimização curta)
- **Exercício:** rode `ensaio_degrau(p, 10.0, coef=coeficientes(p, {"Kaw": 0}))` e veja o
  windup acontecer (sobressinal > 90 %).

---

## Nível 3 — Verificação formal

### Etapa 7 · Máquina de estados como dados
- **Ideia:** o supervisor é uma tabela `(id, origem, guarda, destino, requisito)`. A
  primeira transição verdadeira vence.
- **Código:** `auroraarm/supervisor.py`. Compare `TRANSICOES_V0` e `TRANSICOES_V1`.
- **Exercício:** desenhe no papel o grafo (ou veja `resultados/figuras/fig0_supervisor.png`)
  e encontre o caminho que leva a v0 ao erro.

### Etapa 8 · Model checking explícito
- **Ideia:** gerar **todos** os estados possíveis (busca em largura com `collections.deque`)
  e checar a propriedade em cada um. Prazos viram relógios (`co`, `cz`); vivacidade vira
  "não pode existir ciclo com obrigação pendente".
- **Código:** `auroraarm/verificacao.py::sucessores` (as escolhas não determinísticas são os
  `for` aninhados) e `verificar`.
- **Rode:** `python -c "from auroraarm import verificacao as v, supervisor as s; r=v.verificar(s.TRANSICOES_V0); print(v.formatar_contraexemplo(r))"`
- **Exercício:** mude `K_RET` para `5` e rode de novo com a v0. O defeito some. Explique por
  quê (está no relatório, seção 8.4).

### Etapa 9 · Testes gerados do modelo
- **Ideia:** em vez de inventar testes, gerar a partir do grafo: um caso por transição, todos
  os pares estado × entrada, e passeios aleatórios com invariantes.
- **Código:** `auroraarm/testes_modelo.py`, `tests/test_supervisor_mbt.py`.

---

## Nível 4 — Código embarcado e certificação

### Etapa 10 · Geração de código C
- **Ideia:** `codegen.py` lê `PASSOS` e a tabela do supervisor e escreve o C. Uma operação
  por linha, mesma ordem, `float` de 32 bits, sem laços.
- **Rode:** `python -m auroraarm.codegen` e abra `gen/auroraarm_junta.c`.
- **Exercício:** mude `Kp` em `GANHOS_PADRAO`, regenere e veja o hash do bloco de
  rastreabilidade mudar. Rode `pytest tests/test_codegen.py`: ele falha se você esquecer de
  regenerar.

### Etapa 11 · Software-in-the-loop (SIL)
- **Ideia:** compilar o C como biblioteca e chamá-lo do Python com `ctypes`. As mesmas
  entradas vão para o modelo e para o código; as saídas são comparadas bit a bit.
- **Código:** `auroraarm/sil.py`.
- **Exercício:** compile com `-O3 -ffast-math` em vez de `-ffp-contract=off` (lista `FLAGS`)
  e rode `tests/test_sil.py`. Ele continua bit a bit igual? Pesquise o que `-ffast-math` permite ao compilador e por que isso é proibido em código de segurança.

### Etapa 12 · Rastreabilidade
- **Código:** `scripts/rastreabilidade.py` acha as linhas do C pelas etiquetas `REQ-...`.
- **Para refletir:** o que a seção 12 do relatório diz que ainda falta para certificar?

---

### Ordem para rodar tudo do zero
```bash
pip install -r requirements.txt
python -m pytest
python scripts/memorial.py
python scripts/figuras.py
python scripts/rastreabilidade.py
python relatorio/gerar_pdf.py
```
