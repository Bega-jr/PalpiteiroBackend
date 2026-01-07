import json
from datetime import date
from .supabase_service import get_supabase

# ==========================================================
# PALPITE FIXO (PUBLICO)
# ==========================================================
def obter_palpite_fixo_publico():
    hoje = date.today().isoformat()

    resp = (
        supabase
        .table("palpites")
        .select("*")
        .eq("tipo", "fixo")
        .eq("data_referencia", hoje)
        .order("indice_palpite")
        .execute()
    )

    dados = resp.data or []

    palpites_formatados = []
    for p in dados:
        palpites_formatados.append(_formatar_palpite(p))

    return {
        "status": "ok",
        "data_referencia": hoje,
        "total": len(palpites_formatados),
        "palpites": palpites_formatados
    }


# ==========================================================
# PALPITES ESTATISTICOS (PUBLICO)
# ==========================================================
def obter_palpites_estatisticos_publico():
    hoje = date.today().isoformat()

    resp = (
        supabase
        .table("palpites")
        .select("*")
        .eq("tipo", "estatistico")
        .eq("data_referencia", hoje)
        .order("indice_palpite")
        .execute()
    )

    dados = resp.data or []

    palpites_formatados = []
    for p in dados:
        palpites_formatados.append(_formatar_palpite(p))

    return {
        "status": "ok",
        "data_referencia": hoje,
        "total": len(palpites_formatados),
        "palpites": palpites_formatados
    }


# ==========================================================
# FORMATADOR CENTRAL (ESSENCIAL)
# ==========================================================
def _formatar_palpite(p):
    """
    Converte campos string JSON em objetos reais
    e devolve exatamente no formato esperado pelo frontend
    """

    # numeros
    numeros = []
    if p.get("numeros"):
        try:
            numeros = json.loads(p["numeros"])
        except Exception:
            numeros = []

    # metricas
    metricas = {}
    if p.get("metricas"):
        try:
            metricas = json.loads(p["metricas"])
        except Exception:
            metricas = {}

    # filtros
    filtros = []
    if p.get("filtros_aplicados"):
        try:
            filtros = json.loads(p["filtros_aplicados"])
        except Exception:
            filtros = []

    return {
        "id": p.get("id"),
        "indice_palpite": p.get("indice_palpite"),
        "numeros": numeros,
        "soma_total": p.get("soma_total"),
        "pares": p.get("pares"),
        "impares": p.get("impares"),
        "qtd_sequencias": p.get("qtd_sequencias"),
        "usa_mais_sorteados": p.get("usa_mais_sorteados"),
        "usa_menos_sorteados": p.get("usa_menos_sorteados"),
        "metricas": metricas,
        "filtros_aplicados": filtros,
        "origem": p.get("origem"),
        "created_at": p.get("created_at"),
    }

