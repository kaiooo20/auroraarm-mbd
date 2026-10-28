"""Memorial de cálculo — itens (a) a (e) + evidências complementares.

Uso:  python scripts/memorial.py
Saídas: resultados/memorial.json (números citados no relatório) e
        resultados/memorial.txt  (versão legível, passo a passo).
Cada número do relatório vem deste arquivo; nada é digitado à mão no PDF.
"""
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from auroraarm import codegen, sil, supervisor as sup, verificacao as ver   # noqa: E402
from auroraarm import controlador as ctl, identificacao as idf, planta as pl  # noqa: E402
from auroraarm.parametros import Parametros                                 # noqa: E402

OUT = RAIZ / "resultados"
OUT.mkdir(exist_ok=True)
p = Parametros.carregar()
M = {}          # tudo que vai para o JSON
txt = []        # memorial legível


def linha(s=""):
    txt.append(s)
    print(s)


# =========================================================================== (a)
A, B, E, C, D = pl.matrizes(p)
lam = pl.autovalores(p)
tau_e, tau_m = pl.constantes_de_tempo(p)
Co = pl.matriz_controlabilidade(A, B)
Ob = pl.matriz_observabilidade(A, C)
traco, det = np.trace(A), np.linalg.det(A)
M["a"] = {
    "A": A.tolist(), "B": B.ravel().tolist(), "E": E.ravel().tolist(), "C": C.ravel().tolist(),
    "traco": traco, "det": det, "autovalores": lam.tolist(),
    "tau_e_ms": tau_e * 1e3, "tau_m_ms": tau_m * 1e3, "razao_tau": tau_m / tau_e,
    "L_sobre_R_ms": p.L / p.R * 1e3,
    "tau_m_simplificada_ms": p.R * p.J / (p.R * p.b + p.Kt * p.Ke) * 1e3,
    "Co": Co.tolist(), "posto_Co": int(np.linalg.matrix_rank(Co)), "det_Co": float(np.linalg.det(Co)),
    "Ob": Ob.tolist(), "posto_Ob": int(np.linalg.matrix_rank(Ob)), "det_Ob": float(np.linalg.det(Ob)),
}
a = M["a"]
linha("(a) MODELO EM ESPAÇO DE ESTADOS E CONSTANTES DE TEMPO")
linha("    x = [i, w]^T, u = V, d = T_L, y = w")
linha(f"    A = [[-R/L, -Ke/L], [Kt/J, -b/J]] = [[{A[0,0]:.4f}, {A[0,1]:.4f}], [{A[1,0]:.4f}, {A[1,1]:.6f}]]")
linha(f"    B = [1/L, 0]^T = [{B[0,0]:.4f}, 0]^T   E = [0, -1/J]^T = [0, {E[1,0]:.4f}]^T   C = [0 1]")
linha(f"    det(sI - A) = s^2 + {-traco:.4f} s + {det:.2f} = 0")
linha(f"    autovalores: {lam[0]:.3f} e {lam[1]:.3f} rad/s")
linha(f"    tau_e = 1/|l1| = {a['tau_e_ms']:.4f} ms   (L/R = {a['L_sobre_R_ms']:.3f} ms)")
linha(f"    tau_m = 1/|l2| = {a['tau_m_ms']:.3f} ms   (R J/(R b + Kt Ke) = {a['tau_m_simplificada_ms']:.3f} ms)")
linha(f"    separação de escalas: tau_m / tau_e = {a['razao_tau']:.1f}")
linha(f"    Co = [B AB]: posto {a['posto_Co']}, det = {a['det_Co']:.4g}  -> controlável")
linha(f"    Ob = [C; CA]: posto {a['posto_Ob']}, det = {a['det_Ob']:.4g}  -> observável")

# =========================================================================== (b)
i_ss, V_ss = pl.ponto_de_operacao(p)
M["b"] = {"bw": p.b * p.w_op, "i_ss": i_ss, "Ke_w": p.Ke * p.w_op, "R_i": p.R * i_ss,
          "V_ss": V_ss, "folga_V": p.V_max - V_ss, "folga_V_pct": 100 * (p.V_max - V_ss) / p.V_max,
          "i_pct": 100 * i_ss / p.i_max, "folga_i": p.i_max - i_ss,
          "w_max_vazio": (p.V_max - p.R * (p.b * 0) ) / p.Ke,
          "w_max_com_carga": (p.V_max * p.Kt - p.R * p.T_carga) / (p.Kt * p.Ke + p.R * p.b),
          "aceleracao_max_rad_s2": (p.Kt * ctl.I_LIM - p.T_carga - p.b * p.w_op) / p.J}
b_ = M["b"]
linha("\n(b) PONTO DE OPERAÇÃO CRÍTICO (regime: di/dt = dw/dt = 0)")
linha(f"    i = (b w + T_L)/Kt = ({p.b:g}*{p.w_op:g} + {p.T_carga:g})/{p.Kt:g} = {i_ss:.4f} A ({b_['i_pct']:.1f} % de i_max)")
linha(f"    V = R i + Ke w = {p.R:g}*{i_ss:.4f} + {p.Ke:g}*{p.w_op:g} = {b_['R_i']:.3f} + {b_['Ke_w']:.2f} = {V_ss:.3f} V")
linha(f"    folga de tensão = {p.V_max:g} - {V_ss:.3f} = {b_['folga_V']:.3f} V ({b_['folga_V_pct']:.1f} %)")
linha(f"    folga de corrente = {p.i_max:g} - {i_ss:.3f} = {b_['folga_i']:.3f} A")
linha(f"    velocidade máxima possível com a carga: {b_['w_max_com_carga']:.1f} rad/s")

# =========================================================================== (c)
amostras = tau_m / p.Ts
M["c"] = {"amostras_por_tau_m": amostras, "amostras_por_tau_e": tau_e / p.Ts,
          "Ts_max_regra_10": tau_m / 10 * 1e3, "Ts_min_regra_20": tau_m / 20 * 1e3,
          "fs_Hz": 1 / p.Ts, "banda_malha_fechada_Hz": None}
linha("\n(c) PERÍODO DE AMOSTRAGEM")
linha(f"    N = tau_m / Ts = {tau_m*1e3:.2f} / {p.Ts*1e3:.0f} = {amostras:.1f} amostras por constante de tempo")
linha(f"    faixa usual de 10 a 20 amostras/tau -> Ts entre {M['c']['Ts_min_regra_20']:.2f} e {M['c']['Ts_max_regra_10']:.2f} ms")
linha(f"    tau_e / Ts = {tau_e / p.Ts:.2f}: a dinâmica elétrica NÃO é resolvida pelo laço de posição")

# =========================================================================== controle
cen = []
for amp in (10.0, -10.0, 2.0):
    for tl in (p.T_carga, 0.0, -p.T_carga):
        m, _ = ctl.ensaio_degrau(p, amp, T_carga=tl)
        cen.append({"amplitude_rad_motor": amp, "T_carga": tl, **{k: float(v) for k, v in m.items()}})
m_nom, res_nom = ctl.ensaio_degrau(p, 10.0)
m_sem_aw, _ = ctl.ensaio_degrau(p, 10.0, coef=ctl.coeficientes(p, {"Kaw": 0.0}))
m_big, _ = ctl.ensaio_degrau(p, 15.0, T_carga=-p.T_carga)
den = p.R * p.b + p.Kt * p.Ke
M["controle"] = {
    "ganhos": ctl.GANHOS_PADRAO, "I_LIM": ctl.I_LIM, "degrau_junta_rad": ctl.DEGRAU_JUNTA,
    "K_reduzido": p.Kt / den, "tau_reduzido_ms": p.R * p.J / den * 1e3,
    "nominal": {k: float(v) for k, v in m_nom.items()},
    "cenarios": cen,
    "pior_sobressinal_pct": max(c_["sobressinal_pct"] for c_ in cen),
    "pior_t_acomodacao_s": max(c_["t_acomodacao_s"] for c_ in cen),
    "pior_erro_regime_rad": max(c_["erro_regime_rad"] for c_ in cen),
    "pior_i_A": max(c_["i_max_abs"] for c_ in cen),
    "pior_V": max(c_["V_max_abs"] for c_ in cen),
    "sem_antiwindup": {k: float(v) for k, v in m_sem_aw.items()},
    "fora_do_envelope_15rad_carga_neg": {k: float(v) for k, v in m_big.items()},
}
mc = M["controle"]
linha("\nCONTROLADOR (degrau de 0,1 rad na junta = 10 rad no motor)")
linha(f"    ganhos: {ctl.GANHOS_PADRAO}")
linha(f"    pior caso nos 9 cenários: OS = {mc['pior_sobressinal_pct']:.2f} %, ts = {mc['pior_t_acomodacao_s']*1e3:.0f} ms, "
      f"|i| = {mc['pior_i_A']:.2f} A, |V| = {mc['pior_V']:.2f} V")
linha(f"    sem anti-windup: OS = {m_sem_aw['sobressinal_pct']:.1f} %, ts = {m_sem_aw['t_acomodacao_s']}")

# --- discretização / margem do laço linear (modelo reduzido + ZOH)
from scipy import signal  # noqa: E402
g = ctl.GANHOS_PADRAO
# malha aberta contínua linear (sem saturação) para margens: C(s) G(s) com G de 3 estados
Ap, Bp, _, Cp = pl.matrizes_posicao(p)
w = np.logspace(0, 4, 4000)
s_ = 1j * w
G = np.array([(Cp @ np.linalg.solve(si * np.eye(3) - Ap, Bp))[0, 0] for si in s_])
Cc = g["Kp"] + g["Ki"] / s_ + g["Kd"] * s_ / (g["Tf"] * s_ + 1)
Lw = Cc * G * np.exp(-s_ * p.Ts * 1.5)          # ZOH (Ts/2) + atraso de cálculo (Ts)
idx = np.argmin(np.abs(np.abs(Lw) - 1))
wc = w[idx]
mf = 180 + np.degrees(np.angle(Lw[idx]))
M["controle"]["freq_cruzamento_rad_s"] = float(wc)
M["controle"]["margem_fase_graus"] = float(mf)
M["controle"]["amostras_por_periodo_cruzamento"] = float(2 * math.pi / wc / p.Ts)
M["c"]["banda_malha_fechada_Hz"] = float(wc / 2 / math.pi)
linha(f"    laço linear: cruzamento {wc:.1f} rad/s ({wc/2/math.pi:.1f} Hz), margem de fase {mf:.1f} graus "
      f"(com atraso de 1,5 Ts), {2*math.pi/wc/p.Ts:.0f} amostras por período de cruzamento")

# =========================================================================== identificação
r_id = idf.rodar(p)
r_id.pop("_validacao")
M["identificacao"] = r_id
linha("\nIDENTIFICAÇÃO (ensaio emulado com ruído, validação cruzada)")
for k in r_id["nominal"]:
    linha(f"    {k:3s} nominal {r_id['nominal'][k]:.4g}  estimado {r_id['identificado'][k]:.4g}  erro {r_id['erro_pct'][k]:+.2f} %")
linha(f"    ajuste NRMSE na validação: w {r_id['fit_w_pct']:.1f} %, i {r_id['fit_i_pct']:.1f} %")

# =========================================================================== desligamento do torque
simj = pl.SimuladorJunta(p, sub=200)
simj.reset([0.0, i_ss, p.w_op])
t_off, tt = None, 0.0
h = p.Ts / 200
for k in range(10):
    for _ in range(200):
        simj.x = simj.Ad_off @ simj.x + simj.Ed_off * p.T_carga
        tt += h
        if t_off is None and abs(simj.x[1]) < 0.01 * i_ss:
            t_off = tt
M["torque_off"] = {"t_1pct_ms": t_off * 1e3, "cinco_tau_e_ms": 5 * tau_e * 1e3,
                   "modelo_verificacao_ms": ver.T_OFF}

# =========================================================================== (d)
d_vals = np.round(np.arange(0, 20.0001, 0.1), 4)            # atraso do sensor [ms]
fase = np.round(np.arange(0.05, 2.0001, 0.05), 4)          # espera até a próxima ativação [ms]
perdas = (0, 1)
t_exec = (0.0, 0.2)
t_corte = (M["torque_off"]["t_1pct_ms"], 5 * tau_e * 1e3)
lat = []
for d in d_vals:
    for f in fase:
        for n in perdas:
            for ex in t_exec:
                for tc in t_corte:
                    lat.append((d + f + 2 * n + ex + tc, d, f, n, ex, tc))
lat = np.array(lat)
pior = lat[lat[:, 0].argmax()]
# análise de sensibilidade: o que seria preciso para violar?
base = 20 + 2 + 0.2 + 5 * tau_e * 1e3
n_viol = math.floor((100 - base) / 2) + 1
d_viol = 100 - (2 + 2 + 0.2 + 5 * tau_e * 1e3)
M["d"] = {
    "n_combinacoes": int(lat.shape[0]),
    "pior_latencia_ms": float(pior[0]),
    "pior_combinacao": {"atraso_sensor_ms": float(pior[1]), "espera_ativacao_ms": float(pior[2]),
                        "ciclos_perdidos": int(pior[3]), "execucao_ms": float(pior[4]),
                        "corte_torque_ms": float(pior[5])},
    "menor_latencia_ms": float(lat[:, 0].min()),
    "todas_cumprem": bool((lat[:, 0] <= 100).all()),
    "margem_ms": float(100 - pior[0]),
    "ciclos_perdidos_consecutivos_para_violar": int(n_viol),
    "atraso_sensor_para_violar_ms": float(d_viol),
}
linha("\n(d) PRAZO DE 100 ms (REQ-SAFE-AA-001)")
linha(f"    latência = atraso_sensor + espera_ativação + 2*ciclos_perdidos + execução + corte_torque")
linha(f"    pior caso = 20 + 2 + 2*1 + 0,2 + {5*tau_e*1e3:.2f} = {pior[0]:.2f} ms  ({lat.shape[0]} combinações)")
linha(f"    todas <= 100 ms: {M['d']['todas_cumprem']}   margem = {M['d']['margem_ms']:.2f} ms")
linha(f"    para violar seriam precisos {n_viol} ciclos perdidos seguidos ou atraso de sensor > {d_viol:.1f} ms")

# --- model checking
r1 = ver.verificar(sup.TRANSICOES_V1, "v1")
r0 = ver.verificar(sup.TRANSICOES_V0, "v0")
M["verificacao"] = {
    "v1": {k: getattr(r1, k) for k in ("n_estados", "n_transicoes", "p1_ok", "p2_ok", "p3_ok",
                                       "p4_ok", "pior_latencia_parada_ms", "pior_resposta_zona_ms")},
    "v0": {"n_estados": r0.n_estados, "propriedade_violada": r0.propriedade_violada,
           "tamanho_contraexemplo_ms": len(r0.contraexemplo)},
    "premissas": {"T_SENSOR": ver.T_SENSOR, "T_CICLO": ver.T_CICLO, "T_APLICA": ver.T_APLICA,
                  "T_OFF": ver.T_OFF, "T_TRAVA": ver.T_TRAVA, "K_RET": ver.K_RET,
                  "PRAZO": ver.PRAZO, "PRAZO_ZONA": ver.PRAZO_ZONA},
}
(OUT / "contraexemplo_v0.txt").write_text(
    f"Contraexemplo do supervisor v0 — {r0.propriedade_violada}\n"
    f"(gerado por auroraarm/verificacao.py; traço de menor comprimento, busca em largura)\n\n"
    + ver.formatar_contraexemplo(r0, max_linhas=10_000) + "\n", encoding="utf-8")
linha(f"    model checking v1: {r1.n_estados} estados, {r1.n_transicoes} transições; "
      f"P1..P4 = {r1.p1_ok}, {r1.p2_ok}, {r1.p3_ok}, {r1.p4_ok}; pior latência {r1.pior_latencia_parada_ms} ms")
linha(f"    model checking v0: viola {r0.propriedade_violada} (traço de {len(r0.contraexemplo)} ms)")

# =========================================================================== REQ-SAFE-AA-004 físico
w_lim = p.N * p.v_colab_max_m_s / p.braco_m
coef = ctl.coeficientes(p)
t_sw = 1.0


def trajetoria(t, a=800.0, w=p.w_op):
    """Trajetória de pega-e-solta: acelera a 800 rad/s^2 até 450 rad/s e mantém."""
    t1 = w / a
    return 0.5 * a * t * t if t < t1 else 0.5 * a * t1 * t1 + w * (t - t1)


res_c = ctl.simular_malha_fechada(p, coef, trajetoria, t_final=t_sw + 1.2,
                                  lim_vel=lambda t: t >= t_sw)
k_sw = int(round(t_sw / p.Ts))
w_after = np.abs(res_c.w[k_sw:])
k_ok = np.argmax(w_after <= w_lim)
t_desac = k_ok * p.Ts
v_pico_depois = float(w_after[k_ok:].max() / p.N * p.braco_m)
t_resposta_total = ver.T_SENSOR / 1e3 + 2 * p.Ts + 0.5e-3 + t_desac
K_iso = 1.6   # m/s, velocidade de aproximação (ISO 13855)
np.savez(OUT / "colaborativo.npz", t=res_c.t, w=res_c.w, t_sw=t_sw, w_lim=w_lim)
M["req_safe_004"] = {
    "w_motor_lim_rad_s": w_lim, "w_ref_colab_rad_s": coef["DMAX_COLAB"] / p.Ts,
    "w_antes_rad_s": float(np.abs(res_c.w[k_sw - 1])),
    "v_antes_m_s": float(np.abs(res_c.w[k_sw - 1]) / p.N * p.braco_m),
    "t_desaceleracao_ms": t_desac * 1e3, "v_max_depois_m_s": v_pico_depois,
    "w_regime_colab_rad_s": float(np.abs(res_c.w[-50:]).mean()),
    "a_colab_rad_s2": ctl.A_COLAB, "i_pico_desac_A": float(res_c.i_pico[k_sw:].max()),
    "t_resposta_total_ms": t_resposta_total * 1e3,
    "distancia_campo_alerta_m": K_iso * t_resposta_total,
}
rs = M["req_safe_004"]
linha("\nREQ-SAFE-AA-004 (parte física)")
linha(f"    limite: w_motor <= N v/r = {p.N:g}*{p.v_colab_max_m_s}/{p.braco_m} = {w_lim:.1f} rad/s; referência colaborativa {rs['w_ref_colab_rad_s']:.1f} rad/s")
linha(f"    de {rs['w_antes_rad_s']:.0f} rad/s ({rs['v_antes_m_s']:.2f} m/s) até o limite em {rs['t_desaceleracao_ms']:.0f} ms; "
      f"depois, v máx = {rs['v_max_depois_m_s']*1000:.0f} mm/s")
linha(f"    campo de alerta mínimo (K = 1,6 m/s, ISO 13855): {rs['distancia_campo_alerta_m']:.2f} m")

# =========================================================================== (e)
gerado = codegen.gerar(p)
eq = sil.equivalencia(p)
uc, u32, u64 = eq.pop("_series")
np.savez(OUT / "sil_series.npz", c=uc, m32=u32, m64=u64)
# limite teórico do arredondamento dominante: quantização da entrada y em binário32
y_max = 60.0
cota = coef["BD"] * y_max * eq["eps_float32"] + coef["KP"] * y_max * eq["eps_float32"]
eq["cota_teorica_V"] = float(cota)
eq["lsb_pwm_12bits_V"] = 2 * p.V_max / 4096
M["e"] = eq
# SIL em malha fechada: o C gerado controlando a planta
m_sil, _ = ctl.ensaio_degrau(p, 10.0, controlador=sil.ControladorC())
M["e"]["malha_fechada_sil"] = {k: float(v) for k, v in m_sil.items()}
M["e"]["malha_fechada_modelo"] = {k: float(v) for k, v in m_nom.items()}
M["codigo"] = gerado
linha("\n(e) EQUIVALÊNCIA MODELO x CÓDIGO C GERADO (SIL)")
linha(f"    {eq['n_amostras']} amostras; erro máx vs modelo float32 = {eq['erro_max_vs_modelo_float32_V']:.3g} V "
      f"(bit a bit idênticos: {eq['bits_iguais_vs_float32']})")
linha(f"    erro máx vs modelo float64 = {eq['erro_max_vs_modelo_float64_V']:.3e} V "
      f"= {eq['erro_rel_vs_float64_em_eps']:.1f} eps relativos a {eq['escala_saida_V']:.0f} V; cota teórica {cota:.2e} V")

# =========================================================================== recursos (alvo M4)
recursos = {}
arm = shutil.which("arm-none-eabi-gcc")
tmp = Path(tempfile.mkdtemp())
if arm:
    obj = tmp / "m4.o"
    subprocess.run([arm, "-mcpu=cortex-m4", "-mthumb", "-mfloat-abi=hard", "-mfpu=fpv4-sp-d16",
                    "-O2", "-ffp-contract=off", "-std=c99", "-c",
                    str(RAIZ / "gen/auroraarm_junta.c"), "-o", str(obj)], check=True)
    size = subprocess.run(["arm-none-eabi-size", str(obj)], capture_output=True, text=True).stdout
    text = int(size.splitlines()[1].split()[0])
    dis = subprocess.run(["arm-none-eabi-objdump", "-d", str(obj)], capture_output=True, text=True).stdout
    cont, atual = {}, None
    for ln in dis.splitlines():
        if ln.endswith(">:"):
            atual = ln.split("<")[1][:-2]
            cont[atual] = 0
        elif atual and ln.strip() and ln.strip()[0].isalnum() and ":" in ln[:12]:
            cont[atual] += 1
    instr = cont.get("aa_ctrl_passo", 0) + cont.get("aa_sup_passo", 0)
    ciclos_pior = instr * 3            # pior caso conservador: 3 ciclos/instrução (wait states)
    recursos = {"compilador": subprocess.run([arm, "--version"], capture_output=True,
                                             text=True).stdout.splitlines()[0],
                "text_bytes": text, "pct_256KB": 100 * text / p.memoria_programa_bytes,
                "instrucoes": cont, "instrucoes_por_ciclo_total": instr,
                "ciclos_cpu_cota": ciclos_pior,
                "t_exec_cota_us_168MHz": ciclos_pior / 168.0,
                "pct_orcamento_200us": 100 * ciclos_pior / 168.0 / 200.0}
gcc = shutil.which("gcc")
if gcc:
    exe = tmp / "bench"
    subprocess.run([gcc, "-O2", "-ffp-contract=off", str(RAIZ / "sil/bench.c"),
                    str(RAIZ / "gen/auroraarm_junta.c"), "-o", str(exe)], check=True)
    recursos["host_ns_por_ciclo"] = float(subprocess.run([str(exe)], capture_output=True,
                                                          text=True).stdout)
M["recursos"] = recursos
if recursos:
    linha("\nRECURSOS NO ALVO (Cortex-M4F)")
    linha(f"    .text = {recursos.get('text_bytes')} bytes ({recursos.get('pct_256KB', 0):.2f} % de 256 KB)")
    linha(f"    {recursos.get('instrucoes_por_ciclo_total')} instruções em linha reta (sem laços) -> "
          f"cota {recursos.get('t_exec_cota_us_168MHz', 0):.2f} us a 168 MHz "
          f"({recursos.get('pct_orcamento_200us', 0):.2f} % do orçamento)")
    linha(f"    host x86-64: {recursos.get('host_ns_por_ciclo')} ns por ciclo (controlador + supervisor)")


def _limpa(o):
    if isinstance(o, dict):
        return {str(k): _limpa(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [_limpa(v) for v in o]
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return str(o)
    return o


(OUT / "memorial.json").write_text(json.dumps(_limpa(M), indent=2, ensure_ascii=False), encoding="utf-8")
(OUT / "memorial.txt").write_text("\n".join(txt) + "\n", encoding="utf-8")
print("\nresultados/memorial.json e resultados/memorial.txt gravados")
