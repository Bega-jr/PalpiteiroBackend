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
        print(f"[ERROR] Falha ao consultar palpites fixos: {e}")
        return None

    if not res.data:
        print("[INFO] Nenhum palpite fixo encontrado no Banco de dados.")
        return None

    r = res.data[0]

    # 🔹 Conversão defensiva de JSON
    numeros = json.loads(r.get("numeros")) if isinstance(r.get("numeros"), str) else r.get("numeros")
    metricas = json.loads(r.get("metricas")) if isinstance(r.get("metricas"), str) else r.get("metricas") or {}

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
        res = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("tipo", "estatistico")
            .order("indice_palpite")
            .execute()
        )
    except Exception as e:
        print(f"[ERROR] Falha ao consultar palpites estatísticos: {e}")
        return []

    dados = res.data or []

    # 🔹 Conversão defensiva de JSON
    for r in dados:
        r["numeros"] = json.loads(r.get("numeros")) if isinstance(r.get("numeros"), str) else r.get("numeros")
        r["metricas"] = json.loads(r.get("metricas")) if isinstance(r.get("metricas"), str) else r.get("metricas") or {}

    return dados
