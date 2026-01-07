from fastapi import HTTPException
from app.services.supabase_service import get_supabase

TABELA = "palpites"


# ======================================================
# UTILITÁRIOS
# ======================================================
def _obter_data_referencia_mais_recente():
    resp = (
        supabase
        .table(TABELA)
        .select("data_referencia")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        return None

    return resp.data[0]["data_referencia"]


def _formatar_palpite(p):
    """
    Padroniza o objeto enviado ao frontend
    """
    return {
        "id": p["id"],
        "indice": p["indice_palpite"],
        "tipo": p.get("tipo"),
        "numeros": p["numeros"],
        "soma": p["soma_total"],
        "pares": p["pares"],
        "impares": p["impares"],
        "sequencias": p["qtd_sequencias"],
        "metricas": p.get("metricas"),
        "filtros": p.get("filtros_aplicados"),
        "origem": p.get("origem"),
        "criado_em": p["created_at"]
    }


# ======================================================
# PALPITE FIXO
# ======================================================
def obter_palpite_fixo_publico():
    data_ref = _obter_data_referencia_mais_recente()

    if not data_ref:
        raise HTTPException(404, "Nenhum palpite disponível")

    resp = (
        supabase
        .table(TABELA)
        .select("*")
        .eq("data_referencia", data_ref)
        .eq("indice_palpite", 0)
        .limit(1)
        .execute()
    )

    if not resp.data:
        raise HTTPException(404, "Palpite fixo não encontrado")

    palpite = resp.data[0]

    return {
        "status": "ok",
        "data_referencia": data_ref,
        "palpite": _formatar_palpite(palpite)
    }


# ======================================================
# PALPITES ESTATÍSTICOS
# ======================================================
def obter_palpites_estatisticos_publico():
    data_ref = _obter_data_referencia_mais_recente()

    if not data_ref:
        return {
            "status": "ok",
            "data_referencia": None,
            "total": 0,
            "palpites": []
        }

    resp = (
        supabase
        .table(TABELA)
        .select("*")
        .eq("data_referencia", data_ref)
        .gt("indice_palpite", 0)
        .order("indice_palpite")
        .execute()
    )

    palpites = [_formatar_palpite(p) for p in resp.data]

    return {
        "status": "ok",
        "data_referencia": data_ref,
        "total": len(palpites),
        "palpites": palpites
    }


# ======================================================
# FIXO + ESTATÍSTICOS (ENDPOINT IDEAL PARA FRONTEND)
# ======================================================
def obter_todos_palpites_publico():
    data_ref = _obter_data_referencia_mais_recente()

    if not data_ref:
        return {
            "status": "ok",
            "data_referencia": None,
            "fixo": None,
            "estatisticos": []
        }

    resp = (
        supabase
        .table(TABELA)
        .select("*")
        .eq("data_referencia", data_ref)
        .order("indice_palpite")
        .execute()
    )

    fixo = None
    estatisticos = []

    for p in resp.data:
        if p["indice_palpite"] == 0:
            fixo = _formatar_palpite(p)
        else:
            estatisticos.append(_formatar_palpite(p))

    return {
        "status": "ok",
        "data_referencia": data_ref,
        "fixo": fixo,
        "total_estatisticos": len(estatisticos),
        "estatisticos": estatisticos
    }
