from app.services.supabase_service import get_supabase
import json

# Atualizado para bater com o seu novo motor genético v19.0
VERSAO_GERADOR_ATUAL = "v19.0-genetic-context-engine"


# ==========================================================
# BACKTEST (NÃO BLOQUEANTE) - PRESERVADO
# ==========================================================
def calcular_score_backtest(reg):
    total = int(reg.get("total_concursos", 1)) * int(reg.get("qtd_palpites", 1) or 1)

    if total == 0:
        return 0

    score = (
        int(reg.get("acertos_11", 0) or 0) * 1 +
        int(reg.get("acertos_12", 0) or 0) * 2 +
        int(reg.get("acertos_13", 0) or 0) * 5 +
        int(reg.get("acertos_14", 0) or 0) * 20 +
        int(reg.get("acertos_15", 0) or 0) * 100
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
# UTIL JSON SAFE - PRESERVADO
# ==========================================================
def _safe_json(valor):
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except:
            return {}
    return valor or {}


# ==========================================================
# PALPITE FIXO (REVISADO: Extrai dinamicamente o Índice 1 do dia)
# ==========================================================
def obter_palpite_fixo_publico():
    supabase = get_supabase()

    # Busca a data mais recente independente do marcador de tipo string
    ultima_data_res = (
        supabase
        .table("palpites_validos")
        .select("data_referencia")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not ultima_data_res.data:
        return None

    data_recente = ultima_data_res.data[0]["data_referencia"]

    # CORREÇÃO: Puxa o palpite de índice_palpite = 1 para assumir o papel de Fixo
    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("data_referencia", data_recente)
        .eq("indice_palpite", 1)
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    r = res.data[0]

    numeros = _safe_json(r.get("numeros"))
    metricas = _safe_json(r.get("metricas"))

    return {
        "data_referencia": r.get("data_referencia"),
        "numeros": numeros,
        "soma": r.get("soma_total") or r.get("soma", 0),
        "pares": r.get("pares") or 0,
        "impares": r.get("impares") or 0,
        "metricas": {
            "score": r.get("score") or metricas.get("score_final") or metricas.get("score", 0),
            "metodo": r.get("versao_gerador") or metricas.get("versao", VERSAO_GERADOR_ATUAL),
            "ranking": metricas.get("ranking"),
            "score_backtest": obter_score_backtest(supabase, "fixo"),
            "memoria_aplicada": metricas.get("memoria_aplicada", False)
        }
    }


# ==========================================================
# PALPITES ESTATÍSTICOS (REVISADO: Traz a lista do concurso do índice 1 ao 7)
# ==========================================================
def obter_palpites_estatisticos_publico():
    supabase = get_supabase()

    # 1. Busca a data de referência mais recente disponível
    ultima_data_res = (
        supabase
        .table("palpites_validos")
        .select("data_referencia")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not ultima_data_res.data:
        return []

    data_recente = ultima_data_res.data[0]["data_referencia"]

    # 2. CORREÇÃO: Remove o filtro rígido .eq("tipo", "estatistico")
    # Traz TODOS os registros gerados para a data, ordenados do 1º ao 7º
    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("data_referencia", data_recente) 
        .order("indice_palpite")
        .execute()
    )

    score_backtest = obter_score_backtest(supabase, "estatistico")
    palpites = []

    for r in res.data or []:
        numeros = _safe_json(r.get("numeros"))
        metricas = _safe_json(r.get("metricas"))

        palpites.append({
            "data_referencia": r.get("data_referencia"),
            "indice_palpite": r.get("indice_palpite") or 0,
            "numeros": numeros,
            "soma": r.get("soma_total") or r.get("soma", 0),
            "pares": r.get("pares") or 0,
            "impares": r.get("impares") or 0,
            "metricas": {
                "score": r.get("score") or metricas.get("score_final") or metricas.get("score", 0),
                "metodo": r.get("versao_gerador") or metricas.get("versao", VERSAO_GERADOR_ATUAL),
                "ranking": metricas.get("ranking"),
                "score_backtest": score_backtest,
                "memoria_aplicada": metricas.get("memoria_aplicada", False)
            }
        })

    return palpites
