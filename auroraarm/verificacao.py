"""Verificação formal exaustiva do supervisor de segurança (Unidade 3).

Model checker explícito escrito para este projeto. Ele explora TODOS os estados
alcançáveis do produto síncrono de cinco autômatos temporizados, em tempo discreto de
1 ms (semântica de relógios digitais: para autômatos temporizados *fechados*, isto é,
com guardas <= e >=, a alcançabilidade em tempo inteiro coincide com a de tempo denso —
Henzinger, Manna e Pnueli, 1992; ver também Baier e Katoen, cap. 9):

  1. AMBIENTE   — a mão do operador entra/sai do campo de 500 mm a qualquer instante;
                  o operador entra/sai da zona colaborativa e aperta o rearme livremente.
  2. SENSOR     — scanner com atraso de detecção NÃO determinístico em [0, 20] ms.
  3. RTOS       — tarefa periódica de 2 ms que pode PERDER um ciclo por jitter (nunca
                  dois seguidos); a saída do ciclo é aplicada 1 ms depois do disparo
                  (cobre com folga o orçamento de 200 us de execução).
  4. SUPERVISOR — a tabela de transições de `auroraarm.supervisor` (v0 ou v1).
  5. DRIVER     — ao receber habilita = 0, o torque cai a ~0 em T_OFF = 8 ms
                  (>= 5 tau_e = 7,76 ms: corrente abaixo de 0,7 % do valor inicial).

Propriedades (fórmulas em LTL/TCTL e o monitor que as verifica):
  P1  REQ-SAFE-AA-001 (segurança com prazo)
        AG( mao_real -> (torque_zero R<=100ms ... ) )  — na forma de invariante:
        "nunca a mão fica mais de 100 ms contínuos no campo com torque não nulo"
        monitor: relógio `co` zera na entrada da mão, conta enquanto ela fica e o torque
        não é nulo; violação se co > 100.
  P2  REQ-SAFE-AA-002 (segurança)
        AG( estado in {PARADA, AGUARDA} and not rearme -> AX not habilita )
        monitor: transição do supervisor que religa o torque sem rearme = violação.
  P3  REQ-SAFE-AA-003 (vivacidade)
        AG( rearme and not mao -> AF (retomou or mao) )      ("leads-to")
        monitor: bit `pend`; violação se existir CICLO alcançável só com pend = 1
        (um caminho infinito em que a obrigação nunca é cumprida).
  P4  REQ-SAFE-AA-004 (segurança, parte lógica)
        AG( zona and habilita -> AF<=6ms lim_vel )
        monitor: relógio `cz`; a parte física (desacelerar até 250 mm/s) é verificada por
        simulação em `scripts/memorial.py`.

Premissas de modelagem (declaradas no relatório):
  A1 a mão, depois de entrar no campo, permanece nele até ser detectada (uma intrusão
     mais curta que o tempo de resposta do scanner não é garantida pelo fabricante);
  A2 o retorno à trajetória, quando não interrompido, termina em no máximo K_RET = 60
     ciclos (120 ms) no modelo. O valor precisa ser MAIOR que o prazo de 100 ms: com
     K_RET pequeno a retomada termina "sozinha" antes do prazo e o defeito da v0 fica
     escondido (lição registrada no relatório). Na v1 a duração da retomada não altera P1,
     porque T8 trata a mão em qualquer instante da retomada;
  A3 a perda de ciclo é de no máximo 1 ciclo consecutivo (dado do enunciado);
  A4 a saída do scanner, uma vez acionada, fica acionada por pelo menos T_TRAVA = 6 ms
     (> 2 ciclos + 1 ciclo perdido), mesmo que a mão saia antes, para que TODA detecção
     chegue ao supervisor (scanners comerciais têm tempo mínimo de saída desligada).

Histórico de contraexemplos (documentado no relatório, seção 7):
  C1 (espúrio, de formalização): a 1a versão do monitor mantinha a obrigação do prazo
     mesmo depois que a mão saía e o operador rearmava; o traço mostrava o braço operando
     normalmente, sem ninguém no campo, e acusava violação. Corrigido o MONITOR.
  C2 (real, v0 do supervisor): sem a transição T8, a mão que volta durante a RETOMADA
     é ignorada até a retomada terminar -> torque ligado com a mão no campo > 100 ms.
     Corrigido o SUPERVISOR (v1).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from . import supervisor as sup

T_SENSOR = 20      # ms, atraso máximo de detecção
T_CICLO = 2        # ms, período do laço
T_APLICA = 1       # ms, da ativação da tarefa até a saída valer no driver (>= 200 us)
T_TRAVA = 6        # ms, tempo mínimo de saída acionada do scanner (premissa A4)
T_OFF = 8          # ms, habilita=0 -> torque ~ 0  (>= 5 tau_e)
PRAZO = 100        # ms, REQ-SAFE-AA-001
K_RET = 60         # ciclos (120 ms > prazo de 100 ms), duração máxima modelada da retomada (A2)
PRAZO_ZONA = 6     # ms, resposta lógica ao campo de alerta (P4)

HAB_ESTADOS = {e for e, (h, _) in sup.SAIDAS.items() if h}

# Índices do vetor de estado (tupla, para ser "hashable")
#  0 mao_real  1 sens  2 cs  3 zona  4 sup  5 cc  6 perdeu  7 pend_out
#  8 hab_out   9 lim_out 10 act  11 ca  12 co  13 pend  14 cr  15 cz
ON, DEC, OFF = 0, 1, 2


@dataclass
class Resultado:
    versao: str
    n_estados: int
    n_transicoes: int
    p1_ok: bool
    p2_ok: bool
    p3_ok: bool
    p4_ok: bool
    pior_latencia_parada_ms: int
    pior_resposta_zona_ms: int
    contraexemplo: list = field(default_factory=list)
    propriedade_violada: str | None = None
    transicoes_cobertas: set = field(default_factory=set)
    estados_cobertos: set = field(default_factory=set)


def estado_inicial():
    hab, lim = sup.SAIDAS[sup.ESTADO_INICIAL]
    return (0, 0, 0, 1, sup.ESTADO_INICIAL, 0, 0, None, hab, lim, ON, 0, -1, 0, 0, 0)


def sucessores(s, transicoes):
    """Gera (rótulo, próximo estado, eventos) para todas as escolhas não determinísticas."""
    (mao, sens, cs, zona, est, cc, perdeu, pend_out, hab_out, lim_out,
     act, ca, co, pend, cr, cz) = s

    # (a) saída calculada no ciclo anterior chega ao driver
    if pend_out is not None:
        hab_out, lim_out = pend_out
        pend_out = None
    if hab_out == 1:
        act, ca = ON, 0
    elif act == ON:
        act, ca = DEC, 0
    # (b) decaimento do torque com o driver desabilitado
    if act == DEC:
        ca += 1
        if ca >= T_OFF:
            act, ca = OFF, 0

    opcoes_mao = [mao] if (mao == 1 and sens == 0) else [0, 1]       # premissa A1
    for mao2 in opcoes_mao:
        for zona2 in (0, 1):
            # (c) sensor com atraso não determinístico e saída (OSSD) travada por T_TRAVA
            #     com sens = 1, `cs` passa a contar o tempo desde a detecção
            if sens == 1:
                cl = min(cs + 1, T_TRAVA)
                opc_sensor = [(1, cl)] if (mao2 == 1 or cl < T_TRAVA) else [(0, 0)]
            elif mao2 == 0:
                opc_sensor = [(0, 0)]
            else:
                cs2 = cs + 1 if mao == 1 else 0
                opc_sensor = [(1, 0)] + ([(0, cs2)] if cs2 < T_SENSOR else [])
            for sens2, cs2 in opc_sensor:
                cc2 = cc + 1
                if cc2 < T_CICLO:
                    opc_sched = [("espera", None, None)]
                else:
                    opc_sched = []
                    for rearme in (0, 1):
                        if est == "RETOMADA":
                            cr2 = min(cr + 1, K_RET)
                            opc_cheg = [0, 1] if cr2 < K_RET else [1]
                        else:
                            cr2, opc_cheg = 0, [0]
                        for chegou in opc_cheg:
                            opc_sched.append(("executa", (rearme, chegou), cr2))
                    if perdeu == 0:
                        opc_sched.append(("perde", None, None))
                for acao, ent, cr2 in opc_sched:
                    ev = {}
                    est2, perdeu2, pend_out2, pend2 = est, perdeu, pend_out, pend
                    cr3 = cr
                    cc3 = cc2 if cc2 < T_CICLO else 0
                    if acao == "perde":
                        perdeu2 = 1
                    elif acao == "executa":
                        rearme, chegou = ent
                        perdeu2 = 0
                        entradas = {"mao": sens2, "zona": zona2, "rearme": rearme, "chegou": chegou}
                        est2, tid = sup.proximo_estado(est, entradas, transicoes)
                        ev["tid"] = tid
                        ev["entradas"] = entradas
                        pend_out2 = sup.SAIDAS[est2]
                        # P2: torque religado sem rearme?
                        if est in ("PARADA", "AGUARDA_REARME") and est2 in HAB_ESTADOS and rearme == 0:
                            ev["viola_p2"] = True
                        # P3: premissa do leads-to
                        if est == "AGUARDA_REARME" and rearme == 1 and sens2 == 0:
                            pend2 = 1
                        if tid == "T9":
                            pend2 = 0
                        cr3 = cr2 if est2 == "RETOMADA" else 0
                    if mao2 == 1:
                        pend2 = 0          # mão voltou: parar é o comportamento correto
                    # (d) monitor de prazo P1
                    #     co = há quanto tempo a mão está CONTINUAMENTE no campo com torque não nulo
                    co2 = co
                    if co2 >= 0:
                        co2 += 1
                    elif mao2 == 1 and act != OFF:
                        co2 = 0
                    if co2 >= 0 and act == OFF:
                        ev["latencia"] = co2
                        co2 = -1
                    elif co2 >= 0 and mao2 == 0:
                        co2 = -1            # a mão saiu antes: o perigo deixou de existir
                    if co2 > PRAZO:
                        ev["viola_p1"] = True
                        co2 = PRAZO + 1
                    # (e) monitor P4
                    cz2 = cz + 1 if (zona2 == 1 and hab_out == 1 and lim_out == 0) else 0
                    if cz2 > PRAZO_ZONA:
                        ev["viola_p4"] = True
                        cz2 = PRAZO_ZONA + 1
                    ev["cz"] = cz2
                    rotulo = (mao2, zona2, sens2, acao, ent)
                    s2 = (mao2, sens2, cs2, zona2, est2, cc3, perdeu2, pend_out2, hab_out,
                          lim_out, act, ca, co2, pend2, cr3, cz2)
                    yield rotulo, s2, ev


def verificar(transicoes=sup.TRANSICOES, versao="v1", parar_na_violacao=True) -> Resultado:
    s0 = estado_inicial()
    pai = {s0: None}
    fila = deque([s0])
    n_trans = 0
    pior_lat = 0
    pior_cz = 0
    violacao = None
    cobertas, estados_sup = set(), {s0[4]}
    arestas_pend = {}
    while fila:
        s = fila.popleft()
        for rot, s2, ev in sucessores(s, transicoes):
            n_trans += 1
            if "tid" in ev and ev["tid"]:
                cobertas.add(ev["tid"])
            estados_sup.add(s2[4])
            pior_lat = max(pior_lat, ev.get("latencia", 0))
            pior_cz = max(pior_cz, ev["cz"])
            if s2 not in pai:
                pai[s2] = (s, rot, ev)
                fila.append(s2)
            if s[13] == 1 and s2[13] == 1:
                arestas_pend.setdefault(s, []).append(s2)
            for prop in ("viola_p1", "viola_p2", "viola_p4"):
                if ev.get(prop) and violacao is None:
                    # nó especial: garante que o traço termine exatamente nesta aresta
                    pai[("viol", s2)] = (s, rot, ev)
                    violacao = (prop, ("viol", s2))
        if violacao and parar_na_violacao:
            break

    res = Resultado(versao, len(pai), n_trans, True, True, True, True, pior_lat, pior_cz,
                    transicoes_cobertas=cobertas, estados_cobertos=estados_sup)
    if violacao:
        prop, alvo = violacao
        setattr(res, {"viola_p1": "p1_ok", "viola_p2": "p2_ok", "viola_p4": "p4_ok"}[prop], False)
        res.propriedade_violada = {"viola_p1": "P1 (REQ-SAFE-AA-001)",
                                   "viola_p2": "P2 (REQ-SAFE-AA-002)",
                                   "viola_p4": "P4 (REQ-SAFE-AA-004)"}[prop]
        res.contraexemplo = reconstruir(pai, alvo)
        return res
    # P3: existe ciclo formado só por estados com obrigação pendente?
    ciclo = achar_ciclo(arestas_pend)
    if ciclo:
        res.p3_ok = False
        res.propriedade_violada = "P3 (REQ-SAFE-AA-003)"
        res.contraexemplo = reconstruir(pai, ciclo[0]) + [("(ciclo)", c) for c in ciclo[1:]]
    return res


def reconstruir(pai, alvo):
    passos = []
    s = alvo
    while pai.get(s) is not None:
        anterior, rot, ev = pai[s]
        passos.append((rot, ev, s[1] if isinstance(s[0], str) else s))
        s = anterior
    passos.reverse()
    return passos


def achar_ciclo(arestas):
    """Algoritmo de Kahn no subgrafo: sobra algum nó => existe ciclo. Devolve um ciclo."""
    nos = set(arestas) | {v for vs in arestas.values() for v in vs}
    grau = dict.fromkeys(nos, 0)
    for vs in arestas.values():
        for v in vs:
            grau[v] += 1
    fila = deque(n for n in nos if grau[n] == 0)
    while fila:
        n = fila.popleft()
        for v in arestas.get(n, ()):
            grau[v] -= 1
            if grau[v] == 0:
                fila.append(v)
    restantes = {n for n in nos if grau[n] > 0}
    if not restantes:
        return None
    n = next(iter(restantes))
    caminho, vistos = [], {}
    while n not in vistos:
        vistos[n] = len(caminho)
        caminho.append(n)
        n = next(v for v in arestas[n] if v in restantes)
    return caminho[vistos[n]:]


def formatar_contraexemplo(res: Resultado, max_linhas=200):
    """Traço legível: um evento por linha, com o tempo em ms."""
    linhas = []
    for t, item in enumerate(res.contraexemplo, start=1):
        if item[0] == "(ciclo)":
            linhas.append(f"  ... ciclo repetido indefinidamente (estado {item[1][4]})")
            break
        (mao, zona, sens, acao, ent), ev, s = item
        txt = f"t={t:4d} ms  mao={mao} sensor={sens} zona={zona}"
        if acao == "executa":
            txt += f"  ciclo: rearme={ent[0]} chegou={ent[1]}  {ev.get('tid') or '-'} -> {s[4]}"
        elif acao == "perde":
            txt += "  ciclo PERDIDO (jitter)"
        txt += f"  torque={['ON', 'DECAINDO', 'ZERO'][s[10]]}"
        if s[12] >= 0:
            txt += f"  relogio_prazo={s[12]} ms"
        for k in ("viola_p1", "viola_p2", "viola_p4"):
            if ev.get(k):
                txt += f"  <<< VIOLAÇÃO {k[-2:].upper()}"
        linhas.append(txt)
    if len(linhas) > max_linhas:
        linhas = linhas[:40] + [f"  ... ({len(linhas) - 80} linhas omitidas) ..."] + linhas[-40:]
    return "\n".join(linhas)
