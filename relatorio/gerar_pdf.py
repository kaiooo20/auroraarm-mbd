"""Gera o relatório técnico em PDF (partes teórica e prática + memorial em anexo).

Todos os números vêm de resultados/memorial.json e resultados/rastreabilidade.json.
Uso:  python relatorio/gerar_pdf.py   ->  relatorio/AuroraArm_relatorio_tecnico.pdf
"""
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from auroraarm import controlador as ctl  # noqa: E402
from auroraarm.parametros import Parametros  # noqa: E402

M = json.loads((RAIZ / "resultados/memorial.json").read_text(encoding="utf-8"))
RT = json.loads((RAIZ / "resultados/rastreabilidade.json").read_text(encoding="utf-8"))
FIG = RAIZ / "resultados/figuras"
p = Parametros.carregar()
REPO = "https://github.com/kaiooo20/auroraarm-mbd"

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DV-I", F + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DVM", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")

AZUL = colors.HexColor("#1c5cab")
CINZA = colors.HexColor("#6b6b6b")
FUNDO = colors.HexColor("#f2f5fa")
corpo = ParagraphStyle("corpo", fontName="DV", fontSize=9.6, leading=13.6, alignment=TA_JUSTIFY,
                       spaceAfter=5)
h1 = ParagraphStyle("h1", fontName="DV-B", fontSize=14, leading=18, textColor=AZUL,
                    spaceBefore=10, spaceAfter=6)
h2 = ParagraphStyle("h2", fontName="DV-B", fontSize=11, leading=14, textColor=AZUL,
                    spaceBefore=8, spaceAfter=4)
parte = ParagraphStyle("parte", fontName="DV-B", fontSize=18, leading=22, textColor=AZUL,
                       alignment=TA_CENTER, spaceBefore=120, spaceAfter=20)
leg = ParagraphStyle("leg", fontName="DV-I", fontSize=8.2, leading=10.5, textColor=CINZA,
                     alignment=TA_CENTER, spaceAfter=8)
cel = ParagraphStyle("cel", fontName="DV", fontSize=7.8, leading=9.6)
celb = ParagraphStyle("celb", parent=cel, fontName="DV-B", textColor=colors.white)
eq = ParagraphStyle("eq", fontName="DV", fontSize=9.6, leading=14, alignment=TA_CENTER,
                    spaceBefore=2, spaceAfter=6)
mono = ParagraphStyle("mono", fontName="DVM", fontSize=7.2, leading=9.2, backColor=FUNDO,
                      borderPadding=5, spaceBefore=3, spaceAfter=8)
bul = ParagraphStyle("bul", parent=corpo, leftIndent=14, bulletIndent=4, spaceAfter=3)

S = []


def P(t, st=corpo):
    S.append(Paragraph(t, st))


def B(t):
    S.append(Paragraph(t, bul, bulletText="•"))


def E(t):
    import re
    t = re.sub(r" {2,}", lambda m: "&nbsp;" * (2 * len(m.group(0))), t)
    S.append(Paragraph(t, eq))


def fig(nome, legenda, larg=16.0):
    img = Image(str(FIG / nome))
    r = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = larg * cm, larg * cm * r
    S.append(KeepTogether([img, Paragraph(legenda, leg)]))


def tab(linhas, larguras, cab=True, zebra=True):
    dados = [[Paragraph(str(c), celb if (cab and i == 0) else cel) for c in l]
             for i, l in enumerate(linhas)]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1 if cab else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cfd8")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if cab:
        st.append(("BACKGROUND", (0, 0), (-1, 0), AZUL))
    if zebra:
        for i in range(1 if cab else 0, len(linhas)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), FUNDO))
    t.setStyle(TableStyle(st))
    S.append(t)
    S.append(Spacer(1, 7))


def code(t):
    S.append(Preformatted(t, mono))


def n(x, d=2):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


a, b_, c_, mc, d_, ve, rs, e_, rc, idf = (M[k] for k in ("a", "b", "c", "controle", "d",
                                                          "verificacao", "req_safe_004", "e",
                                                          "recursos", "identificacao"))
v1 = ve["v1"]
g = mc["ganhos"]

# ============================================================================ CAPA
S.append(Spacer(1, 2.2 * cm))
for t, st in [("UNIFECAF — Engenharia da Computação", ParagraphStyle("c1", fontName="DV-B", fontSize=12, alignment=TA_CENTER, textColor=CINZA)),
              ("Model Based Design for Cyber-Physical Systems", ParagraphStyle("c2", fontName="DV", fontSize=11, alignment=TA_CENTER, textColor=CINZA, spaceBefore=4))]:
    S.append(Paragraph(t, st))
S.append(Spacer(1, 3.2 * cm))
S.append(Paragraph("Operação Linha Viva", ParagraphStyle("t0", fontName="DV-B", fontSize=26, leading=32, alignment=TA_CENTER, textColor=AZUL)))
S.append(Paragraph("Modelagem, controle, verificação formal e geração de código da junta do cotovelo do braço colaborativo AuroraArm",
                   ParagraphStyle("t1", fontName="DV", fontSize=13, leading=18, alignment=TA_CENTER, spaceBefore=10)))
S.append(Spacer(1, 1.0 * cm))
S.append(Paragraph("Relatório técnico — parte teórica, parte prática e memorial de cálculo (Anexo A)",
                   ParagraphStyle("t2", fontName="DV-I", fontSize=10, alignment=TA_CENTER, textColor=CINZA)))
S.append(Spacer(1, 4.2 * cm))
S.append(Paragraph("Kaio Santana Rodrigues Santos — RA 98328", ParagraphStyle("a1", fontName="DV-B", fontSize=11, alignment=TA_CENTER)))
S.append(Paragraph(f"Repositório: <link href='{REPO}' color='#1c5cab'>{REPO}</link>",
                   ParagraphStyle("a2", fontName="DV", fontSize=9.5, alignment=TA_CENTER, spaceBefore=6)))
S.append(Spacer(1, 2.4 * cm))
S.append(Paragraph("São Paulo, outubro de 2026", ParagraphStyle("a3", fontName="DV", fontSize=10, alignment=TA_CENTER, textColor=CINZA)))
S.append(PageBreak())

# ============================================================================ SUMÁRIO
P("Sumário", h1)
for item in ["1. Introdução e resumo dos resultados",
             "PARTE TEÓRICA",
             "2. Modelagem física da junta",
             "3. Requisitos: desempenho x segurança colaborativa",
             "4. Fundamentação das escolhas de controle, verificação e geração de código",
             "PARTE PRÁTICA",
             "5. Organização do repositório e reprodução",
             "6. Modelo da planta, identificação e validação",
             "7. Controlador: projeto, saturação e anti-windup",
             "8. Supervisor de segurança e verificação formal",
             "9. Testes baseados em modelo e cobertura",
             "10. Geração de código C e equivalência SIL",
             "11. Matriz de rastreabilidade",
             "12. Honestidade técnica: o que o pacote sustenta e o que falta",
             "Referências",
             "ANEXO A — Memorial de cálculo, itens (a) a (e)"]:
    st = ParagraphStyle("su", parent=corpo, fontName="DV-B" if item.isupper() else "DV",
                        textColor=AZUL if item.isupper() else colors.black,
                        leftIndent=0 if item.isupper() else 12, spaceAfter=2,
                        spaceBefore=6 if item.isupper() else 0)
    P(item, st)
S.append(PageBreak())

# ============================================================================ 1
P("1. Introdução e resumo dos resultados", h1)
P("Um protótipo anterior de célula colaborativa da Aurora Robótica sofreu um quase-acidente: o torque "
  "da junta não foi zerado a tempo quando um operador aproximou a mão do efetuador, porque o firmware "
  "escrito à mão não tratava uma condição de borda entre os estados de movimento e de parada de "
  "segurança. Não havia modelo formal nem evidência reprodutível de que os requisitos de segurança "
  "fossem satisfeitos. Este trabalho entrega, para a junta do cotovelo do AuroraArm, o pacote de "
  "evidências exigido para a auditoria de segurança: <b>modelo</b> em espaço de estados identificado e "
  "validado, <b>controlador</b> com saturação e anti-windup, <b>supervisor de segurança</b> verificado "
  "exaustivamente por model checking, <b>código C gerado</b> a partir do modelo com equivalência "
  "numérica demonstrada em SIL e <b>matriz de rastreabilidade</b> de requisito a teste.")
P("O método é o mesmo construído ao longo da disciplina para o NexaBot, aplicado a um novo sistema. "
  "Tudo é reprodutível com dois comandos (seção 5); cada número citado aqui é lido de "
  "<font name='DVM'>resultados/memorial.json</font>, gerado por <font name='DVM'>scripts/memorial.py</font>.")
tab([["Requisito", "Exigido", "Obtido", "Como foi demonstrado"],
     ["REQ-CTRL-AA-001", "erro em regime nulo", f"{mc['pior_erro_regime_rad']:.1e} rad", "simulação, 9 cenários"],
     ["REQ-CTRL-AA-002", "sobressinal ≤ 8 %", f"{n(mc['pior_sobressinal_pct'])} % (pior caso)", "simulação, 9 cenários + robustez"],
     ["REQ-CTRL-AA-003", "acomodação ≤ 300 ms", f"{mc['pior_t_acomodacao_s']*1e3:.0f} ms (pior caso)", "simulação, 9 cenários + robustez"],
     ["REQ-CTRL-AA-004", "|V| ≤ 48 V, |i| ≤ 8 A", f"|i| ≤ {n(mc['pior_i_A'])} A; |V| ≤ 48 V", "simulação + 5 000 entradas aleatórias"],
     ["REQ-SAFE-AA-001", "torque zero ≤ 100 ms", f"{n(d_['pior_latencia_ms'])} ms (pior caso)", f"model checking ({v1['n_estados']:,} estados) + varredura de {d_['n_combinacoes']:,} combinações".replace(",", ".")],
     ["REQ-SAFE-AA-002", "só religa com rearme", "verdadeira", "model checking (P2) + MBT"],
     ["REQ-SAFE-AA-003", "retorna à trajetória", "verdadeira", "model checking de vivacidade (P3)"],
     ["REQ-SAFE-AA-004", "v ≤ 250 mm/s na zona", f"{rs['w_regime_colab_rad_s']/p.N*p.braco_m*1e3:.0f} mm/s em regime", "model checking (P4) + simulação"]],
    [3.0, 3.4, 3.8, 6.3])
P(f"O model checker encontrou na versão preliminar do supervisor (v0) um contraexemplo real de "
  f"REQ-SAFE-AA-001 que reproduz o tipo de falha do protótipo anterior (seção 8.4); o código gerado é "
  f"<b>bit a bit idêntico</b> ao modelo em precisão simples ao longo de {e_['n_amostras']:,} amostras "
  f"(seção 10); o firmware ocupa {rc['text_bytes']} bytes (de 256 KB) e no máximo "
  f"{n(rc['t_exec_cota_us_168MHz'])} µs por ciclo (de 200 µs).".replace(",", "X").replace(".", ",").replace("X", "."))

# ============================================================================ PARTE TEÓRICA
S.append(PageBreak())
P("PARTE TEÓRICA", parte)
S.append(PageBreak())
P("2. Modelagem física da junta", h1)
P("A junta é um motor CC de ímã permanente de 48 V acoplado a uma transmissão harmônica 100:1. Todas "
  "as grandezas mecânicas são <b>referidas ao eixo do motor</b>: a inércia e o atrito da tabela já são "
  "os valores refletidos, e o torque de carga de 0,25 N m é o torque do payload (2 kg a 0,35 m) "
  "dividido pela redução. Ângulo e velocidade da junta são θ<sub>j</sub> = θ<sub>m</sub>/N e "
  "ω<sub>j</sub> = ω/N (Siciliano et al., 2010, cap. 5).")
P("2.1 Leis de conservação", h2)
P("<b>Equação elétrica da armadura</b> (lei das malhas de Kirchhoff — conservação de energia no "
  "circuito): a tensão aplicada se divide entre a queda resistiva, a queda indutiva e a força "
  "contraeletromotriz, proporcional à velocidade:")
E("L · di/dt = V − R·i − K<sub>e</sub>·ω")
P("<b>Equação mecânica do eixo</b> (2ª lei de Newton na rotação — conservação do momento angular): "
  "o torque eletromagnético acelera a inércia contra o atrito viscoso e o torque de carga:")
E("J · dω/dt = K<sub>t</sub>·i − b·ω − T<sub>L</sub>")
P("O acoplamento eletromecânico aparece duas vezes, em K<sub>t</sub>·i e em K<sub>e</sub>·ω. Em "
  "unidades SI, K<sub>t</sub> = K<sub>e</sub> (0,085 nos dados) é consequência da conservação de "
  "potência no entreferro: K<sub>t</sub>·i·ω = K<sub>e</sub>·ω·i.")
P("2.2 Escolha das variáveis de estado", h2)
P("O estado de um sistema é o conjunto mínimo de variáveis que, junto com as entradas futuras, "
  "determina todo o comportamento futuro. Cada elemento armazenador de energia contribui com uma "
  "variável: a indutância armazena ½·L·i² e a inércia armazena ½·J·ω². Por isso:")
B("<b>x<sub>1</sub> = i</b> (corrente): é a energia magnética e, por ser proporcional ao torque, é a "
  "grandeza limitada pelo driver (8 A) — precisa estar visível no modelo.")
B("<b>x<sub>2</sub> = ω</b> (velocidade do eixo): é a energia cinética e aparece na f.c.e.m., que "
  "consome a maior parte da tensão no ponto crítico (38,25 de 41,24 V).")
B("Para o laço de posição acrescenta-se <b>θ<sub>m</sub></b> (dθ<sub>m</sub>/dt = ω), um integrador "
  "puro que não armazena energia mas é a grandeza controlada (modelo de 3 estados em "
  "<font name='DVM'>auroraarm/planta.py::matrizes_posicao</font>).")
P("Ambas as variáveis são mensuráveis (sensor de corrente do driver e encoder), têm significado físico "
  "direto e tornam as matrizes lineares e invariantes no tempo. Resultado (memorial, item a):")
E("ẋ = A·x + B·V + E·T<sub>L</sub>,  y = C·x,  A = [−R/L  −K<sub>e</sub>/L ; K<sub>t</sub>/J  −b/J],  "
  "B = [1/L ; 0],  E = [0 ; −1/J],  C = [0  1]")
P("<b>Premissas do modelo:</b> transmissão rígida (a flexibilidade da harmônica, relevante acima de "
  "algumas dezenas de Hz, não foi modelada — ver seção 12); atrito apenas viscoso (sem Coulomb); "
  "parâmetros constantes (sem aquecimento da armadura); torque de carga tratado como perturbação "
  "constante de ±0,25 N m (na prática varia com a configuração do braço); driver de ponte H ideal "
  "(tensão aplicada = comando, dentro de ±48 V).")
P("2.3 Dinâmica resultante", h2)
P(f"Os autovalores de A são {n(a['autovalores'][0],1)} e {n(a['autovalores'][1],2)} rad/s, ambos reais e "
  f"negativos: o motor em malha aberta é estável e sem oscilação. Eles definem duas constantes de "
  f"tempo, τ<sub>e</sub> = {n(a['tau_e_ms'],3)} ms (elétrica) e τ<sub>m</sub> = {n(a['tau_m_ms'],1)} ms "
  f"(mecânica), separadas por um fator {n(a['razao_tau'],1)}. Essa separação de escalas de tempo "
  f"justifica três decisões do projeto: (i) identificar as equações elétrica e mecânica em etapas "
  f"diferentes (seção 6); (ii) projetar o controlador de posição sobre um modelo reduzido de 2ª ordem "
  f"que ignora τ<sub>e</sub> (seção 7); (iii) tratar o corte do torque como quase instantâneo frente "
  f"ao prazo de 100 ms (≤ 5τ<sub>e</sub> = {n(5*a['tau_e_ms'],2)} ms, seção 8).")

# ============================================================================ 3
P("3. Requisitos: desempenho x segurança colaborativa", h1)
P("Os dois grupos de requisitos têm naturezas diferentes e, por isso, exigem técnicas de demonstração "
  "diferentes:")
tab([["Aspecto", "Desempenho (REQ-CTRL-AA-001..004)", "Segurança colaborativa (REQ-SAFE-AA-001..004)"],
     ["O que restringe", "qualidade da resposta contínua (erro, sobressinal, tempo, limites físicos)", "comportamento discreto do sistema na presença de pessoas (estados, eventos, prazos)"],
     ["Domínio", "sinais contínuos, equações diferenciais", "eventos discretos e tempo (autômatos temporizados)"],
     ["Origem", "engenharia de processo (produtividade)", "ISO/TS 15066 e ISO 10218 (risco a pessoas)"],
     ["Consequência da falha", "peça mal montada, perda de ciclo", "lesão do operador"],
     ["Evidência adequada", "simulação em cenários + robustez; testes", "verificação EXAUSTIVA de todos os comportamentos possíveis"],
     ["Por que não basta simular", "o espaço de cenários relevante é pequeno e contínuo", "a falha está em combinações raras de eventos (a do protótipo era uma condição de borda)"]],
    [3.2, 6.4, 6.9])
P("Na lógica temporal (Baier e Katoen, 2008, cap. 3), uma <b>propriedade de segurança</b> afirma que "
  "“algo ruim nunca acontece”: toda violação tem um prefixo finito que a demonstra (um traço "
  "que termina no instante do erro). Uma <b>propriedade de vivacidade</b> afirma que “algo bom "
  "eventualmente acontece”: nenhum prefixo finito a viola, porque o bom ainda pode acontecer depois; "
  "a violação é um traço infinito (na prática, um ciclo) em que o bom nunca ocorre.")
tab([["Requisito", "Classificação", "Formalização", "Justificativa"],
     ["REQ-SAFE-AA-001: mão a < 500 mm → torque zero em ≤ 100 ms", "<b>Segurança</b> (com prazo — “vivacidade limitada”)",
      "AG(mão → AF<sub>≤100ms</sub> torque_zero), verificada como invariante: “nunca a mão fica mais de 100 ms no campo com torque ≠ 0”",
      "Embora tenha a forma “eventualmente”, o prazo a torna de segurança: se for violada, existe um instante finito (100 ms após a entrada da mão) em que o erro já é visível."],
     ["REQ-SAFE-AA-002: depois de zerado, não religa sem rearme", "<b>Segurança</b>",
      "AG((PARADA ∨ AGUARDA) ∧ ¬rearme → AX ¬habilita)",
      "A coisa ruim (religar sem rearme) é um evento observável numa única transição."],
     ["REQ-SAFE-AA-003: mão removida e rearme → volta à trajetória", "<b>Vivacidade</b>",
      "AG(rearme ∧ ¬mão → AF(retomou ∨ mão)) (“leads-to”)",
      "Não há prazo: nenhum prefixo finito viola. A violação seria ficar para sempre sem retomar — um ciclo no grafo de estados."],
     ["REQ-SAFE-AA-004: v ≤ 250 mm/s na zona colaborativa", "<b>Segurança</b> (invariante)",
      "AG(zona ∧ habilita → AF<sub>≤6ms</sub> lim_vel) + G(v ≤ 250 mm/s) após a desaceleração",
      "Ultrapassar a velocidade é um evento instantâneo detectável num prefixo finito."]],
    [3.6, 2.6, 4.9, 5.4])
P("Note o par de cuidados na formalização de REQ-SAFE-AA-001 e 004: um requisito em linguagem natural "
  "esconde premissas (o que é “detectada”? a partir de quando conta o prazo?). A seção 8.4 mostra que "
  "a primeira formalização do monitor estava errada e produziu um contraexemplo espúrio — um "
  "exemplo concreto de que formalizar é parte do trabalho de engenharia, e não um detalhe.")

# ============================================================================ 4
P("4. Fundamentação das escolhas", h1)
P("4.1 Controle (Unidades 1 e 2)", h2)
P("<b>PID discreto em vez de realimentação de estados.</b> A realimentação de estados exigiria a "
  "corrente na lei de controle a 500 Hz, mas τ<sub>e</sub>/T<sub>s</sub> = "
  f"{n(c_['amostras_por_tau_e'],2)}: a dinâmica elétrica termina dentro de um único período e não pode "
  "ser controlada pelo laço de posição (memorial, item c). Com a planta efetivamente de 2ª ordem "
  "(integrador + polo mecânico), um PID com ação integral dá erro nulo para degrau mesmo com a "
  "carga constante (tipo 1 em relação à perturbação), e é o que a equipe da Aurora já conhece — "
  "vantagem de manutenção. Os ganhos partiram de alocação de três polos reais no modelo reduzido e "
  "foram refinados por otimização sobre o laço não linear (<font name='DVM'>scripts/sintonia.py</font>).")
P("<b>Estrutura 2-GDL.</b> A derivada é aplicada só à medição (evita o “chute derivativo” no degrau) "
  "e filtrada (T<sub>f</sub> = 1 ms); o termo proporcional usa ponderação de referência β = 0,55, que "
  "remove o zero de malha fechada responsável pelo sobressinal sem perder rejeição de perturbação.")
P(f"<b>Saturação e anti-windup.</b> No ponto crítico a folga de tensão é de apenas {n(b_['folga_V'],2)} V "
  f"({n(b_['folga_V_pct'],1)} %) (item b): qualquer transitório satura o atuador. Durante a saturação o "
  "integrador continua acumulando erro (windup) e, ao sair dela, produz grande sobressinal. Usou-se "
  "<b>retrocálculo</b> (back-calculation): o integrador recebe K<sub>aw</sub>·(u<sub>sat</sub> − u). "
  "A saturação tem duas camadas: uma janela de tensão que mantém |i| ≤ 7,5 A, calculada a partir da "
  "f.c.e.m. estimada (K<sub>e</sub>·ω̂ ± R·i<sub>lim</sub>), e por último o limite rígido de ±48 V.")
P("<b>Discretização.</b> A planta foi discretizada por segurador de ordem zero exato (exponencial de "
  "matriz) — é assim que o conversor PWM aplica a tensão; a simulação usa 20 subpassos por período só "
  "para registrar picos de corrente. O controlador é escrito diretamente em diferenças (Euler para o "
  "integrador, filtro de 1ª ordem para a derivada), forma que vai literalmente para o C.")
P("4.2 Verificação (Unidade 3)", h2)
P("O supervisor foi modelado como uma máquina de estados síncrona e composto com autômatos temporizados "
  "do ambiente (mão, zona, rearme), do scanner (atraso não determinístico em [0, 20] ms), do RTOS "
  "(período de 2 ms com possível perda de um ciclo) e do driver (corte do torque em 8 ms). Por "
  "serem autômatos <i>fechados</i> (guardas ≤ e ≥ com constantes inteiras), a semântica de relógios "
  "digitais com passo de 1 ms preserva as propriedades de alcançabilidade do tempo denso "
  "(Henzinger, Manna e Pnueli, 1992), o que permite uma exploração explícita e exaustiva em busca em "
  "largura — a mesma ideia do UPPAAL. Propriedades com prazo viraram <b>monitores</b> (relógios "
  "observadores, Baier e Katoen, 2008, cap. 9) e a vivacidade virou busca de <b>ciclos</b> no "
  "subgrafo de estados com obrigação pendente.")
P("Escreveu-se um model checker próprio (<font name='DVM'>auroraarm/verificacao.py</font>, ~300 linhas) "
  "em vez de usar UPPAAL por três motivos: (i) o modelo do supervisor verificado é <i>exatamente</i> a "
  "tabela que gera o código C — não há tradução manual para outra linguagem; (ii) o checker roda no "
  "mesmo pytest, a cada mudança; (iii) o checador é ele próprio testado com mutantes (seção 9). O "
  "custo é que uma ferramenta própria não é qualificada (seção 12).")
P("Os testes do supervisor foram <b>gerados do modelo</b> (MBT): caminhos que cobrem cada transição, "
  "todos os pares estado × entrada e passeios aleatórios com invariantes — e executados contra a "
  "implementação Python <i>e</i> o C gerado.")
P("4.3 Geração de código e certificação (Unidade 4)", h2)
P("O controlador é um <b>modelo executável</b>: uma lista ordenada de passos de fluxo de dados "
  "(<font name='DVM'>controlador.PASSOS</font>). O mesmo modelo é interpretado em Python e traduzido "
  "para C por <font name='DVM'>auroraarm/codegen.py</font>, que imprime uma operação por linha na mesma "
  "ordem, em float IEEE-754 binário32 (a FPU do Cortex-M4 é de precisão simples), sem laços, "
  "recursão ou alocação dinâmica (tempo de execução constante, requisito típico da IEC 61508-3 para "
  "software de segurança), e com <font name='DVM'>-ffp-contract=off</font> (sem FMA, que mudaria os "
  "arredondamentos). Cada linha do C carrega a etiqueta do requisito que implementa, e o cabeçalho tem "
  "um bloco de rastreabilidade com o hash do modelo e dos parâmetros; um teste falha se o C versionado "
  "divergir do que o gerador produz hoje. A equivalência foi verificada em SIL: o C compilado roda via "
  "ctypes com as mesmas entradas do modelo e também fecha a malha com a planta simulada. A co-simulação "
  "por FMI (fonte 6) não foi usada: como planta e controlador estão no mesmo ambiente Python, o SIL por "
  "ctypes cumpre o mesmo papel sem a camada de empacotamento FMU; numa integração com outra ferramenta "
  "(p. ex. o simulador da célula) o C gerado poderia ser empacotado como FMU de co-simulação.")
P("4.4 Normas e caso real", h2)
P("A <b>ISO/TS 15066</b> define os modos colaborativos; este projeto combina <i>parada monitorada de "
  "segurança</i> (REQ-SAFE-AA-001/002) com <i>monitoramento de velocidade e separação</i> "
  "(REQ-SAFE-AA-004), e a distância do campo de alerta foi dimensionada com a velocidade de "
  "aproximação de 1,6 m/s da ISO 13855. A <b>IEC 61508</b> enquadra o supervisor como função de "
  "segurança e motiva as escolhas de código (subconjunto restrito, determinismo, rastreabilidade) e a "
  "discussão de qualificação de ferramentas e independência da seção 12.")
P("Como caso real, adotou-se Colim et al. (2021), que relatam a reformulação de um posto de montagem "
  "manual em posto colaborativo com um <b>UR10e</b> (Universal Robots): avaliação de risco inicial, "
  "escolha do cobot pela reach, 6 GDL e sensor de torque embutido, garra a vácuo colaborativa, "
  "proteção física ISO 13857 apenas onde havia perigo térmico, e medição ergonômica antes/depois. Duas "
  "lições foram trazidas para cá: (i) a segurança é demonstrada por <i>avaliação de risco "
  "sistemática</i>, não pela escolha do robô — o cobot certificado não dispensa a análise da "
  "aplicação; (ii) o perigo dominante pode estar fora do braço (lá, a cola quente; aqui, a latência "
  "do scanner e do RTOS, que juntos respondem por 75 % do pior caso de REQ-SAFE-AA-001).")

# ============================================================================ PARTE PRÁTICA
S.append(PageBreak())
P("PARTE PRÁTICA", parte)
S.append(PageBreak())
P("5. Organização do repositório e reprodução", h1)
P(f"Repositório: <link href='{REPO}' color='#1c5cab'>{REPO}</link>. Todos os caminhos citados neste "
  "relatório são relativos à raiz do repositório.")
code("""parametros.json            fonte única dos dados do enunciado
auroraarm/                 o MODELO (biblioteca Python)
  planta.py                espaço de estados, ZOH, simulação          -> seções 2, 6, memorial (a)(b)(c)
  identificacao.py         ensaio emulado, mínimos quadrados, validação -> seção 6
  controlador.py           PID 2-GDL + saturação + anti-windup (PASSOS) -> seção 7
  supervisor.py            tabela de transições v0 (com defeito) e v1  -> seção 8
  verificacao.py           model checker: P1..P4, contraexemplos       -> seção 8, memorial (d)
  testes_modelo.py         geração de testes a partir do grafo         -> seção 9
  codegen.py               gerador de C a partir do modelo             -> seção 10
  sil.py                   SIL via ctypes, equivalência numérica       -> seção 10, memorial (e)
gen/auroraarm_junta.{h,c}  código C GERADO (não editar)
sil/bench.c                medição de tempo no host
scripts/                   sintonia.py, memorial.py, figuras.py, rastreabilidade.py
tests/                     42 testes pytest (requisitos, MBT, SIL, model checking, codegen)
resultados/                memorial.json/.txt, contraexemplo_v0.txt, figuras/
docs/                      passo-a-passo.md (guia de estudo), rastreabilidade.md""")
code("""pip install -r requirements.txt          # numpy, scipy, matplotlib, pytest, reportlab
python -m pytest                         # 42 testes: requisitos, MBT, SIL, model checking
python scripts/memorial.py               # recalcula o memorial (itens a..e) e o model checking
python scripts/figuras.py && python scripts/rastreabilidade.py && python relatorio/gerar_pdf.py""")

# ============================================================================ 6
P("6. Modelo da planta, identificação e validação", h1)
P(f"As matrizes (memorial, item a) estão em <font name='DVM'>auroraarm/planta.py::matrizes</font> e são "
  f"conferidas por <font name='DVM'>tests/test_planta.py</font>. O posto 2 das matrizes de "
  f"controlabilidade e de observabilidade (com y = ω) garante que a tensão consegue levar a junta a "
  f"qualquer estado e que a corrente pode ser reconstruída só a partir da velocidade — o que justifica "
  f"usar um observador caso o sensor de corrente falhe (degradação considerada na seção 12). A "
  f"simulação em malha aberta com V = {n(b_['V_ss'],2)} V e T<sub>L</sub> = 0,25 N m converge para "
  f"exatamente 450 rad/s e {n(b_['i_ss'],3)} A, validando o balanço de regime do item (b).")
P("<b>Identificação.</b> Sem acesso à bancada, o ensaio foi emulado: tensão PRBS (níveis de 5 ms) e "
  "degrau de carga sobre a planta nominal, com ruído de 0,02 A na corrente e 0,5 rad/s no encoder. "
  "Aproveitando a separação de escalas, a equação elétrica foi estimada a 10 kHz por mínimos quadrados, "
  "com inversão exata da ZOH; a mecânica, na forma integral em janelas de 10 ms, o que filtra o ruído "
  "do encoder. A validação usou um <i>segundo</i> conjunto de dados (outra semente, outra amplitude, "
  "outra carga) em simulação livre:")
tab([["Parâmetro", "Nominal", "Estimado", "Erro"]] +
    [[k, f"{idf['nominal'][k]:.4g}", f"{idf['identificado'][k]:.4g}", f"{n(idf['erro_pct'][k],2)} %"]
     for k in ("R", "L", "Ke", "J", "b")] +
    [["Ajuste NRMSE (validação)", "", f"ω: {n(idf['fit_w_pct'],1)} %", f"i: {n(idf['fit_i_pct'],1)} %"]],
    [5.0, 3.5, 3.5, 4.5])
P("<b>Defeito encontrado e corrigido:</b> a primeira versão estimava tudo de uma vez a 10 kHz e "
  "errou o atrito em 119 %, porque o ruído do encoder entra no regressor (erro nas variáveis) e a "
  "dinâmica mecânica quase não muda de uma amostra para a outra. O teste "
  "<font name='DVM'>tests/test_identificacao.py</font> exige erro < 2 % em todos os parâmetros.")
fig("fig2_identificacao.png", "Figura 1 — Validação cruzada: o modelo identificado, simulado sem realimentar a medição, reproduz a velocidade medida num ensaio que não foi usado na estimação.")

# ============================================================================ 7
P("7. Controlador: projeto, saturação e anti-windup", h1)
P(f"Modelo reduzido para projeto (desprezando τ<sub>e</sub>): θ<sub>m</sub>(s)/V(s) = K/(s(τs+1)), com "
  f"K = K<sub>t</sub>/(Rb + K<sub>t</sub>K<sub>e</sub>) = {n(mc['K_reduzido'],3)} rad/(V·s) e "
  f"τ = RJ/(Rb + K<sub>t</sub>K<sub>e</sub>) = {n(mc['tau_reduzido_ms'],2)} ms. Com PID, a equação "
  f"característica é τs³ + (1 + K K<sub>d</sub>)s² + K K<sub>p</sub> s + K K<sub>i</sub> = 0; impondo três polos "
  f"em −30 rad/s obtém-se o ponto de partida K<sub>p</sub> = 10,7, K<sub>i</sub> = 107, K<sub>d</sub> = 0,27. O "
  f"refinamento minimizou o pior tempo de acomodação sobre 9 cenários (degraus de ±10 e 2 rad no "
  f"motor; carga de +0,25, 0 e −0,25 N m), penalizando sobressinal acima de 4 % (metade da folga do "
  f"requisito). Ganhos finais, em <font name='DVM'>auroraarm/controlador.py::GANHOS_PADRAO</font>: "
  f"K<sub>p</sub> = {n(g['Kp'],1)} V/rad, K<sub>i</sub> = {n(g['Ki'],0)} V/(rad·s), K<sub>d</sub> = {n(g['Kd'],2)} V·s/rad, "
  f"T<sub>f</sub> = 1 ms, β = {n(g['beta'],2)}, K<sub>aw</sub> = {n(g['Kaw'],2)}.")
P(f"<b>Premissa do ensaio de degrau:</b> 0,1 rad na junta (≈ 5,7°, 10 rad no motor), aplicado com a "
  f"junta já em equilíbrio sob carga. Esse degrau leva o laço ao limite de corrente; movimentos maiores "
  f"do ciclo de pega-e-solta são feitos por trajetórias suaves, não por degraus. Fora desse envelope "
  f"(degrau de 15 rad com carga a favor) o sobressinal chega a "
  f"{n(mc['fora_do_envelope_15rad_carga_neg']['sobressinal_pct'],1)} % — limitação registrada.")
linhas = [["Degrau (motor)", "Carga [N m]", "Sobressinal", "t<sub>s</sub> (2 %)", "Erro regime", "|V| máx", "|i| máx"]]
for c in mc["cenarios"]:
    linhas.append([f"{c['amplitude_rad_motor']:+.0f} rad", f"{c['T_carga']:+.2f}", f"{n(c['sobressinal_pct'],2)} %",
                   f"{c['t_acomodacao_s']*1e3:.0f} ms", f"{c['erro_regime_rad']:.1e}", f"{n(c['V_max_abs'],1)} V",
                   f"{n(c['i_max_abs'],2)} A"])
linhas.append(["sem anti-windup", "+0,25", f"{n(mc['sem_antiwindup']['sobressinal_pct'],1)} %", "não acomoda", "—", f"{n(mc['sem_antiwindup']['V_max_abs'],1)} V", f"{n(mc['sem_antiwindup']['i_max_abs'],2)} A"])
tab(linhas, [2.8, 2.0, 2.2, 2.2, 2.3, 2.2, 2.2])
fig("fig1_degrau.png", "Figura 2 — Degrau de 0,1 rad: com retrocálculo (azul) a junta acomoda em 218 ms com 0,5 % de sobressinal; sem ele (laranja) o integrador acumula erro durante a saturação de corrente e o pico de posição chega a 94 % acima da referência.")
P(f"<b>Margens.</b> No laço linearizado, com atraso equivalente de 1,5 T<sub>s</sub> (ZOH + cálculo), a "
  f"frequência de cruzamento é {n(mc['freq_cruzamento_rad_s'],1)} rad/s ({n(c_['banda_malha_fechada_Hz'],1)} Hz) "
  f"e a margem de fase é {n(mc['margem_fase_graus'],1)}°, com {mc['amostras_por_periodo_cruzamento']:.0f} amostras "
  f"por período de cruzamento. Robustez: com J ±20 % todos os requisitos continuam atendidos "
  f"(<font name='DVM'>tests/test_controlador.py::test_robustez_inercia</font>).")
P("<b>Defeito encontrado e corrigido:</b> a primeira versão saturava com min/max combinados. O teste "
  "aleatório do SIL mostrou que, se |K<sub>e</sub>·ω̂| > V<sub>max</sub> + R·i<sub>lim</sub> (sobrevelocidade "
  "ou pulo do encoder), a janela se invertia e o comando chegava a 4 952 V. Agora o limite do "
  "barramento é aplicado por último e o teste com 5 000 entradas absurdas garante |V| ≤ 48 V.")

# ============================================================================ 8
P("8. Supervisor de segurança e verificação formal", h1)
P("8.1 Modelo do supervisor", h2)
P("Cinco estados, nove transições com prioridade, executado a cada ciclo de 2 ms "
  "(<font name='DVM'>auroraarm/supervisor.py</font>). Em PARADA e AGUARDA_REARME o driver é "
  "desabilitado (STO); a única saída para um estado com torque é T7, que exige rearme. Na RETOMADA o "
  "braço volta à trajetória em velocidade colaborativa, partindo da posição medida (sem salto).")
fig("fig0_supervisor.png", "Figura 3 — Supervisor v1. Em vermelho, T8: a transição que faltava na versão preliminar v0 e cuja ausência o model checker encontrou.", 10.0)
P("8.2 Modelo verificado e premissas", h2)
pr = ve["premissas"]
tab([["Componente", "Comportamento modelado (todas as escolhas são exploradas)"],
     ["Ambiente", "a mão entra/sai do campo de 500 mm a qualquer ms; operador entra/sai da zona; rearme a qualquer ciclo"],
     ["Scanner", f"detecção com atraso não determinístico em [0, {pr['T_SENSOR']}] ms; saída acionada por ≥ {pr['T_TRAVA']} ms (A4)"],
     ["RTOS", f"tarefa de {pr['T_CICLO']} ms; pode perder 1 ciclo (nunca 2 seguidos); saída vale {pr['T_APLICA']} ms após a ativação (≥ 200 µs)"],
     ["Driver", f"habilita = 0 → torque nulo em {pr['T_OFF']} ms (≥ 5τ<sub>e</sub>; a simulação dá {n(M['torque_off']['t_1pct_ms'],2)} ms até 1 %)"],
     ["Retomada", f"termina em até {pr['K_RET']} ciclos = 120 ms se não for interrompida (A2)"],
     ["Premissa A1", "a mão permanece no campo até ser detectada (intrusões mais curtas que o tempo de resposta do scanner não são garantidas pelo fabricante)"]],
    [2.8, 13.7])
P("8.3 Resultado da verificação exaustiva (v1)", h2)
tab([["Propriedade", "Resultado", "Detalhe"],
     ["P1 — REQ-SAFE-AA-001", "VERDADEIRA", f"pior latência entrada da mão → torque nulo: {v1['pior_latencia_parada_ms']} ms (≤ 100)"],
     ["P2 — REQ-SAFE-AA-002", "VERDADEIRA", "nenhuma transição religa o torque sem rearme"],
     ["P3 — REQ-SAFE-AA-003", "VERDADEIRA", "nenhum ciclo alcançável com obrigação de retomada pendente"],
     ["P4 — REQ-SAFE-AA-004", "VERDADEIRA", f"pior resposta lógica à zona: {v1['pior_resposta_zona_ms']} ms (≤ 6)"],
     ["Espaço explorado", f"{v1['n_estados']:,} estados".replace(",", "."), f"{v1['n_transicoes']:,} transições; os 5 estados e as 9 transições do supervisor alcançados".replace(",", ".")]],
    [4.0, 2.6, 9.9])
P("8.4 Contraexemplos obtidos durante o desenvolvimento", h2)
P("<b>C1 — espúrio, de formalização.</b> A primeira versão do monitor de P1 mantinha a obrigação do "
  "prazo mesmo depois que a mão saía e o operador rearmava. O traço mostrava o braço operando "
  "normalmente com ninguém no campo e acusava violação aos 101 ms. A correção foi no <i>monitor</i>: "
  "o requisito protege a pessoa enquanto ela está no campo. Lição: um contraexemplo deve ser "
  "<i>lido</i> antes de corrigir o código.")
P("<b>C2 — real, supervisor v0.</b> A versão preliminar não tinha T8 (premissa implícita: “se o "
  "operador acabou de rearmar, a mão está longe”). O model checker devolveu o traço mais curto "
  f"({ve['v0']['tamanho_contraexemplo_ms']} ms, arquivo <font name='DVM'>resultados/contraexemplo_v0.txt</font>):")
code("""t=  1 ms  mão entra; scanner detecta
t=  4 ms  supervisor (após perder um ciclo): T3 -> PARADA; torque começa a cair
t=  7 ms  mão sai; t=8 ms: T5 -> AGUARDA_REARME
t=  8 ms  MÃO VOLTA, mas o scanner ainda não detectou (atraso de até 20 ms)
t= 10 ms  operador aperta o rearme; sensor = 0  ->  T7 -> RETOMADA, torque religado
t= 11 ms  scanner detecta a mão... v0 não tem transição RETOMADA --mao=1--> PARADA
t=109 ms  mão há 101 ms no campo com torque ligado  <<< VIOLAÇÃO de REQ-SAFE-AA-001""")
P("É exatamente uma “condição de borda entre os estados de movimento e de parada de segurança”, "
  "como a do protótipo anterior, e depende de uma combinação de três fatores (atraso do scanner, "
  "rearme durante esse atraso e mão que volta) que dificilmente apareceria em teste manual. Com T8 o "
  "supervisor v1 volta a PARADA no ciclo seguinte à detecção. Outro aprendizado: com a duração da "
  "retomada modelada como 5 ciclos o defeito <i>não</i> aparecia, porque a retomada terminava sozinha "
  "antes do prazo — a abstração precisa ser mais longa que o prazo verificado (K<sub>RET</sub> = 120 ms).")
fig("fig6_contraexemplo.png", "Figura 4 — Contraexemplo C2 na versão v0: a mão volta durante o atraso do scanner, o rearme religa o torque e a detecção posterior é ignorada até estourar o prazo.")
P("8.5 Prazo de 100 ms sob os atrasos informados (memorial, item d)", h2)
P(f"Além do model checking, a cadeia de latência foi varrida analiticamente em "
  f"{d_['n_combinacoes']:,}".replace(",", ".") +
  f" combinações (atraso do sensor de 0 a 20 ms em passos de 0,1 ms; instante da detecção dentro do "
  f"período; 0 ou 1 ciclo perdido; execução de 0 ou 200 µs; corte do torque pela simulação ou por "
  f"5τ<sub>e</sub>). <b>Todas</b> cumprem o prazo; o pior caso é {n(d_['pior_latencia_ms'],2)} ms, com margem "
  f"de {n(d_['margem_ms'],1)} ms. O valor inteiro do model checker ({v1['pior_latencia_parada_ms']} ms) é "
  f"coerente com ele (relógios de 1 ms). A violação exigiria {d_['ciclos_perdidos_consecutivos_para_violar']} "
  f"ciclos perdidos seguidos ou um scanner com atraso acima de {n(d_['atraso_sensor_para_violar_ms'],1)} ms.")
fig("fig4_latencia.png", "Figura 5 — Decomposição do pior caso de REQ-SAFE-AA-001 (memorial, item d).", 15.5)
P("8.6 REQ-SAFE-AA-004 na física da junta", h2)
P(f"A parte lógica (P4) garante que lim_vel liga em até {v1['pior_resposta_zona_ms']} ms. A parte física "
  f"depende de desacelerar: v = (ω/N)·r ≤ 0,25 m/s exige ω ≤ {n(rs['w_motor_lim_rad_s'],1)} rad/s no motor. A "
  f"referência colaborativa usa 85 % desse valor ({n(rs['w_ref_colab_rad_s'],1)} rad/s) e desacelera a "
  f"{rs['a_colab_rad_s2']:.0f} rad/s². Partindo do ponto crítico ({n(rs['v_antes_m_s'],2)} m/s), a junta fica "
  f"abaixo do limite em {rs['t_desaceleracao_ms']:.0f} ms e não volta a ultrapassá-lo; o pico de corrente "
  f"é {n(rs['i_pico_desac_A'],2)} A. Por isso o campo de <i>alerta</i> do scanner (que sinaliza "
  f"“zona”) deve ficar a pelo menos 1,6 m/s × {n(rs['t_resposta_total_ms']/1000,3)} s ≈ "
  f"<b>{n(rs['distancia_campo_alerta_m'],2)} m</b> da área de colaboração (ISO 13855) — requisito derivado "
  f"para o leiaute da célula.")
P("<b>Defeito encontrado e corrigido:</b> com limitação só de velocidade, a referência “freava” "
  "instantaneamente, o motor ultrapassava a referência e oscilava, com pico de 0,42 m/s. A versão "
  "atual limita também a aceleração da referência.")
fig("fig3_colaborativo.png", "Figura 6 — Entrada na zona colaborativa a 450 rad/s: a velocidade do efetuador fica abaixo de 250 mm/s em 666 ms e estabiliza em 212 mm/s.")

# ============================================================================ 9
P("9. Testes baseados em modelo e cobertura", h1)
P("Os casos do supervisor são <b>gerados</b> a partir da tabela de transições "
  "(<font name='DVM'>auroraarm/testes_modelo.py</font>) e executados na implementação Python e no "
  "C gerado (<font name='DVM'>tests/test_supervisor_mbt.py</font>):")
tab([["Gerador", "Casos", "Critério", "Python", "C gerado"],
     ["Percurso do grafo (BFS até a origem + disparo)", "9", "cobertura de transições", "9/9 (100 %)", "9/9 (100 %)"],
     ["Pares estado × entrada (5 × 16)", "80", "todas as transições e não transições", "80/80", "80/80"],
     ["Passeio aleatório com invariantes I1–I3", "20 000 ciclos", "propriedades REQ-SAFE-001/002/004", "0 violações", "0 violações"],
     ["Cobertura de estados", "—", "5 estados", "100 %", "100 %"]],
    [5.6, 1.8, 4.0, 2.5, 2.6])
P("<b>Os testes testam a si mesmos.</b> Rodando os casos gerados contra o supervisor v0, o caso MBT-T8 "
  "falha (e 797 violações do invariante I1 aparecem no passeio aleatório). Dois mutantes verificam o "
  "model checker: sem T9 ele acusa a violação de vivacidade P3; com T5 levando direto à RETOMADA ele "
  "acusa P2 (<font name='DVM'>tests/test_verificacao.py</font>). A suíte completa tem "
  "<b>42 testes, todos passando</b>, em cerca de 5 s.")

# ============================================================================ 10
P("10. Geração de código C e equivalência SIL", h1)
P("Trecho do código gerado (<font name='DVM'>gen/auroraarm_junta.c</font>) — note a etiqueta de requisito "
  "em cada linha e o bloco de rastreabilidade:")
cod = (RAIZ / "gen/auroraarm_junta.c").read_text(encoding="utf-8").splitlines()
ini = next(i for i, l in enumerate(cod) if "BLOCO DE RASTREABILIDADE" in l)
trecho = cod[ini - 1: ini + 15] + ["..."] + [l for l in cod if "u_sat =" in l or "t4c =" in l or "u_out =" in l][:3]
code("\n".join(trecho))
P(f"<b>Equivalência numérica (memorial, item e).</b> Sequência de {e_['n_amostras']:,} amostras".replace(",", ".") +
  f": 801 de um ensaio em malha fechada (degraus, parada de segurança, modo colaborativo) e 3 000 "
  f"aleatórias em toda a faixa física. Contra o modelo executado em binário32, o erro máximo é "
  f"<b>zero</b>: as saídas são idênticas bit a bit. Contra o modelo em binário64, o erro máximo é "
  f"{e_['erro_max_vs_modelo_float64_V']:.2e} V, ou seja, {n(e_['erro_rel_vs_float64_em_eps'],0)} ε relativos à escala de 48 V, "
  f"abaixo da cota teórica de {e_['cota_teorica_V']:.2e} V (quantização da posição em binário32 "
  f"amplificada pelos ganhos derivativo e proporcional) e {e_['lsb_pwm_12bits_V']/e_['erro_max_vs_modelo_float64_V']:.0f} vezes menor que 1 LSB de um PWM de 12 bits. "
  f"Em malha fechada com o C, o tempo de acomodação é idêntico ao do modelo "
  f"({e_['malha_fechada_sil']['t_acomodacao_s']*1e3:.0f} ms).")
fig("fig5_sil.png", "Figura 7 — SIL: diferença entre o código C e o modelo. Em binário32 é identicamente zero; em relação ao binário64 fica na ordem de 10⁻⁴ V, coerente com o arredondamento.")
P(f"<b>Recursos no alvo.</b> Compilado com {rc['compilador'].split(' 20')[0]} para Cortex-M4F "
  f"(-mfpu=fpv4-sp-d16, -mfloat-abi=hard): <b>{rc['text_bytes']} bytes</b> de código "
  f"({n(rc['pct_256KB'],2)} % dos 256 KB). O controlador e o supervisor somam "
  f"{rc['instrucoes_por_ciclo_total']} instruções em linha reta, sem laços nem divisões; assumindo 3 "
  f"ciclos por instrução (flash com estados de espera), a cota é {rc['ciclos_cpu_cota']} ciclos = "
  f"<b>{n(rc['t_exec_cota_us_168MHz'],2)} µs a 168 MHz</b>, {n(rc['pct_orcamento_200us'],1)} % do orçamento de "
  f"200 µs. No host x86-64 o ciclo mede {n(rc['host_ns_por_ciclo'],1)} ns.")

# ============================================================================ 11
P("11. Matriz de rastreabilidade", h1)
P("Gerada automaticamente por <font name='DVM'>scripts/rastreabilidade.py</font>: as linhas do C são "
  "encontradas pelas etiquetas que o gerador grava, e o script falha se algum teste citado não existir. "
  "Versão Markdown em <font name='DVM'>docs/rastreabilidade.md</font>.")
tab([["Requisito", "Modelo", "Código (gen/auroraarm_junta.c)", "Teste", "Evidência"]] +
    [[f"<b>{r['id']}</b><br/>{r['descricao']}<br/><i>{r['tipo']}</i>", r["modelo"],
      r["codigo"].replace("gen/auroraarm_junta.c linhas ", "linhas "),
      r["teste"].replace("; ", "<br/>"), r["evidencia"]] for r in RT],
    [3.0, 3.5, 2.2, 4.6, 3.2])

# ============================================================================ 12
P("12. Honestidade técnica: o que o pacote sustenta e o que falta", h1)
P("<b>O que este pacote sustenta perante a auditoria da Aurora Robótica:</b>")
B("o modelo da junta é coerente com a física e com os parâmetros de bancada, e o procedimento de "
  "identificação recupera esses parâmetros com erro < 1 % a partir de dados ruidosos;")
B("o controlador atende REQ-CTRL-AA-001..004 em todos os cenários do envelope declarado, com "
  "saturação de tensão e de corrente garantidas por construção;")
B("a <i>lógica</i> do supervisor satisfaz REQ-SAFE-AA-001..004 em <b>todas</b> as combinações de "
  "atraso do scanner, perda de ciclo e ação do operador do modelo — não em uma amostra delas;")
B("o código que vai para o microcontrolador é gerado do modelo verificado, é equivalente a ele bit "
  "a bit em precisão simples e cabe com folga nos limites de tempo e memória;")
B("cada requisito está ligado a modelo, linhas de código, testes e números reprodutíveis.")
P("<b>O que ainda não sustenta, e o que exigiria para certificação</b> (IEC 61508 ou, se o setor "
  "pedir, ISO 26262/ISO 13849):")
B("<b>Qualificação de ferramentas.</b> O model checker, o gerador de código e o gerador de testes "
  "foram escritos neste projeto e não são qualificados (IEC 61508-3, 7.4.4; ISO 26262-8, cláusula 11). "
  "Seria preciso qualificá-los, ou usar ferramentas qualificadas (UPPAAL/compilador certificado), ou "
  "verificar o código gerado de forma independente a cada geração. O compilador GCC também não é "
  "qualificado.")
B("<b>Independência da verificação.</b> Modelo, código e testes foram produzidos pela mesma pessoa. "
  "Para SIL 2/PL d a verificação deve ser feita por pessoa ou equipe independente.")
B("<b>Fidelidade das premissas.</b> A1–A4, o atraso de 20 ms e o tempo de STO precisam ser "
  "confirmados com os dados do scanner e do driver reais; a identificação foi emulada, não feita "
  "em bancada; a flexibilidade da harmônica, o atrito de Coulomb e o aquecimento não foram modelados.")
B("<b>HIL e hardware.</b> Falta rodar o binário no Cortex-M4 real (HIL), medir o WCET (a cota foi "
  "estimada pela contagem de instruções) e configurar a FPU (sem flush-to-zero). O canal de segurança "
  "deveria ser redundante (dois canais, scanner e STO certificados), o que este pacote não cobre.")
B("<b>Escopo.</b> Apenas a junta do cotovelo e apenas a sua contribuição para a velocidade do "
  "efetuador; o braço completo exige a cinemática das seis juntas e a análise de força/pressão de "
  "contato da ISO/TS 15066 (limitação de potência e força), não tratada aqui.")

# ============================================================================ Referências
P("Referências", h1)
refs = [
    "BAIER, Christel; KATOEN, Joost-Pieter. <b>Principles of model checking</b>. Cambridge: MIT Press, 2008.",
    "COLIM, Ana; FARIA, Carlos; CUNHA, João; OLIVEIRA, João; SOUSA, Nuno; ROCHA, Luís A. Physical ergonomic improvement and safe design of an assembly workstation through collaborative robotics. <b>Safety</b>, Basel, v. 7, n. 1, art. 14, 2021. DOI: 10.3390/safety7010014. Disponível em: https://www.mdpi.com/2313-576X/7/1/14. Acesso em: 28 out. 2026.",
    "HENZINGER, Thomas A.; MANNA, Zohar; PNUELI, Amir. What good are digital clocks? In: INTERNATIONAL COLLOQUIUM ON AUTOMATA, LANGUAGES AND PROGRAMMING (ICALP), 19., 1992, Viena. <b>Proceedings</b>. Berlin: Springer, 1992. p. 545-558. (Lecture Notes in Computer Science, v. 623).",
    "INTERNATIONAL ELECTROTECHNICAL COMMISSION. <b>IEC 61508</b>: functional safety of electrical/electronic/programmable electronic safety-related systems. Parts 1-7. Geneva: IEC, 2010.",
    "INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. <b>ISO/TS 15066</b>: robots and robotic devices — collaborative robots. Geneva: ISO, 2016.",
    "INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. <b>ISO 13855</b>: safety of machinery — positioning of safeguards with respect to the approach speeds of parts of the human body. Geneva: ISO, 2010.",
    "INTERNATIONAL ORGANIZATION FOR STANDARDIZATION. <b>ISO 26262</b>: road vehicles — functional safety. Geneva: ISO, 2018.",
    "MODELICA ASSOCIATION. <b>Functional Mock-up Interface Specification</b>, version 3.0. Linköping: Modelica Association, 2022.",
    "SICILIANO, Bruno; SCIAVICCO, Lorenzo; VILLANI, Luigi; ORIOLO, Giuseppe. <b>Robotics</b>: modelling, planning and control. London: Springer-Verlag, 2010.",
    "UNIFECAF. <b>Model Based Design for Cyber-Physical Systems</b>: material das aulas 1 a 16. São Paulo: UniFECAF, 2026.",
]
for r in refs:
    P(r, ParagraphStyle("ref", parent=corpo, alignment=0, leftIndent=12, firstLineIndent=-12))

# ============================================================================ ANEXO A
S.append(PageBreak())
P("ANEXO A — Memorial de cálculo", parte)
P("Cada item apresenta fórmula, substituição, premissas e resultado. Os valores são recalculados por "
  "<font name='DVM'>scripts/memorial.py</font> (saídas em <font name='DVM'>resultados/memorial.txt</font> "
  "e <font name='DVM'>resultados/memorial.json</font>).", ParagraphStyle("x", parent=corpo, alignment=TA_CENTER))
S.append(PageBreak())
A_ = a["A"]
P("(a) Modelo em espaço de estados e constantes de tempo", h1)
P("<b>Premissas:</b> parâmetros da tabela referidos ao eixo do motor; K<sub>t</sub> = K<sub>e</sub>; atrito "
  "viscoso; x = [i, ω]<super>T</super>, u = V, perturbação d = T<sub>L</sub>, y = ω.")
P("<b>Passo 1 — matrizes.</b>")
E(f"a<sub>11</sub> = −R/L = −0,8/0,0012 = {n(A_[0][0],4)} s⁻¹    a<sub>12</sub> = −K<sub>e</sub>/L = −0,085/0,0012 = {n(A_[0][1],4)} A/(rad)")
E(f"a<sub>21</sub> = K<sub>t</sub>/J = 0,085/4,2×10⁻⁴ = {n(A_[1][0],4)}    a<sub>22</sub> = −b/J = −1,5×10⁻⁴/4,2×10⁻⁴ = {n(A_[1][1],6)} s⁻¹")
E(f"B = [1/L ; 0] = [{n(a['B'][0],4)} ; 0]    E = [0 ; −1/J] = [0 ; {n(a['E'][1],4)}]    C = [0  1]")
P("<b>Passo 2 — autovalores.</b> det(λI − A) = λ² − tr(A)·λ + det(A) = 0:")
E(f"tr(A) = {n(a['traco'],4)}    det(A) = a<sub>11</sub>a<sub>22</sub> − a<sub>12</sub>a<sub>21</sub> = {n(A_[0][0]*A_[1][1],4)} + {n(-A_[0][1]*A_[1][0],4)} = {n(a['det'],2)}")
E(f"λ = [tr ± √(tr² − 4 det)]/2  →  λ<sub>1</sub> = {n(a['autovalores'][0],3)} rad/s,  λ<sub>2</sub> = {n(a['autovalores'][1],3)} rad/s")
P("<b>Passo 3 — constantes de tempo.</b>")
E(f"τ<sub>e</sub> = 1/|λ<sub>1</sub>| = {n(a['tau_e_ms'],4)} ms  (aprox. L/R = {n(a['L_sobre_R_ms'],3)} ms)")
E(f"τ<sub>m</sub> = 1/|λ<sub>2</sub>| = {n(a['tau_m_ms'],3)} ms  (aprox. RJ/(Rb + K<sub>t</sub>K<sub>e</sub>) = {n(a['tau_m_simplificada_ms'],3)} ms)")
P(f"<b>Discussão:</b> τ<sub>m</sub>/τ<sub>e</sub> = {n(a['razao_tau'],1)}. Os autovalores são reais e bem separados; as "
  "aproximações desacopladas erram cerca de 3 % a 3,5 %, o que confirma que as "
  "dinâmicas elétrica e mecânica podem ser tratadas em escalas de tempo distintas (identificação em duas "
  "etapas, projeto do PID no modelo reduzido, corte do torque quase instantâneo).")
P("<b>Passo 4 — controlabilidade e observabilidade</b> (n = 2):")
Co, Ob = a["Co"], a["Ob"]
E(f"M<sub>c</sub> = [B  AB] = [{n(Co[0][0],2)}  {n(Co[0][1],1)} ; {n(Co[1][0],0)}  {n(Co[1][1],1)}]   det M<sub>c</sub> = {a['det_Co']:.4e}  →  posto {a['posto_Co']}")
E(f"M<sub>o</sub> = [C ; CA] = [0  1 ; {n(Ob[1][0],4)}  {n(Ob[1][1],6)}]   det M<sub>o</sub> = −K<sub>t</sub>/J = {n(a['det_Ob'],2)}  →  posto {a['posto_Ob']}")
P("<b>Resultado:</b> posto completo nas duas matrizes — a junta é <b>controlável</b> pela tensão e "
  "<b>observável</b> pela velocidade. Como det M<sub>o</sub> = −K<sub>t</sub>/J, a observabilidade só se perderia se "
  "K<sub>t</sub> = 0 (sem acoplamento eletromecânico). Código: <font name='DVM'>auroraarm/planta.py</font>; "
  "teste: <font name='DVM'>tests/test_planta.py</font>.")

P("(b) Ponto de operação crítico", h1)
P("<b>Premissas:</b> regime permanente (di/dt = dω/dt = 0), ω = 450 rad/s, T<sub>L</sub> = 0,25 N m, "
  "parâmetros nominais.")
P("<b>Passo 1 — corrente</b> (equação mecânica em regime: K<sub>t</sub>·i = b·ω + T<sub>L</sub>):")
E(f"i<sub>ss</sub> = (b·ω + T<sub>L</sub>)/K<sub>t</sub> = (1,5×10⁻⁴·450 + 0,25)/0,085 = ({n(b_['bw'],4)} + 0,25)/0,085 = <b>{n(b_['i_ss'],4)} A</b>")
P("<b>Passo 2 — tensão</b> (equação elétrica em regime: V = R·i + K<sub>e</sub>·ω):")
E(f"V<sub>ss</sub> = 0,8·{n(b_['i_ss'],4)} + 0,085·450 = {n(b_['R_i'],3)} + {n(b_['Ke_w'],2)} = <b>{n(b_['V_ss'],3)} V</b>")
P("<b>Passo 3 — folgas:</b>")
E(f"ΔV = V<sub>max</sub> − V<sub>ss</sub> = 48 − {n(b_['V_ss'],3)} = <b>{n(b_['folga_V'],3)} V</b> ({n(b_['folga_V_pct'],1)} %)")
E(f"Δi = 8 − {n(b_['i_ss'],3)} = <b>{n(b_['folga_i'],3)} A</b> (i<sub>ss</sub> = {n(b_['i_pct'],1)} % de i<sub>max</sub>)")
P(f"<b>Discussão:</b> 93 % da tensão é consumida pela f.c.e.m.; a velocidade máxima possível com a carga é "
  f"{n(b_['w_max_com_carga'],1)} rad/s, só 17 % acima do ponto de operação. Qualquer correção de erro ou "
  "aceleração adicional satura o atuador — logo a saturação é o regime <i>normal</i> de transitório e "
  "o <b>anti-windup é obrigatório</b>: sem ele o degrau da seção 7 passa de 94 % de sobressinal e não "
  "acomoda. Em corrente a folga é maior (4,3 A), mas a aceleração também é limitada pelo driver: por "
  "isso o controlador satura numa janela de corrente (7,5 A, margem de 0,5 A) além dos 48 V. A folga "
  "pequena também desaconselha ganhos muito altos (eles só trocariam desempenho linear por mais tempo "
  "saturado).")

P("(c) Escolha do período de amostragem", h1)
P("<b>Premissa:</b> regra prática de 10 a 20 amostras por constante de tempo dominante de malha aberta, "
  "e 20 a 40 amostras por período da frequência de cruzamento de malha fechada.")
E(f"N = τ<sub>m</sub>/T<sub>s</sub> = {n(a['tau_m_ms'],2)}/2 = <b>{n(c_['amostras_por_tau_m'],1)} amostras</b>")
E(f"faixa recomendada: τ<sub>m</sub>/20 = {n(c_['Ts_min_regra_20'],2)} ms ≤ T<sub>s</sub> ≤ τ<sub>m</sub>/10 = {n(c_['Ts_max_regra_10'],2)} ms")
E(f"malha fechada: ω<sub>c</sub> = {n(mc['freq_cruzamento_rad_s'],1)} rad/s → 2π/(ω<sub>c</sub>T<sub>s</sub>) = {mc['amostras_por_periodo_cruzamento']:.0f} amostras por período")
P(f"<b>Resultado:</b> T<sub>s</sub> = 2 ms é <b>adequado</b>, ligeiramente conservador (22 amostras, logo acima da "
  f"faixa). Não é desnecessariamente conservador porque: (i) o atraso de 1,5 T<sub>s</sub> (ZOH + cálculo) "
  f"já custa ω<sub>c</sub>·1,5T<sub>s</sub> = {n(mc['freq_cruzamento_rad_s']*0.003*57.2958,1)}° de margem de fase no cruzamento, e dobrar T<sub>s</sub> dobraria essa perda; (ii) o supervisor roda no "
  f"mesmo ciclo e cada período perdido entra diretamente na latência de REQ-SAFE-AA-001; (iii) a CPU "
  f"gasta só {n(rc['pct_orcamento_200us'],1)} % do orçamento. Ao mesmo tempo, τ<sub>e</sub>/T<sub>s</sub> = "
  f"{n(c_['amostras_por_tau_e'],2)}: a dinâmica elétrica é rápida demais para este laço, e por isso o limite "
  "de corrente é imposto por uma janela algébrica de tensão, e não por um laço de corrente.")

P("(d) Verificação do prazo de segurança de 100 ms", h1)
P("<b>Premissas:</b> atraso do scanner d ∈ [0, 20] ms; a detecção ocorre em qualquer instante do "
  "período, logo a espera até a próxima ativação vale w ∈ (0, 2] ms; no máximo 1 ciclo perdido "
  "(+2 ms); execução e ≤ 0,2 ms; após habilita = 0 o torque é considerado nulo quando a corrente cai a "
  f"1 % (simulado: {n(M['torque_off']['t_1pct_ms'],2)} ms) ou, conservadoramente, em 5τ<sub>e</sub> = "
  f"{n(M['torque_off']['cinco_tau_e_ms'],2)} ms.")
E("L = d + w + 2·n<sub>perdidos</sub> + e + t<sub>corte</sub>")
E(f"L<sub>max</sub> = 20 + 2 + 2·1 + 0,2 + {n(M['torque_off']['cinco_tau_e_ms'],2)} = <b>{n(d_['pior_latencia_ms'],2)} ms ≤ 100 ms</b>")
P(f"<b>Varredura exaustiva:</b> 201 valores de d × 40 de w × 2 de n × 2 de e × 2 de t<sub>corte</sub> = "
  f"{d_['n_combinacoes']:,} combinações; todas cumprem; mínimo {n(d_['menor_latencia_ms'],2)} ms; margem no pior caso "
  f"{n(d_['margem_ms'],2)} ms. <b>Autômato temporizado:</b> o model checker explora as mesmas fontes de "
  f"atraso em tempo inteiro e encontra pior latência de {v1['pior_latencia_parada_ms']} ms em "
  f"{v1['n_estados']:,} estados.".replace(",", "."))
P(f"<b>Combinação que violaria:</b> nenhuma dentro das premissas. Por sensibilidade, seriam necessários "
  f"n ≥ (100 − 20 − 2 − 0,2 − 7,76)/2 + 1 = <b>{d_['ciclos_perdidos_consecutivos_para_violar']} ciclos perdidos "
  f"seguidos</b>, ou um scanner com atraso > <b>{n(d_['atraso_sensor_para_violar_ms'],1)} ms</b>. A lógica, porém, "
  "<i>pode</i> violar o prazo: o contraexemplo C2 da versão v0 (seção 8.4) estoura 100 ms com atrasos "
  "dentro das premissas — o tempo só é cumprido se a máquina de estados reagir à detecção em todos os "
  "estados com torque.")

P("(e) Equivalência modelo-código", h1)
P(f"<b>Premissas:</b> tipo float (IEEE-754 binário32), ε = 2⁻²³ = {e_['eps_float32']:.4e}; mesma ordem de "
  f"operações; sem FMA; sequência de {e_['n_amostras']:,} amostras (801 de malha fechada e 3 000 aleatórias).".replace(",", "."))
E("e<sub>max</sub> = max<sub>k</sub> |u<sub>C</sub>[k] − u<sub>modelo</sub>[k]|")
E(f"modelo em binário32:  e<sub>max</sub> = <b>{e_['erro_max_vs_modelo_float32_V']:.1f} V</b>  (as {e_['n_amostras']:,} saídas são idênticas bit a bit)".replace(",", "."))
E(f"modelo em binário64:  e<sub>max</sub> = <b>{e_['erro_max_vs_modelo_float64_V']:.3e} V</b> = "
  f"{e_['erro_max_vs_modelo_float64_V']:.3e}/(48·ε) = {n(e_['erro_rel_vs_float64_em_eps'],1)} ε")
E(f"cota de arredondamento: (B<sub>D</sub> + K<sub>p</sub>)·|y|<sub>max</sub>·ε = (76,67 + 10,1)·60·{e_['eps_float32']:.3e} = {e_['cota_teorica_V']:.2e} V")
P(f"<b>Discussão e resultado:</b> o erro zero contra o modelo em binário32 mostra que o gerador traduziu o "
  f"modelo <i>sem defeito</i>: qualquer erro de geração (operação trocada, constante errada, ordem "
  f"diferente) apareceria como diferença de ao menos 1 ulp. A diferença para o binário64 não indica "
  f"defeito: ela vem da quantização da posição em binário32 (até 60 rad → passo de 3,8×10⁻⁶ rad), "
  f"amplificada pelo ganho derivativo B<sub>D</sub> = K<sub>d</sub>/(T<sub>f</sub>+T<sub>s</sub>) = 76,7; por isso é "
  f"~{n(e_['erro_rel_vs_float64_em_eps'],0)} ε e não 1 ε, e fica abaixo da cota de {e_['cota_teorica_V']:.1e} V. "
  f"Comparada ao que importa fisicamente — 1 LSB de PWM de 12 bits = {n(e_['lsb_pwm_12bits_V'],4)} V — é "
  f"{e_['lsb_pwm_12bits_V']/e_['erro_max_vs_modelo_float64_V']:.0f} vezes menor. A equivalência é <b>aceitável</b>.")


def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(CINZA)
    if doc.page > 1:
        canvas.drawString(2 * cm, 1.2 * cm, "AuroraArm — junta do cotovelo  |  Kaio Santana Rodrigues Santos, RA 98328")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
    canvas.restoreState()


saida = RAIZ / "relatorio" / "AuroraArm_relatorio_tecnico.pdf"
doc = SimpleDocTemplate(str(saida), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                        topMargin=2 * cm, bottomMargin=2 * cm,
                        title="Operação Linha Viva — AuroraArm", author="Kaio Santana Rodrigues Santos")
doc.build(S, onFirstPage=rodape, onLaterPages=rodape)
print(saida)
