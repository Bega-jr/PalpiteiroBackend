import sys
import json
import random
import itertools
import numpy as np
import pytz

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

from app.services.meta_learning_service import (
    obter_pesos_ensemble,
    registrar_execucao_ensemble
)

from scripts.processamento_diario_lotofacil import (
    carregar_historico,
    extrair_estrutura
)


# ======================================================
# CONFIG
# ======================================================
VERSAO = "v17.1-adaptive-ensemble"

QTD_FINAL = 7
MAX_TENTATIVAS = 120000

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15, 16, 20,
    21, 22, 23, 24, 25
}


# ======================================================
# UTIL
# ======================================================
def media_segura(v, fallback=0.5):

    validos = [x for x in v if x is not None]

    if not validos:
        return fallback

    return float(np.mean(validos))


def concurso_ja_processado(
    supabase,
    concurso_ref
):

    rows = (

        supabase
        .table("palpites_validos")
        .select("indice_palpite")
        .eq(
            "concurso_referencia",
            concurso_ref
        )
        .limit(1)
        .execute()
        .data
    )

    return len(rows) > 0


def montar_msg_telegram(
    concurso_ref,
    linhas_palpites
):

    linhas = []

    linhas.append(
        "🟢 Pipeline Lotofácil concluído!"
    )

    linhas.append("")

    linhas.append(
        f"🎯 Palpites gerados para o concurso {concurso_ref}"
    )

    linhas.append("")

    linhas.extend(
        linhas_palpites
    )

    return "\n".join(
        linhas
    )


def calcular_filtros(nums, ultimo):

    pares = sum(
        1 for n in nums
        if n % 2 == 0
    )

    primos = sum(
        1 for n in nums
        if n in PRIMOS
    )

    moldura = sum(
        1 for n in nums
        if n in MOLDURA
    )

    soma = sum(nums)

    repetidos = len(
        set(nums) & set(ultimo)
    )

    seq_max = 1
    atual = 1

    for i in range(len(nums) - 1):

        if nums[i + 1] == nums[i] + 1:

            atual += 1

            seq_max = max(
                seq_max,
                atual
            )

        else:

            atual = 1

    return {
        "pares": pares,
        "primos": primos,
        "moldura": moldura,
        "soma": soma,
        "repetidos": repetidos,
        "seq_max": seq_max
    }


# ======================================================
# VALIDAÇÃO
# ======================================================
def validar_autonomo(
    filtros,
    linhas,
    limites
):

    return (

        limites["soma_min"]
        <= filtros["soma"]
        <= limites["soma_max"]

        and

        limites["pares_min"]
        <= filtros["pares"]
        <= limites["pares_max"]

        and

        limites["primos_min"]
        <= filtros["primos"]
        <= limites["primos_max"]

        and

        limites["moldura_min"]
        <= filtros["moldura"]
        <= limites["moldura_max"]

        and

        limites["repetidos_min"]
        <= filtros["repetidos"]
        <= limites["repetidos_max"]

        and

        filtros["seq_max"]
        <= limites["seq_max_limite"]

        and

        max(linhas)
        <= limites["max_linha_limite"]
    )


# ======================================================
# SCORE BASE
# ======================================================
def score_base(jogo, base):

    s1 = media_segura([
        base.get((n,), 0.5)
        for n in jogo
    ])

    s2 = media_segura([

        base.get(
            tuple(sorted(p)),
            0.5
        )

        for p in itertools.combinations(
            jogo,
            2
        )
    ])

    ternos = list(
        itertools.combinations(
            jogo,
            3
        )
    )

    random.shuffle(ternos)

    ternos_amostrados = ternos[:120]

    scores_ternos = [

        base.get(
            tuple(sorted(t)),
            0.5
        )

        for t in ternos_amostrados
    ]

    s3 = (

        media_segura(
            scores_ternos
        ) * 0.70

        +

        max(scores_ternos) * 0.30
    )

    return s1, s2, s3


# ======================================================
# BONUS
# ======================================================
def bonus_estrutura(mem):

    if not mem:
        return 1.0

    vezes = int(
        mem.get(
            "vezes_gerado",
            0
        )
    )

    if vezes >= 40:
        return 0.97

    if vezes <= 5:
        return 1.03

    return 1.0


def diversidade_ok(
    novo,
    lista
):

    return all(

        len(
            set(novo)
            ^
            set(x["nums"])
        ) >= 8

        for x in lista
    )


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(f"🛡️ {VERSAO}")

    fuso = pytz.timezone(
        "America/Sao_Paulo"
    )

    hoje = datetime.now(
        fuso
    ).date().isoformat()

    hist = carregar_historico()

    ultimo = hist[-1]["numeros"]

    concurso_ref = int(
        hist[-1]["concurso"]
    ) + 1


    if concurso_ja_processado(
        supabase,
        concurso_ref
    ):

        print(
            f"ℹ️ Concurso {concurso_ref} já possui palpites gerados."
        )

        return


    # ======================================
    # BASE
    # ======================================
    base_scores, _ = (
        calcular_score_combinacoes_reais()
    )

    fator_global = (
        obter_fator_aprendizado_global()["fator"]
    )


    # ======================================
    # META LEARNING (Alinhado com as 8 colunas da sua tabela)
    # ======================================
    pesos = obter_pesos_ensemble()

    p_base = float(pesos.get("peso_base", 0.30))
    p_global = float(pesos.get("peso_global", 0.15))
    p_feedback = float(pesos.get("peso_feedback", 0.15))
    p_regime = float(pesos.get("peso_regime", 0.10))
    p_moldura = float(pesos.get("peso_moldura", 0.10))
    p_estrutura = float(pesos.get("peso_estrutura", 0.10))
    p_fadiga = float(pesos.get("peso_fadiga", 0.05))
    p_recencia = float(pesos.get("peso_recencia", 0.05))

    # ======================================
    # MEMÓRIA
    # ======================================
    memoria = {

        m["hash_estrutura"]: m

        for m in (

            supabase
            .table(
                "memoria_cenarios"
            )
            .select("*")
            .execute()
            .data
        )
    }

    usados = set(

        tuple(
            sorted(
                h["numeros"]
            )
        )

        for h in hist
    )

    candidatos = []

    pool = list(
        range(1, 26)
    )

    limites = {
        "soma_min": 160,
        "soma_max": 230,
        "pares_min": 5,
        "pares_max": 10,
        "primos_min": 3,
        "primos_max": 8,
        "moldura_min": 8,
        "moldura_max": 14,
        "repetidos_min": 6,
        "repetidos_max": 12,
        "seq_max_limite": 5,
        "max_linha_limite": 5
    }


    for _ in range(
        MAX_TENTATIVAS
    ):

        if len(
            candidatos
        ) >= 1500:

            break

        jogo = sorted(
            random.sample(
                pool,
                15
            )
        )

        if tuple(
            jogo
        ) in usados:

            continue

        filtros = calcular_filtros(
            jogo,
            ultimo
        )

        estrutura = extrair_estrutura(
            jogo
        )

        mem = memoria.get(
            estrutura[
                "hash_estrutura"
            ]
        )

        if not validar_autonomo(
            filtros,
            estrutura["linhas"],
            limites
        ):
            continue

        if not diversidade_ok(
            jogo,
            candidatos[-25:]
        ):
            continue


        # ======================================
        # ENSEMBLE ADAPTATIVO (Atualizado)
        # ======================================
        s1, s2, s3 = score_base(jogo, base_scores)

        # 1. Consolida o score estatístico base (unidade, dupla, terno)
        score_estatistico = (s1 * 0.30) + (s2 * 0.35) + (s3 * 0.35)

        # 2. Mescla os múltiplos critérios usando os novos pesos do Meta-Learning
        score_final = (
            (score_estatistico * peso_base) +
            (bonus_estrutura(mem) * peso_memoria) +
            (fator_global * peso_regime)
        )

        # 3. Aplica os pesos de feedback e recência como multiplicadores finos de estabilidade
        score_final *= (1.0 + (peso_feedback * 0.1))
        score_final *= (1.0 + (peso_recencia * 0.1))

        candidatos.append({
            "nums": jogo,
            "score": float(score_final),
            "filtros": filtros
        })

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = []
    for c in candidatos:
        if len(finais) >= QTD_FINAL:
            break
        if diversidade_ok(c["nums"], finais):
            finais.append(c)

    payload = []
    telegram = []
    somas_score = 0.0

    for i, c in enumerate(finais, 1):
        somas_score += c['score']
        linha = f"{i}º | {c['score']:.6f} | {c['nums']}"
        telegram.append(linha)

        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(c["nums"]),
            "pares": c["filtros"]["pares"],
            "impares": 15 - c["filtros"]["pares"],
            "soma_total": c["filtros"]["soma"],
            "processado": False,
            "conferido": False,
            
            # CORREÇÃO CRUCIAL: Ajustado para o nome real da sua coluna no banco
            "versao_gerador": VERSAO 
        })

    # Envia os palpites válidos para o banco sem rejeição de esquema
    supabase.table("palpites_validos").upsert(
        payload, on_conflict="concurso_referencia,indice_palpite"
    ).execute()

    # ======================================
    # REGISTRO DA EXECUÇÃO DO ENSEMBLE (Compatível com o novo Service)
    # ======================================
    media_score_geral = somas_score / len(finais) if finais else 0.0
    
    registrar_execucao_ensemble(
        concurso_ref=concurso_ref,
        media_score=media_score_geral,
        qtd_palpites=len(finais),
        versao=VERSAO
    )

    print("\n📲 TELEGRAM_PAYLOAD_START")
    print(montar_msg_telegram(concurso_ref, telegram))
    print("📲 TELEGRAM_PAYLOAD_END")

if __name__ == "__main__":
    main()
