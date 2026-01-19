from app.services.supabase_service import get_supabase
import json

VERSAO_GERADOR_ATUAL = "v1.2-top-auto"


# ==========================
# BACKTEST (NÃO BLOQUEANTE)
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


def obter_score_backtest(supabase, tipo):
    res = (
        supabase
        .table("palpites_resultados_reais")
        .select("*")
        .eq("tipo_palpite", tipo)
        .eq("versao_gerador", VERSAO_GERADOR_ATUAL)
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    return calcular_score_backtest(res.data[0])


# ==========================
# PALPITE FIXO
# ==========================
def obter_palpite_fixo_publico():
    supabase = get_supabase()

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

    return {
        "data_referencia": r["data_referencia"],
        "numeros": numeros,
        "soma": r["soma_total"],
        "pares": r["pares"],
        "impares": r["impares"],
        "metricas": metricas,
        "score_backtest": obter_score_backtest(supabase, "fixo"),
    }


# ==========================
# PALPITES ESTATÍSTICOS
# ==========================
def obter_palpites_estatisticos_publico():
    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("tipo", "estatistico")
        .order("indice_palpite")
        .execute()
    )

    score_backtest = obter_score_backtest(supabase, "estatistico")

    palpites = []

    for r in res.data or []:
        numeros = json.loads(r["numeros"]) if isinstance(r["numeros"], str) else r["numeros"]
        metricas = json.loads(r["metricas"]) if isinstance(r["metricas"], str) else {}

        palpites.append({
            "data_referencia": r["data_referencia"],
            "indice_palpite": r["indice_palpite"],
            "numeros": numeros,
            "soma": r["soma_total"],
            "pares": r["pares"],
            "impares": r["impares"],
            "metricas": metricas,
            "score_backtest": score_backtest,
        })

    return palpites
