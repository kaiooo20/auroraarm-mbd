"""Gera as figuras do relatório em resultados/figuras/ (PNG, 200 dpi).

Uso:  python scripts/figuras.py      (rodar depois de scripts/memorial.py)
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from auroraarm import controlador as ctl, identificacao as idf, supervisor as sup  # noqa: E402
from auroraarm import verificacao as ver  # noqa: E402
from auroraarm.parametros import Parametros  # noqa: E402

FIG = RAIZ / "resultados" / "figuras"
FIG.mkdir(parents=True, exist_ok=True)
M = json.loads((RAIZ / "resultados" / "memorial.json").read_text(encoding="utf-8"))
p = Parametros.carregar()

# paleta categórica validada (ordem fixa) + tinta de texto neutra
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
TXT, MUTED, GRID = "#2b2b2b", "#6b6b6b", "#e4e4e0"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
    "axes.labelcolor": TXT, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.8,
    "legend.frameon": False, "axes.titleweight": "bold", "axes.titlesize": 10,
    "axes.titlelocation": "left",
})


def salvar(fig, nome):
    fig.tight_layout()
    fig.savefig(FIG / nome, dpi=200)
    plt.close(fig)
    print("figura:", nome)


# ---------------------------------------------------------------- 1. degrau
_, r = ctl.ensaio_degrau(p, 10.0)
_, r0 = ctl.ensaio_degrau(p, 10.0, coef=ctl.coeficientes(p, {"Kaw": 0.0}))
t0 = 0.3
fig, ax = plt.subplots(3, 1, figsize=(7, 6.4), sharex=True)
tt = (r.t - t0) * 1e3
ax[0].plot(tt, r.theta / p.N, color=S1, label="com anti-windup (projeto)")
ax[0].plot(tt, r0.theta / p.N, color=S2, label="sem anti-windup")
ax[0].axhline(0.1 * 1.08, color=MUTED, ls="--", lw=1)
ax[0].text(595, 0.1 * 1.08 + 0.004, "limite de sobressinal (+8 %)", ha="right", va="bottom", color=MUTED, fontsize=8)
ax[0].axvline(300, color=MUTED, ls=":", lw=1)
ax[0].text(305, 0.02, "300 ms", color=MUTED, fontsize=8)
ax[0].set_ylabel("posição da junta [rad]")
ax[0].set_title("Degrau de 0,1 rad na junta com carga de 0,25 N m")
ax[0].legend(loc="lower right")
ax[0].set_ylim(-0.01, 0.2)
ax[1].plot(tt, r.V, color=S1)
ax[1].plot(tt, r0.V, color=S2)
ax[1].set_ylabel("tensão [V]")
ax[2].plot(tt, r.i_pico, color=S1)
ax[2].plot(tt, r0.i_pico, color=S2)
ax[2].axhline(8, color=MUTED, ls="--", lw=1)
ax[2].text(595, 8.15, "i_max = 8 A", ha="right", va="bottom", color=MUTED, fontsize=8)
ax[2].set_ylim(-0.3, 9.2)
ax[2].set_ylabel("|corrente| pico [A]")
ax[2].set_xlabel("tempo após o degrau [ms]")
ax[2].set_xlim(-20, 600)
salvar(fig, "fig1_degrau.png")

# ---------------------------------------------------------------- 2. identificação
r_id = idf.rodar(p)
val, i_hat, w_hat = r_id["_validacao"]
fig, ax = plt.subplots(2, 1, figsize=(7, 4.6), sharex=True)
k = val.t <= 0.6
ax[0].plot(val.t[k] * 1e3, val.w[k], color=MUTED, lw=0.8, label="medido (com ruído)")
ax[0].plot(val.t[k] * 1e3, w_hat[k], color=S1, lw=1.4, label="modelo identificado (simulação livre)")
ax[0].set_ylabel("w [rad/s]")
ax[0].set_title(f"Validação cruzada da identificação  —  ajuste NRMSE: w {r_id['fit_w_pct']:.1f} %, i {r_id['fit_i_pct']:.1f} %")
ax[0].legend(loc="upper right", fontsize=8)
ax[1].plot(val.t[k] * 1e3, val.V[k], color=S2, lw=1)
ax[1].set_ylabel("V (PRBS) [V]")
ax[1].set_xlabel("tempo [ms]")
salvar(fig, "fig2_identificacao.png")

# ---------------------------------------------------------------- 3. colaborativo
d = np.load(RAIZ / "resultados" / "colaborativo.npz")
fig, ax = plt.subplots(figsize=(7, 3.2))
v = np.abs(d["w"]) / p.N * p.braco_m * 1e3
ax.plot((d["t"] - d["t_sw"]) * 1e3, v, color=S1, label="velocidade do efetuador")
ax.axhline(250, color=S2, ls="--", lw=1.2, label="limite REQ-SAFE-AA-004 (250 mm/s)")
ax.axvline(0, color=MUTED, ls=":", lw=1)
ax.text(8, 700, "lim_vel = 1", color=MUTED, fontsize=8)
td = M["req_safe_004"]["t_desaceleracao_ms"]
ax.axvline(td, color=MUTED, ls=":", lw=1)
ax.text(td + 8, 700, f"{td:.0f} ms", color=MUTED, fontsize=8)
ax.set_xlim(-300, 1200)
ax.set_xlabel("tempo após a entrada na zona colaborativa [ms]")
ax.set_ylabel("v [mm/s]")
ax.set_title("Redução para velocidade colaborativa a partir do ponto crítico (450 rad/s)")
ax.legend(loc="center right", fontsize=8, bbox_to_anchor=(1.0, 0.62), frameon=True, facecolor="white", edgecolor="white")
salvar(fig, "fig3_colaborativo.png")

# ---------------------------------------------------------------- 4. latência (d)
dd = M["d"]["pior_combinacao"]
comp = [("atraso do sensor", dd["atraso_sensor_ms"], S1),
        ("espera da próxima ativação", dd["espera_ativacao_ms"], S3),
        ("ciclo perdido (jitter)", 2 * dd["ciclos_perdidos"], S4),
        ("execução", dd["execucao_ms"], MUTED),
        ("corte do torque (5 tau_e)", dd["corte_torque_ms"], S2)]
fig, ax = plt.subplots(figsize=(7, 3.0))
x = 0
for nome, val_, cor in comp:
    ax.barh(0, val_, left=x, color=cor, edgecolor="white", linewidth=2, height=0.5,
            label=f"{nome}: {val_:.2f} ms")
    x += val_
ax.axvline(100, color=TXT, lw=1.4)
ax.text(98.5, -0.18, "prazo\n100 ms", ha="right", va="center", color=TXT, fontsize=8)
ax.text(x + 1.5, 0, f"{x:.2f} ms", va="center", color=TXT, fontsize=9, fontweight="bold")
ax.set_xlim(0, 105)
ax.set_ylim(-0.4, 0.4)
ax.set_yticks([])
ax.set_xlabel("latência do pior caso [ms]")
ax.set_title(f"Pior caso entre {M['d']['n_combinacoes']} combinações (margem {M['d']['margem_ms']:.1f} ms)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=2, fontsize=7.5)
ax.grid(axis="y", visible=False)
salvar(fig, "fig4_latencia.png")

# ---------------------------------------------------------------- 5. SIL
s = np.load(RAIZ / "resultados" / "sil_series.npz")
fig, ax = plt.subplots(2, 1, figsize=(7, 4.2), sharex=True)
n = np.arange(s["c"].size)
ax[0].plot(n[:801], s["c"][:801], color=S1, lw=1.0)
ax[0].scatter(n[801:], s["c"][801:], color=S1, s=1.5, linewidths=0)
ax[0].set_ylabel("u do código C [V]")
ax[0].set_title("Equivalência SIL: código C gerado x modelo de referência")
ax[0].axvline(801, color=MUTED, ls=":", lw=1)
ax[0].text(820, 40, "entradas aleatórias", color=MUTED, fontsize=8)
ax[0].text(20, 40, "malha fechada", color=MUTED, fontsize=8)
ax[1].plot(n, s["c"] - s["m64"], color=S2, lw=0.7, label="C - modelo float64")
ax[1].plot(n, s["c"] - s["m32"], color=S1, lw=1.4, label="C - modelo float32 (identicamente zero)")
ax[1].set_ylabel("diferença [V]")
ax[1].set_xlabel("amostra")
ax[1].legend(loc="lower left", fontsize=8)
salvar(fig, "fig5_sil.png")

# ---------------------------------------------------------------- 6. contraexemplo v0
r0v = ver.verificar(sup.TRANSICOES_V0, "v0")
ce = r0v.contraexemplo
tt = np.arange(1, len(ce) + 1)
mao = [c[0][0] for c in ce]
sens = [c[2][1] for c in ce]
est = [sup.ESTADOS.index(c[2][4]) for c in ce]
torque = [1 if c[2][10] == 0 else (0.5 if c[2][10] == 1 else 0) for c in ce]
fig, ax = plt.subplots(4, 1, figsize=(7, 5), sharex=True)
ax[0].step(tt, mao, where="post", color=S2)
ax[0].set_ylabel("mão\nno campo")
ax[0].set_title("Contraexemplo C2 (supervisor v0, sem T8)")
ax[1].step(tt, sens, where="post", color=S3)
ax[1].set_ylabel("saída do\nscanner")
ax[2].step(tt, est, where="post", color=S1)
ax[2].set_yticks(range(len(sup.ESTADOS)))
ax[2].set_yticklabels([e.replace("_REARME", "") for e in sup.ESTADOS], fontsize=7)
ax[2].set_ylabel("estado")
ax[3].step(tt, torque, where="post", color=S4)
ax[3].set_yticks([0, 0.5, 1])
ax[3].set_yticklabels(["zero", "decaindo", "ligado"], fontsize=7)
ax[3].set_xlabel("tempo [ms]")
for a_ in ax[:2]:
    a_.set_yticks([0, 1])
ent = next(i for i, c in enumerate(ce) if c[0][0] == 1 and i > 2) + 1
ax[0].annotate("mão volta durante o atraso do scanner", xy=(ent, 1), xytext=(ent + 10, 0.45),
               fontsize=7.5, color=TXT, arrowprops=dict(arrowstyle="->", color=MUTED))
ax[3].axvline(ent + 100, color=S2, ls="--", lw=1)
ax[3].text(ent + 99, 0.75, "100 ms", ha="right", color=S2, fontsize=8)
salvar(fig, "fig6_contraexemplo.png")

# ---------------------------------------------------------------- 7. diagrama do supervisor
dot = shutil.which("dot")
if dot:
    cores = {"NORMAL": "#cde2fb", "REDUZIDA": "#b7d3f6", "PARADA": "#f7c9b5",
             "AGUARDA_REARME": "#fbe2b0", "RETOMADA": "#c6eedc"}
    linhas = ["digraph G {", 'rankdir=TB; bgcolor="white"; nodesep=0.6; ranksep=0.55;',
              'node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=11, color="#6b6b6b"];',
              'edge [fontname="DejaVu Sans", fontsize=9, color="#6b6b6b"];',
              'inicio [shape=point, width=0.12, color="#2b2b2b"];', f"inicio -> {sup.ESTADO_INICIAL};"]
    for e in sup.ESTADOS:
        h, l = sup.SAIDAS[e]
        linhas.append(f'{e} [label="{e}\\nhabilita={h}  lim_vel={l}", fillcolor="{cores[e]}"];')
    for tid, o, g, dst, req in sup.TRANSICOES:
        cond = " & ".join(f"{k}={v}" for k, v in g.items())
        cor = "#d03b3b" if tid == "T8" else "#6b6b6b"
        largura = 2.2 if tid == "T8" else 1.0
        linhas.append(f'{o} -> {dst} [label="{tid}: {cond}", color="{cor}", penwidth={largura}, fontcolor="{cor if tid == "T8" else "#2b2b2b"}"];')
    linhas.append("}")
    src = FIG / "fig0_supervisor.dot"
    src.write_text("\n".join(linhas), encoding="utf-8")
    subprocess.run([dot, "-Tpng", "-Gdpi=200", str(src), "-o", str(FIG / "fig0_supervisor.png")], check=True)
    print("figura: fig0_supervisor.png")
