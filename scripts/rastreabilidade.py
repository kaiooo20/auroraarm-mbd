"""Monta a matriz de rastreabilidade requisito -> modelo -> código -> teste -> evidência.

As linhas do código C são encontradas AUTOMATICAMENTE pelas etiquetas de requisito que o
gerador escreve em cada linha; os nomes dos testes são conferidos contra os arquivos.
Uso: python scripts/rastreabilidade.py   (depois de scripts/memorial.py)
Saídas: docs/rastreabilidade.md e resultados/rastreabilidade.json
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
M = json.loads((RAIZ / "resultados" / "memorial.json").read_text(encoding="utf-8"))
C = (RAIZ / "gen" / "auroraarm_junta.c").read_text(encoding="utf-8").splitlines()

mc, d, v1, e, rs = M["controle"], M["d"], M["verificacao"]["v1"], M["e"], M["req_safe_004"]

REQS = [
    ("REQ-CTRL-AA-001", "Erro de posição nulo em regime (degrau)", "Desempenho",
     "controlador.py: PASSOS e, t5, t8, i_new (ação integral)",
     "tests/test_controlador.py::test_req_ctrl_001_a_004",
     f"pior erro {mc['pior_erro_regime_rad']:.1e} rad em 9 cenários"),
    ("REQ-CTRL-AA-002", "Sobressinal <= 8 %", "Desempenho",
     "controlador.py: br, e_p, p_term (beta = 0,55), d_new (D na medição)",
     "tests/test_controlador.py::test_req_ctrl_001_a_004; ::test_robustez_inercia",
     f"pior sobressinal {mc['pior_sobressinal_pct']:.2f} %"),
    ("REQ-CTRL-AA-003", "Tempo de acomodação <= 300 ms", "Desempenho",
     "controlador.py: ganhos (scripts/sintonia.py) + anti-windup t6, t7",
     "tests/test_controlador.py::test_req_ctrl_001_a_004; ::test_anti_windup_e_necessario",
     f"pior ts {mc['pior_t_acomodacao_s']*1e3:.0f} ms"),
    ("REQ-CTRL-AA-004", "|V| <= 48 V e |i| <= 8 A sempre", "Desempenho (restrição)",
     "controlador.py: fcem, v_hi0, v_lo0, t4..u_sat (janela de corrente + barramento)",
     "tests/test_controlador.py::test_saturacao_nunca_passa_de_48V_mesmo_com_entrada_absurda",
     f"pior |i| {mc['pior_i_A']:.2f} A; |V| <= 48 V com entradas aleatórias"),
    ("REQ-SAFE-AA-001", "Mão < 500 mm -> torque zero em <= 100 ms", "Segurança (com prazo)",
     "supervisor.py: T1, T3, T6, T8; verificacao.py: P1; controlador.py: u_out",
     "tests/test_verificacao.py::test_v1_satisfaz_todas_as_propriedades; ::test_v0_tem_contraexemplo_de_prazo",
     f"pior latência {d['pior_latencia_ms']:.2f} ms (varredura) / {v1['pior_latencia_parada_ms']} ms (model checking)"),
    ("REQ-SAFE-AA-002", "Após parada, só religa com rearme explícito", "Segurança",
     "supervisor.py: T5, T7 (única saída para estado com torque); verificacao.py: P2",
     "tests/test_verificacao.py::test_checador_detecta_religamento_sem_rearme; tests/test_supervisor_mbt.py::test_invariantes_em_passeio_aleatorio",
     f"P2 verdadeira em {v1['n_estados']} estados"),
    ("REQ-SAFE-AA-003", "Mão removida + rearme -> retorna à trajetória", "Vivacidade",
     "supervisor.py: T7, T9; controlador.py: r_prev/v_prev (retomada sem salto); verificacao.py: P3",
     "tests/test_verificacao.py::test_v1_satisfaz_todas_as_propriedades; ::test_checador_detecta_violacao_de_vivacidade",
     "P3 verdadeira (nenhum ciclo com obrigação pendente)"),
    ("REQ-SAFE-AA-004", "Velocidade do efetuador <= 250 mm/s na zona colaborativa", "Segurança",
     "supervisor.py: T2, T4, saída lim_vel; controlador.py: dr..r (limitador vel./acel.); verificacao.py: P4",
     "tests/test_controlador.py::test_modo_colaborativo_limita_velocidade; tests/test_supervisor_mbt.py::test_invariantes_em_passeio_aleatorio",
     f"regime {rs['w_regime_colab_rad_s']/100*0.35*1000:.0f} mm/s; desaceleração {rs['t_desaceleracao_ms']:.0f} ms; campo de alerta {rs['distancia_campo_alerta_m']:.2f} m"),
]


def linhas_c(req):
    alvo = req.replace("REQ-", "")
    num = alvo.split("-")[-1]
    prefixo = "-".join(alvo.split("-")[:-1])
    ls = []
    for i, ln in enumerate(C, start=1):
        if "/*" not in ln or "BLOCO" in ln:
            continue
        for tag in re.findall(r"REQ-(" + prefixo + r")-([0-9./]+(?:\.\.[0-9]+)?)", ln):
            nums = tag[1]
            ok = num in nums.split("/") or (".." in nums and int(nums.split("..")[0]) <= int(num) <= int(nums.split("..")[1]))
            if ok and i > 25:
                ls.append(i)
    return ls


def faixas(ls):
    if not ls:
        return "-"
    out, ini, ant = [], ls[0], ls[0]
    for x in ls[1:] + [None]:
        if x is not None and x == ant + 1:
            ant = x
            continue
        out.append(f"{ini}" if ini == ant else f"{ini}-{ant}")
        if x is not None:
            ini = ant = x
    return ", ".join(out)


testes_txt = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "tests").glob("test_*.py"))
linhas = []
for rid, desc, tipo, modelo, teste, evid in REQS:
    for nome in re.findall(r"::(\w+)", teste):
        assert f"def {nome}(" in testes_txt, f"teste inexistente: {nome}"
    linhas.append({"id": rid, "descricao": desc, "tipo": tipo, "modelo": modelo,
                   "codigo": f"gen/auroraarm_junta.c linhas {faixas(linhas_c(rid))}",
                   "teste": teste, "evidencia": evid})

(RAIZ / "resultados" / "rastreabilidade.json").write_text(
    json.dumps(linhas, indent=2, ensure_ascii=False), encoding="utf-8")
md = ["# Matriz de rastreabilidade", "",
      "Gerada por `scripts/rastreabilidade.py` a partir de `resultados/memorial.json` e das "
      "etiquetas de requisito escritas pelo gerador em `gen/auroraarm_junta.c`.", "",
      "| Requisito | Tipo | Modelo | Código | Teste | Evidência |", "|---|---|---|---|---|---|"]
for l in linhas:
    md.append(f"| **{l['id']}** {l['descricao']} | {l['tipo']} | {l['modelo']} | {l['codigo']} | {l['teste']} | {l['evidencia']} |")
(RAIZ / "docs" / "rastreabilidade.md").write_text("\n".join(md) + "\n", encoding="utf-8")
for l in linhas:
    print(l["id"], "|", l["codigo"])
