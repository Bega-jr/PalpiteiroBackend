from typing import List, Dict, Any
import json
from .supabase_service import get_supabase


def _parse_json(valor):
    if valor is None:
        return None
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except Exception:
            return None
    return None


# ==========================================================
# PALPITE FIXO = MAIOR SCORE DO DIA
# ==========================================================
def obter_palpite_fixo_publico() -> Dict[str, Any] | None:
    try:
        supabase = get_supabase()

        # 1️⃣ Descobre a data mais recente
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

        # 2️⃣ Busca o palpite com MAIOR SCORE
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", data_ref)
            .order("metricas->>score", desc=True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return None

        r = resp.data[0]
        r["numeros"] = _parse_json(r.get("numeros"))
        r["metricas"] = _parse_json(r.get("metricas"))

        return r

    except Exception as e:
        print(f"❌ Erro palpite fixo: {repr(e)}")
        return None


# ==========================================================
# PALPITES ESTATÍSTICOS = RESTANTE DO DIA
# ==========================================================
def obter_palpites_estatisticos_publico() -> List[Dict[str, Any]]:
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
            return []

        data_ref = data_resp.data[0]["data_referencia"]

        # 2️⃣ Todos os palpites do dia
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", data_ref)
            .order("indice_palpite")
            .execute()
        )

        registros = []
        for r in resp.data or []:
            r["numeros"] = _parse_json(r.get("numeros"))
            r["metricas"] = _parse_json(r.get("metricas"))
            registros.append(r)

        return registros

    except Exception as e:
        print(f"❌ Erro estatísticos: {repr(e)}")
        return []

