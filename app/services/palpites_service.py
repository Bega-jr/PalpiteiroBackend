import json
from app.services.supabase_service import get_supabase


def _normalizar_json(valor):
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except Exception:
            return {}
    return {}


def _normalizar_array(valor):
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except Exception:
            return []
    return []


def obter_palpite_fixo_publico():
    """
    Retorna o palpite fixo (indice_palpite = 0) mais recente
    com dados normalizados.
    """
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("indice_palpite", 0)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return None

        r = resp.data[0]

        return {
            "data_referencia": r.get("data_referencia"),
            "numeros": _normalizar_array(r.get("numeros")),
            "soma": r.get("soma_total"),
            "pares": r.get("pares"),
            "impares": r.get("impares"),
            "metricas": _normalizar_json(r.get("metricas")),
        }

    except Exception as e:
        print(f"❌ Erro Service Palpite Fixo: {repr(e)}")
        return None


def obter_palpites_estatisticos_publico():
    """
    Retorna os palpites estatísticos da data mais recente
    (indice_palpite > 0), todos normalizados.
    """
    try:
        supabase = get_supabase()

        # Descobre a última data com dados
        data_resp = (
            supabase.table("palpites_validos")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        if not data_resp.data:
            return {"data_referencia": None, "palpites": []}

        ultima_data = data_resp.data[0]["data_referencia"]

        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("data_referencia", ultima_data)
            .gt("indice_palpite", 0)
            .order("indice_palpite", desc=False)
            .execute()
        )

        palpites = []
        for r in resp.data or []:
            metricas = _normalizar_json(r.get("metricas"))

            palpites.append({
                "indice": r.get("indice_palpite"),
                "numeros": _normalizar_array(r.get("numeros")),
                "soma": r.get("soma_total"),
                "pares": r.get("pares"),
                "score": float(metricas.get("score", 0)),
            })

        return {
            "data_referencia": ultima_data,
            "palpites": palpites
        }

    except Exception as e:
        print(f"❌ Erro Service Palpites Estatísticos: {repr(e)}")
        return {"data_referencia": None, "palpites": []}
