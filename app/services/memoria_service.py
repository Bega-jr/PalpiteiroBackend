from datetime import date
from typing import Dict, Tuple, Any
from app.services.supabase_service import get_supabase


# ==========================================================
# Utilitário: gerar chave do cenário
# ==========================================================
def gerar_chave_cenario(metricas: Dict[str, Any]) -> Tuple:
    """
    Recebe output de extrair_metricas_jogo e devolve
    chave padronizada para memória.
    """
    return (
        round(metricas["soma"] / 10) * 10,
        metricas["pares"],
        metricas["primos"],
        tuple(metricas["linhas"]),
    )


# ==========================================================
# Buscar cenário existente
# ==========================================================
def obter_memoria_cenario(chave: Tuple) -> Dict | None:
    supabase = get_supabase()

    soma_faixa, pares, primos, linhas = chave

    resp = (
        supabase.table("memoria_cenarios")
        .select("*")
        .eq("soma_faixa", soma_faixa)
        .eq("pares", pares)
        .eq("primos", primos)
        .eq("linhas", list(linhas))
        .limit(1)
        .execute()
    )

    if resp.data:
        return resp.data[0]

    return None


# ==========================================================
# Criar cenário se não existir
# ==========================================================
def criar_memoria_cenario(chave: Tuple):
    supabase = get_supabase()

    soma_faixa, pares, primos, linhas = chave

    supabase.table("memoria_cenarios").insert({
        "soma_faixa": soma_faixa,
        "pares": pares,
        "primos": primos,
        "linhas": list(linhas),
        "vezes_gerado": 0,
        "acertos_11": 0,
        "acertos_12": 0,
        "acertos_13": 0,
        "acertos_14": 0,
        "acertos_15": 0,
        "score_medio_real": 0,
        "tendencia": 0,
        "saturacao": 0,
        "ultima_aparicao": date.today().isoformat(),
    }).execute()


# ==========================================================
# Atualizar memória após resultado real
# ==========================================================
def atualizar_memoria_cenario(
    chave: Tuple,
    acertos: int,
    score_real: float
):
    """
    Deve ser chamado APÓS sair o resultado oficial
    """

    supabase = get_supabase()

    memoria = obter_memoria_cenario(chave)

    if not memoria:
        criar_memoria_cenario(chave)
        memoria = obter_memoria_cenario(chave)

    vezes_gerado = memoria["vezes_gerado"] + 1

    # Atualiza acertos
    campos_acertos = {
        11: "acertos_11",
        12: "acertos_12",
        13: "acertos_13",
        14: "acertos_14",
        15: "acertos_15",
    }

    update_data = {
        "vezes_gerado": vezes_gerado,
        "ultima_aparicao": date.today().isoformat(),
    }

    if acertos in campos_acertos:
        campo = campos_acertos[acertos]
        update_data[campo] = memoria.get(campo, 0) + 1

    # ======================================================
    # Atualiza score médio (média móvel simples)
    # ======================================================
    score_antigo = float(memoria.get("score_medio_real", 0))
    score_medio = ((score_antigo * (vezes_gerado - 1)) + score_real) / vezes_gerado
    update_data["score_medio_real"] = round(score_medio, 6)

    # ======================================================
    # Saturação (quanto mais usado, menor prioridade)
    # ======================================================
    saturacao = min(vezes_gerado / 200, 1)  # escala ajustável
    update_data["saturacao"] = round(saturacao, 6)

    # ======================================================
    # Tendência (simples V1)
    # ======================================================
    tendencia = score_real - score_antigo
    update_data["tendencia"] = round(tendencia, 6)

    supabase.table("memoria_cenarios") \
        .update(update_data) \
        .eq("id", memoria["id"]) \
        .execute()


# ==========================================================
# Aplicar memória no score
# ==========================================================
def aplicar_memoria_ao_score(
    chave: Tuple,
    score_base: float
) -> float:
    """
    Ajusta score considerando memória histórica
    """

    memoria = obter_memoria_cenario(chave)

    if not memoria:
        return score_base

    tendencia = float(memoria.get("tendencia", 0))
    saturacao = float(memoria.get("saturacao", 0))

    score_ajustado = (
        score_base
        * (1 + tendencia)
        * (1 - saturacao)
    )

    return max(score_ajustado, 0)
