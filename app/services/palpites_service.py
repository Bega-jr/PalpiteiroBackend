from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import json
from datetime import date

# ==========================
# CONFIGURAÇÕES
# ==========================
SCORE_MINIMO_BACKTEST = 0.8  # baseline mínimo aceitável
VERSAO_GERADOR_PADRAO = "v1.0"

# ==========================
# BACKTEST SCORE
# ==========================
def calcular_score_backtest(reg):
    total = reg["total_concursos"] * reg["qtd_palpites"]
    if total == 0:
        return 0

    score = (
        reg["acertos_11"] * 1 +
        reg["acertos_12"] * 2 +
        reg["acertos_13"] * 5 +
        reg["acertos_14"] * 20 +
        reg["acertos_15"] * 100
    ) / total

    return round(score, 2)

def versao_valida_por_backtest(supabase, tipo):
    res = (
        supabase
        .table("palpites_resultados_reais")
        .select("*")
        .eq("tipo_palpite", tipo)
        .eq("versao_gerador", VERSAO_GERADOR_PADRAO)
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        return False

    score = calcular_score_backtest(res.data[0])
    return score >= SCORE_MINIMO_BACKTEST

# ==========================
# PALPITE FIXO (PÚBLICO)
# ==========================
def obter_palpite_fixo_publico():
    supabase = get_supabase()

    if not versao_valida_por_backtest(supabase, "fixo"):
        return None

    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("tipo", "fixo")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    r = res.data[0]

    numeros = json.loads(r["numeros"]) if isinstance(r["numeros"], str) else r["numeros"]
    metricas = json.loads(r["metricas"]) if isinstance(r["metricas"], str) else {}

    # 🔒 Filtro raro
    soma = sum(numeros)
    if not (170 <= soma <= 210):
        return None

    return {
        "data_referencia": r["data_referencia"],
        "numeros": numeros,
        "pares": r["pares"],
        "impares": r["impares"],
        "metricas": metricas
    }

# ==========================
# PALPITES ESTATÍSTICOS (PÚBLICO)
# ==========================
def obter_palpites_estatisticos_publico():
    supabase = get_supabase()
    hoje = date.today().isoformat()

    if not versao_valida_por_backtest(supabase, "estatistico"):
        return []

    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("tipo", "estatistico")
        .eq("data_referencia", hoje)
        .order("indice_palpite")
        .execute()
    )

    dados_validos = []

    for r in res.data or []:
        numeros = json.loads(r["numeros"]) if isinstance(r["numeros"], str) else r["numeros"]
        metricas = json.loads(r["metricas"]) if isinstance(r["metricas"], str) else {}

        pares = r["pares"]
        soma = sum(numeros)

        # 🔒 FILTROS ANTI-RARIDADE
        if pares < 6 or pares > 9:
            continue
        if soma < 170 or soma > 210:
            continue

        dados_validos.append({
            "indice_palpite": r["indice_palpite"],
            "numeros": numeros,
            "pares": r["pares"],
            "impares": r["impares"],
            "metricas": metricas
        })

    return dados_validos
