from typing import List, Dict, Any
import json
from .supabase_service import get_supabase


def _parse_json_field(valor):
    """
    Garante que campos JSON vindos do Supabase
    sejam sempre dict/list, mesmo se vierem como string.
    """
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
# PALPITE FIXO (indice_palpite = 0)
# ==========================================================
def obter_palpite_fixo_publico() -> Dict[str, Any] | None:
    """
    Retorna o palpite fixo (indice 0) da data mais recente.
    """
    try:
        supabase = get_supabase()

        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("indice_palpite", 0)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return None

        registro = resp.data[0]

        # Normaliza JSON
        registro["numeros"] = _parse_json_field(registro.get("numeros"))
        registro["metricas"] = _parse_json_field(registro.get("metricas"))
        registro["filtros_aplicados"] = _parse_json_field(registro.get("filtros_aplicados"))

        return registro

    except Exception as e:
        print(f"❌ Erro obter_palpite_fixo_publico: {repr(e)}")
        return None


# ==========================================================
# PALPITES ESTATÍSTICOS (indice_palpite > 0)
# ==========================================================
def obter_palpites_estatisticos_publico() -> List[Dict[str, Any]]:
    """
    Retorna todos os palpites estatísticos da data mais recente.
    """
    try:
        supabase = get_supabase()

        # 1️⃣ Descobre a data mais recente com registros
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

        ultima_data = data_resp.data[0]["data_referencia"]

        # 2️⃣ Busca palpites estatísticos dessa data
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", ultima_data)
            .gt("indice_palpite", 0)
            .order("indice_palpite")
            .execute()
        )

        resultados = []

        for r in resp.data or []:
            r["numeros"] = _parse_json_field(r.get("numeros"))
            r["metricas"] = _parse_json_field(r.get("metricas"))
            r["filtros_aplicados"] = _parse_json_field(r.get("filtros_aplicados"))
            resultados.append(r)

        return resultados

    except Exception as e:
        print(f"❌ Erro obter_palpites_estatisticos_publico: {repr(e)}")
        return []
