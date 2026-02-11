from app.services.supabase_service import get_supabase
import json

VERSAO_GERADOR_ATUAL = "v4-memoria-estrategica"


# ==========================================================
# BACKTEST (NÃO BLOQUEANTE)
# ==========================================================
def calcular_score_backtest(reg):
    total = reg.get("total_concursos", 0) * reg.get("qtd_palpites", 0)

    if total == 0:
        return 0

    score = (
        reg.get("acertos_11", 0) * 1 +
        reg.get("acertos_12", 0) * 2 +
        reg.get("acertos_13", 0) * 5 +
        reg.get("acertos_14", 0) * 20 +
        reg.get("acertos_15", 0) * 100
    ) / total

    return round(score, 4)


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


# ==========================================================
# UTIL JSON SAFE
# ==========================================================
def _safe_json(valor):
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except:
            return {}
    return valor or {}


# ==========================================================
# PALPITE FIXO
# ==========================================================
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

    numeros = _safe_json(r.get("numeros"))
    metricas = _safe_json(r.get("metricas"))

    return {
        "versao_gerador": metricas.get("versao", VERSAO_GERADOR_ATUAL),
        "data_referencia": r.get("data_referencia"),
        "numeros": numeros,
        "soma": r.get("soma_total"),
        "pares": r.get("pares"),
        "impares": r.get("impares"),
        "score_final": metricas.get("score_final"),
        "ranking": metricas.get("ranking"),
        "score_backtest": obter_score_backtest(supabase, "fixo"),
        "memoria_aplicada": metricas.get("memoria_aplicada", False),
    }


# ==========================================================
# PALPITES ESTATÍSTICOS
# ==========================================================
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
        numeros = _safe_json(r.get("numeros"))
        metricas = _safe_json(r.get("metricas"))

        palpites.append({
            "versao_gerador": metricas.get("versao", VERSAO_GERADOR_ATUAL),
            "data_referencia": r.get("data_referencia"),
            "indice_palpite": r.get("indice_palpite"),
            "numeros": numeros,
            "soma": r.get("soma_total"),
            "pares": r.get("pares"),
            "impares": r.get("impares"),
            "score_final": metricas.get("score_final"),
            "ranking": metricas.get("ranking"),
            "score_backtest": score_backtest,
            "memoria_aplicada": metricas.get("memoria_aplicada", False),
        })

    return palpites
