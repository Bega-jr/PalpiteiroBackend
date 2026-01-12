from app.services.supabase_service import get_supabase
from fastapi import HTTPException
from datetime import date
import json

# ==========================
# PALPITE FIXO (PÚBLICO)
# ==========================

def obter_palpite_fixo_publico():
    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("tipo_palpite", "fixo")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not res.data:
        return None

    r = res.data[0]

    return {
        "data_referencia": r.get("data_referencia"),
        "numeros": r.get("numeros"),
        "soma_total": r.get("soma"),
        "pares": r.get("pares"),
        "impares": r.get("impares"),
        "metricas": r.get("metricas") or {}
    }


# ==========================
# PALPITES ESTATÍSTICOS (PÚBLICO)
# ==========================

def obter_palpites_estatisticos_publico():
    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("tipo_palpite", "estatistico")
        .order("indice_palpite")
        .execute()
    )

    return res.data or []
