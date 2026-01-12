from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import random
import traceback
from itertools import combinations

# -----------------------------------
# Helpers
# -----------------------------------
def _buscar_base_estatistica():
    supabase = get_supabase()

    numeros = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, score")
        .order("score", desc=True)
        .execute()
    ).data

    diario = (
        supabase
        .table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    ).data

    if not numeros or not diario:
        raise HTTPException(500, "Base estatística indisponível")

    return numeros, diario[0]


def _sortear_pool_por_peso(numeros, tamanho=18):
    pesos = [n["score"] for n in numeros]
    selecionados = set()

    while len(selecionados) < tamanho:
        escolhido = random.choices(numeros, weights=pesos, k=1)[0]["numero"]
        selecionados.add(escolhido)

    return sorted(selecionados)


def _validar_regras_suaves(jogo, diario):
    soma = sum(jogo)
    pares = sum(1 for n in jogo if n % 2 == 0)
    impares = 15 - pares

    if not (diario["media_soma"] - 20 <= soma <= diario["media_soma"] + 20):
        return False

    if abs(pares - diario["media_pares"]) > 3:
        return False

    sequencias = 1
    max_seq = 1
    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            sequencias += 1
            max_seq = max(max_seq, sequencias)
        else:
            sequencias = 1

    if max_seq > 4:
        return False

    return True


def _gerar_jogos(pool, diario, qtd=7):
    jogos_validos = []

    tentativas = 0
    while len(jogos_validos) < qtd and tentativas < 3000:
        tentativas += 1
        jogo = sorted(random.sample(pool, 15))

        if _validar_regras_suaves(jogo, diario):
            if jogo not in jogos_validos:
                jogos_validos.append(jogo)

    if len(jogos_validos) < qtd:
        raise HTTPException(500, "Falha ao gerar jogos válidos")

    return jogos_validos


# -----------------------------------
# GERAÇÃO PRINCIPAL
# -----------------------------------
def gerar_palpites_validos():
    """
    Executar 1x por concurso (cron ou admin)
    """
    try:
        supabase = get_supabase()

        numeros, diario = _buscar_base_estatistica()

        # 1. Pool ponderado (18–20)
        pool = _sortear_pool_por_peso(numeros, tamanho=18)

        # 2. Jogos estatísticos
        jogos = _gerar_jogos(pool, diario, qtd=7)

        # 3. Palpite fixo (top score)
        top_fixos = sorted(
            numeros, key=lambda x: x["score"], reverse=True
        )[:15]
        palpite_fixo = sorted([n["numero"] for n in top_fixos])

        data_ref = diario["data_referencia"]

        # 4. Limpa palpites do dia
        supabase.table("palpites_validos") \
            .delete().eq("data_referencia", data_ref).execute()

        # 5. Insere palpite fixo
        registros = [{
            "data_referencia": data_ref,
            "indice_palpite": 0,
            "numeros": palpite_fixo
        }]

        # 6. Insere estatísticos
        for idx, jogo in enumerate(jogos, start=1):
            registros.append({
                "data_referencia": data_ref,
                "indice_palpite": idx,
                "numeros": jogo
            })

        supabase.table("palpites_validos").insert(registros).execute()

        return {
            "status": "ok",
            "pool": pool,
            "palpite_fixo": palpite_fixo,
            "gerados": len(jogos)
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# -----------------------------------
# API PÚBLICA (MANTIDA)
# -----------------------------------
def _buscar_palpites_por_data():
    try:
        supabase = get_supabase()
        response = (
            supabase
            .table("palpites_validos")
            .select("*")
            .order("data_referencia", desc=True)
            .order("indice_palpite")
            .execute()
        )
        return response.data or []
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, detail=str(e))


def obter_palpite_fixo_publico():
    dados = _buscar_palpites_por_data()
    for r in dados:
        if r.get("indice_palpite") == 0:
            return r
    return None


def obter_palpites_estatisticos_publico():
    dados = _buscar_palpites_por_data()
    return [r for r in dados if r.get("indice_palpite", 0) > 0]

