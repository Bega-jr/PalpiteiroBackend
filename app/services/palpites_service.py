from typing import List, Dict, Any
from app.services.supabase_service import get_supabase


TABELA_PALPITES = "palpites"


def obter_palpite_fixo_publico() -> Dict[str, Any] | None:
    """
    Retorna o palpite fixo (indice_palpite = 0)
    """
    supabase = get_supabase()

    try:
        response = (
            supabase
            .table(TABELA_PALPITES)
            .select("*")
            .eq("indice_palpite", 0)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        registro = response.data[0]

        return {
            "id": registro.get("id"),
            "data_referencia": registro.get("data_referencia"),
            "indice_palpite": registro.get("indice_palpite"),
            "numeros": registro.get("numeros"),
            "soma_total": registro.get("soma_total"),
            "pares": registro.get("pares"),
            "impares": registro.get("impares"),
            "qtd_sequencias": registro.get("qtd_sequencias"),
            "metricas": registro.get("metricas"),
            "filtros_aplicados": registro.get("filtros_aplicados"),
            "tipo": registro.get("tipo"),
            "origem": registro.get("origem"),
        }

    except Exception as e:
        print("❌ Erro ao obter palpite fixo:", e)
        return None


def obter_palpites_estatisticos_publico() -> List[Dict[str, Any]]:
    """
    Retorna todos os palpites estatísticos (indice_palpite >= 1)
    """
    supabase = get_supabase()

    try:
        response = (
            supabase
            .table(TABELA_PALPITES)
            .select("*")
            .gte("indice_palpite", 1)
            .order("indice_palpite")
            .execute()
        )

        if not response.data:
            return []

        palpites = []

        for r in response.data:
            palpites.append({
                "id": r.get("id"),
                "data_referencia": r.get("data_referencia"),
                "indice_palpite": r.get("indice_palpite"),
                "numeros": r.get("numeros"),
                "soma_total": r.get("soma_total"),
                "pares": r.get("pares"),
                "impares": r.get("impares"),
                "qtd_sequencias": r.get("qtd_sequencias"),
                "metricas": r.get("metricas"),
                "filtros_aplicados": r.get("filtros_aplicados"),
                "tipo": r.get("tipo"),
                "origem": r.get("origem"),
            })

        return palpites

    except Exception as e:
        print("❌ Erro ao obter palpites estatísticos:", e)
        return []
