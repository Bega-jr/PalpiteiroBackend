import sys
import json
import random
import itertools
import numpy as np
import pytz
import time


from collections import Counter

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

from app.services.aprendizado_service_v3 import (
    obter_fator_aprendizado_global
)

from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais
)

from app.services.meta_learning_service import (
    obter_pesos_ensemble
)

from app.services.persistencia_analytics_service import (
    persistir_telemetria
)

from app.services.recompensa_evolutiva_service import (
    calcular_recompensa_evolutiva
)

# ======================================================
# NOVOS MÓDULOS V19.0
# ======================================================
from app.services.feature_store_service import (
    gerar_features_jogo
)

from app.services.clusterizacao_service import (
    identificar_cluster_jogo
)

from app.services.diversidade_service import (
    diversidade_avancada_ok
)

from app.services.montecarlo_service import (
    simular_probabilidade_jogo
)

from app.services.motores_ensemble_service import (
    calcular_score_ensemble
)

from app.services.selecao_genetica_service import (
    selecionar_populacao_final
)

from scripts.processamento_diario_lotofacil import (
    carregar_historico,
    extrair_estrutura
)


VERSAO = "v19.0-genetic-context-engine"

QTD_FINAL = 7

MAX_TENTATIVAS = 120000

PRIMOS = {
    2, 3, 5, 7, 11,
    13, 17, 19, 23
}

MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15,
    16, 20, 21, 22,
    23, 24, 25
}


# ======================================================
# AUX
# ======================================================
def media_segura(v, fallback=0.5):

    validos = [
        x for x in v
        if x is not None
    ]

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

    linhas = [

        "🟢 Pipeline Lotofácil concluído!",
        "",
        f"🎯 Palpites gerados para o concurso {concurso_ref}",
        ""
    ]

    linhas.extend(
        linhas_palpites
    )

    return "\n".join(linhas)


# ======================================================
# FILTROS
# ======================================================
def calcular_filtros(
    nums,
    ultimo
):

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
# CONTEXTO
# ======================================================
def detectar_contexto(hist):

    janela = hist[-12:]

    repetidos = []
    somas = []
    sequencias = []

    for i, h in enumerate(janela):

        nums = h["numeros"]

        ant = (
            janela[i - 1]["numeros"]
            if i > 0
            else nums
        )

        filtros = calcular_filtros(
            nums,
            ant
        )

        repetidos.append(
            filtros["repetidos"]
        )

        somas.append(
            filtros["soma"]
        )

        sequencias.append(
            filtros["seq_max"]
        )

    return {

        "media_repetidos": float(
            np.mean(repetidos)
        ),

        "media_soma": float(
            np.mean(somas)
        ),

        "media_seq": float(
            np.mean(sequencias)
        )
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
def score_base(
    jogo,
    base
):

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

    scores_ternos = [

        base.get(
            tuple(sorted(t)),
            0.5
        )

        for t in ternos[:120]
    ]

    s3 = (

        media_segura(scores_ternos)
        * 0.70

        +

        max(scores_ternos)
        * 0.30
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
        return 0.93

    if vezes <= 5:
        return 1.05

    return 1.0


def bonus_fadiga(mem):

    if not mem:
        return 1.0

    fadiga = float(
        mem.get(
            "fadiga_estrutura",
            0
        )
    )

    return max(
        0.88,
        1 - (fadiga * 0.10)
    )


def bonus_recencia(mem):

    if not mem:
        return 1.0

    taxa = float(
        mem.get(
            "taxa_7d",
            0
        )
    )

    return 1 + (taxa * 0.05)


def bonus_moldura(filtros):

    qtd = filtros["moldura"]

    if 10 <= qtd <= 13:
        return 1.05

    if qtd <= 7:
        return 0.95

    return 1.0


def fator_regime(tipo):

    if tipo == "EXPANSAO_QUENTES":
        return 1.05

    if tipo == "CONTRACAO_FRIAS":
        return 0.95

    return 1.0


# ======================================================
# MAIN
# ======================================================
def main():

    inicio_execucao = time.time()
    
    supabase = get_supabase()

    print(f"🛡️ {VERSAO}")

    fuso = pytz.timezone(
        "America/Sao_Paulo"
    )

    hoje = datetime.now(
        fuso
    ).date().isoformat()

    hist = carregar_historico()

    contexto = detectar_contexto(hist)

    ultimo = hist[-1]["numeros"]

    concurso_ref = (
        int(hist[-1]["concurso"])
        + 1
    )

    if concurso_ja_processado(
        supabase,
        concurso_ref
    ):

        print(
            f"ℹ️ Concurso {concurso_ref} já possui palpites."
        )

        return


    print(
        f"📊 Aprendizado: últimos {len(hist)} concursos"
    )


    base_scores, _ = (
        calcular_score_combinacoes_reais()
    )

    fator_global = (
        obter_fator_aprendizado_global()["fator"]
    )

    pesos = obter_pesos_ensemble()


    p_base = pesos["peso_base"]
    p_global = pesos["peso_global"]
    p_feedback = pesos["peso_feedback"]
    p_regime = pesos["peso_regime"]
    p_moldura = pesos["peso_moldura"]
    p_estrutura = pesos["peso_estrutura"]
    p_fadiga = pesos["peso_fadiga"]
    p_recencia = pesos["peso_recencia"]


    # ==================================================
    # ANTI-COLAPSO CONTEXTUAL
    # ==================================================
    if contexto["media_repetidos"] >= 9:

        p_feedback *= 1.05
        p_estrutura *= 1.05

    if contexto["media_soma"] <= 185:

        p_base *= 1.03

    if contexto["media_seq"] >= 4:

        p_regime *= 1.04


    p_feedback = min(
        p_feedback,
        0.22
    )

    p_estrutura = min(
        p_estrutura,
        0.18
    )


    tipo_regime = "NEUTRO"

    try:

        reg = (

            supabase
            .table("memoria_regimes")
            .select("tipo_regime")
            .order(
                "concurso",
                desc=True
            )
            .limit(1)
            .execute()
            .data
        )

        if reg:

            tipo_regime = (
                reg[0]["tipo_regime"]
            )

    except:
        pass


    fator_feedback = 1.0

    try:

        fb = (

            supabase
            .table("memoria_feedback_loop")
            .select("fator_correcao")
            .eq(
                "concurso_referencia",
                concurso_ref - 1
            )
            .execute()
            .data
        )

        if fb:

            fator_feedback = float(
                fb[0]["fator_correcao"]
            )

    except:
        pass


    memoria = {

        m["hash_estrutura"]: m

        for m in (
            supabase
            .table("memoria_cenarios")
            .select("*")
            .execute()
            .data
        )
    }


    usados = set(

        tuple(sorted(h["numeros"]))

        for h in hist
    )


    candidatos = []

    pool = list(
        range(1, 26)
    )

    contador_dezenas = Counter()


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


    # ==================================================
    # GERAÇÃO
    # ==================================================
    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 2200:
            break

        jogo = sorted(
            random.sample(
                pool,
                15
            )
        )

        if tuple(jogo) in usados:
            continue


        filtros = calcular_filtros(
            jogo,
            ultimo
        )

        estrutura = extrair_estrutura(
            jogo
        )

        mem = memoria.get(
            estrutura["hash_estrutura"]
        )


        if not validar_autonomo(
            filtros,
            estrutura["linhas"],
            limites
        ):
            continue


        # ==================================================
        # FEATURES
        # ==================================================
        features = gerar_features_jogo(

            jogo=jogo,

            filtros=filtros,

            estrutura=estrutura,

            contexto=contexto
        )


        # ==================================================
        # MONTE CARLO
        # ==================================================
        score_mc = simular_probabilidade_jogo(
            jogo,
            historico=hist
        )


        # ==================================================
        # CLUSTER
        # ==================================================
        cluster_id = identificar_cluster_jogo(
            features
        )
        # ==================================================
        # RECOMPENSA EVOLUTIVA
        # ==================================================
        recompensa = calcular_recompensa_evolutiva(
        
            estrutura=estrutura,
        
            filtros=filtros,
        
            cluster_id=cluster_id
        )


        # ==================================================
        # DIVERSIDADE AVANÇADA
        # ==================================================
        if not diversidade_avancada_ok(

            jogo= jogo,

            candidatos=candidatos[-50:],

            estrutura=estrutura,

            cluster_id=cluster_id
        ):
            continue


        s1, s2, s3 = score_base(
            jogo,
            base_scores
        )


        score_estatistico = (

            (s1 * 0.30)

            +

            (s2 * 0.35)

            +

            (s3 * 0.35)
        )


        # ==================================================
        # ENSEMBLE CENTRALIZADO
        # ==================================================
        score_final = calcular_score_ensemble(

            score_estatistico=score_estatistico,

            score_montecarlo=score_mc,

            fator_global=fator_global,

            fator_feedback=fator_feedback,

            fator_regime=fator_regime(tipo_regime),

            bonus_estrutura=bonus_estrutura(mem),

            bonus_fadiga=bonus_fadiga(mem),

            bonus_recencia=bonus_recencia(mem),

            bonus_moldura=bonus_moldura(filtros),

            pesos=pesos,

            bonus_recompensa=recompensa
        )


        # ==================================================
        # PENALIDADE GLOBAL
        # ==================================================
        penalidade_repeticao = sum(

            contador_dezenas[n] * 0.015

            for n in jogo
        )

        score_final -= penalidade_repeticao


        # ==================================================
        # ENTROPIA CONTROLADA
        # ==================================================
        score_final *= random.uniform(
            0.985,
            1.015
        )


        # ==================================================
        # EXPLORAÇÃO EVOLUTIVA
        # ==================================================
        if random.random() < 0.18:

            score_final *= random.uniform(
                0.92,
                1.08
            )


        # ==================================================
        # PERSISTÊNCIA ANALYTICS
        # ==================================================
        try:
        
            from app.services.persistencia_analytics_service import (
        
                salvar_feature_store_jogo,
        
                salvar_cluster_jogo
            )
        
            salvar_feature_store_jogo(
        
                concurso=concurso_ref,
        
                jogo=jogo,
        
                features=features,
        
                score=score_final,
        
                cluster_id=cluster_id
            )
        
            salvar_cluster_jogo(
        
                concurso=concurso_ref,
        
                cluster_id=cluster_id,
        
                jogo=jogo,
        
                score=score_final
            )
        
        except Exception as e:
        
            print(
                f"⚠️ Falha analytics: {e}"
            )
        
        
        candidatos.append({
        
            "nums": jogo,
        
            "score": float(score_final),

            "score_estatistico": float(score_estatistico),
        
            "score_mc": float(score_mc),
        
            "filtros": filtros,
        
            "estrutura": estrutura,
        
            "features": features,
        
            "cluster_id": cluster_id
        })


       # ==================================================
        # CONTADOR DE DIVERSIDADE
        # ==================================================
        for dezena in jogo:
            contador_dezenas[dezena] += 1
        
        # ==================================================
        # FIM LOOP GERAÇÃO
        # ==================================================
        
        print(
            f"✅ Aprendizado concluído: {len(candidatos)} candidatos"
        )

        
    # ==================================================
    # MÉTRICAS GERAIS
    # ==================================================
    if candidatos:

        try:

            media_score = np.mean([
                x["score"]
                for x in candidatos
            ])

            media_mc = np.mean([
                x["score_mc"]
                for x in candidatos
            ])

            clusters_unicos = len(set([
                x["cluster_id"]
                for x in candidatos
            ]))

            print(
                f"📊 Score médio: "
                f"{media_score:.6f}"
            )

            print(
                f"🎲 Monte Carlo médio: "
                f"{media_mc:.6f}"
            )

            print(
                f"🧬 Clusters únicos: "
                f"{clusters_unicos}"
            )

        except Exception as e:

            print(
                f"⚠️ Erro métricas finais: {e}"
            )


    # ==================================================
    # ORDENA
    # ==================================================
    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    # ==================================================
    # SELEÇÃO GENÉTICA
    # ==================================================
    finais = selecionar_populacao_final(

        candidatos=candidatos,

        qtd_final=QTD_FINAL
    )


    # ==================================================
    # LOG CONTEXTUAL
    # ==================================================
    try:

        supabase.table(
            "meta_learning_execucoes"
        ).upsert({

            "concurso_referencia": concurso_ref,

            "contexto_repetidos": contexto["media_repetidos"],

            "contexto_soma": contexto["media_soma"],

            "contexto_seq": contexto["media_seq"],

            "qtd_candidatos": len(candidatos),

            "score_medio": round(
                np.mean([
                    x["score"]
                    for x in finais
                ]),
                6
            )

        },
        on_conflict="concurso_referencia"
        ).execute()

    except:
        pass


    # ==================================================
    # OUTPUT
    # ==================================================
    payload = []

    telegram = []


    for i, c in enumerate(finais, 1):

        estrategia = (
            "exploratorio"
            if i >= 6
            else "estatistico"
        )

        telegram.append(

            f"{i}º | "

            f"{c['score']:.6f} | "

            f"MC={c['score_mc']:.4f} | "

            f"C{c['cluster_id']} | "

            f"{c['nums']}"
        )

        payload.append({

        "data_referencia": hoje,
    
        "concurso_referencia": concurso_ref,
    
        "indice_palpite": i,
    
        "tipo": estrategia,
    
        "numeros": json.dumps(
            c["nums"]
        ),
    
        "pares": c["filtros"]["pares"],
    
        "impares": (
            15 - c["filtros"]["pares"]
        ),
    
        "soma_total": c["filtros"]["soma"],
    
        "score": round(
            float(c["score"]),
            8
        ),
    
        "score_montecarlo": round(
            float(c["score_mc"]),
            8
        ),
    
        "score_estrutural": round(
            float(c["score_estatistico"]),
            8
        ),
    
        "cluster_id": int(
            c["cluster_id"]
        ),
    
        "processado": False,
    
        "conferido": False,
    
        "versao_gerador": VERSAO
    })

        supabase.table(
        "palpites_validos"
    ).upsert(
        payload,
        on_conflict=(
            "concurso_referencia,"
            "indice_palpite"
        )
    ).execute()

    # ==================================================
    # TELEMETRIA FINAL
    # ==================================================
    try:
        tempo_total = time.time() - inicio_execucao
        
        persistir_telemetria(
            supabase=supabase,
            concurso_ref=concurso_ref,
            candidatos=finais,
            tempo_execucao=tempo_total,
            versao=VERSAO
        )
    except Exception as e:
        print(f"⚠️ Falha telemetria final: {e}")

    # Sempre executa o bloco do Telegram (independente do try/except acima)
    print("\n📲 TELEGRAM_PAYLOAD_START")
    print(
        montar_msg_telegram(
            concurso_ref,
            telegram
        )
    )
    print("📲 TELEGRAM_PAYLOAD_END")


if __name__ == "__main__":
    main()
