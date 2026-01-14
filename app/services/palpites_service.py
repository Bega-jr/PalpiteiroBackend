from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import json

# ==========================
# PALPITE FIXO (PÚBLICO)
# ==========================

def obter_palpite_fixo_publico():
    supabase = get_supabase()

    try:
        res = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("tipo", "fixo")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        print(f"[ERROR] Falha ao consultar palpite fixo: {e}")
        return None

    if not res.data:
        return None

    r = res.data[0]

    numeros = json.loads(r["numeros"]) if isinstance(r.get("numeros"), str) else r.get("numeros")
    metricas = json.loads(r["metricas"]) if isinstance(r.get("metricas"), str) else r.get("metricas") or {}

    return {
        "data_referencia": r.get("data_referencia"),
        "numeros": numeros,
        "soma_total": r.get("soma"),
        "pares": r.get("pares"),
        "impares": r.get("impares"),
        "metricas": metricas
    }


# ==========================
# PALPITES ESTATÍSTICOS (PÚBLICO)
# ==========================

def obter_palpites_estatisticos_publico():
    supabase = get_supabase()

    try:
        # 1️⃣ Descobre a data mais recente com palpites estatísticos
        data_resp = (
            supabase
            .table("palpites_validos")
            .select("data_referencia")
            .eq("tipo", "estatistico")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        print(f"[ERROR] Falha ao buscar data de referência: {e}")
        return []

    if not data_resp.data:
        return []

    data_atual = data_resp.data[0]["data_referencia"]

    try:
        # 2️⃣ Busca apenas os palpites dessa data
        res = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("tipo", "estatistico")
            .eq("data_referencia", data_atual)
            .order("indice_palpite")
            .execute()
        )
    except Exception as e:
        print(f"[ERROR] Falha ao consultar palpites estatísticos: {e}")
        return []

    dados = res.data or []

    for r in dados:
        r["numeros"] = json.loads(r["numeros"]) if isinstance(r.get("numeros"), str) else r.get("numeros")
        r["metricas"] = json.loads(r["metricas"]) if isinstance(r.get("metricas"), str) else r.get("metricas") or {}

    return dados
