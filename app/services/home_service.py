# app/services/home_service.py
import json
from app.services.supabase_service import get_supabase


def obter_dados_home():
    supabase = get_supabase()

    response = (
        supabase
        .table("vw_lotofacil_stats")
        .select("*")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    row = response.data[0]

    # 🔧 TRATAMENTOS IMPORTANTES

    # dezenas → number[]
    row["dezenas"] = [int(d) for d in row.get("dezenas", [])]

    # municipios → array real
    municipios_raw = row.get("municipios")
    if isinstance(municipios_raw, str):
        try:
            row["municipios"] = json.loads(municipios_raw)
        except Exception:
            row["municipios"] = []
    else:
        row["municipios"] = municipios_raw or []

    # normalizações opcionais
    row["arrecadacao"] = float(row["arrecadacao"] or 0)
    row["estimativa_proximo"] = float(row["estimativa_proximo"] or 0)

    return row
