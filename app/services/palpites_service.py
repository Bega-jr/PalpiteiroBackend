import json
from typing import List, Dict, Any
from .supabase_service import get_supabase

def _parse_json(valor):
    if not valor:
        return {}
    if isinstance(valor, dict):
        return valor
    try:
        return json.loads(valor)
    except Exception:
        return {}

def _parse_array(valor):
    if not valor:
        return []
    if isinstance(valor, list):
        return valor
    try:
        return json.loads(valor)
    except Exception:
        return []

# ======================================================
# PALPITE FIXO = MAIOR SCORE DO DIA (SEGURO)
# ======================================================
def obter_palpite_fixo_publico() -> Dict[str, Any] | None:
    try:
        supabase = get_supabase()
        # 1️⃣ Data mais recente
        data_resp = (
            supabase
            .table("palpites_validos")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        if not data_resp.data:
            return None
        data_ref = data_resp.data[0]["data_referencia"]
        # 2️⃣ Todos os palpites do dia
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", data_ref)
            .execute()
        )
        if not resp.data:
            return None
        # 3️⃣ Encontra o maior score manualmente
        melhor = None
        maior_score = -1
        for r in resp.data:
            metricas = _parse_json(r.get("metricas"))
            score = metricas.get("score", 0)
            if score > maior_score:
                r["metricas"] = metricas
                r["numeros"] = _parse_array(r.get("numeros", "[]"))
                r["filtros_aplicados"] = _parse_array(r.get("filtros_aplicados", "[]"))
                melhor = r
                maior_score = score
        return melhor
    except Exception as e:
        print(f"❌ Erro palpite fixo: {repr(e)}")
        return None

# ======================================================
# PALPITES ESTATÍSTICOS (LISTA DO DIA)
# ======================================================
def obter_palpites_estatisticos_publico() -> List[Dict[str, Any]]:
    try:
        supabase = get_supabase()
        data_resp = (
            supabase
            .table("palpites_validos")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        if not data_resp.data:
            return []
        data_ref = data_resp.data[0]["data_referencia"]
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", data_ref)
            .order("indice_palpite")
            .execute()
        )
        resultados = []
        for r in resp.data or []:
            r["metricas"] = _parse_json(r.get("metricas"))
            r["numeros"] = _parse_array(r.get("numeros", "[]"))
            r["filtros_aplicados"] = _parse_array(r.get("filtros_aplicados", "[]"))
            resultados.append(r)
        return resultados
    except Exception as e:
        print(f"❌ Erro estatísticos: {repr(e)}")
        return []
