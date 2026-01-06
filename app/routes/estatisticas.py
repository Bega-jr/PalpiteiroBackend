from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase
import json

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])
supabase = get_supabase()


def safe_float(valor, default=0.0):
    try:
        return float(valor) if valor is not None else default
    except Exception:
        return default


def safe_json(valor):
    if not valor:
        return []
    if isinstance(valor, list):
        return valor
    try:
        return json.loads(valor)
    except Exception:
        return []


@router.get("")
def get_estatisticas():
    try:
        resp = (
            supabase
            .table("vw_estatisticas_numeros_atuais")
            .select("*")
            .order("score", desc=True)
            .execute()
        )

        dados = resp.data or []

        if not dados:
            return {
                "estatisticas": [],
                "analise": {},
                "ciclo": {"faltam": [], "total_faltam": 0},
                "meta": {"fonte": "vw_estatisticas_numeros_atuais"}
            }

        ref = dados[0].get("data_referencia")

        estatisticas = [
            {
                "numero": int(d["numero"]),
                "frequencia": int(d["frequencia"]),
                "atraso": int(d["atraso"]),
                "score": round(safe_float(d["score"]), 6),
            }
            for d in dados
        ]

        analise = {
            "soma_media": round(safe_float(dados[0].get("media_soma")), 2),
            "pares_media": round(safe_float(dados[0].get("media_pares")), 2),
            "impares_media": round(safe_float(dados[0].get("media_impares")), 2),
            "primos_media": round(safe_float(dados[0].get("media_primos")), 2),
            "data_referencia": ref,
        }

        faltam = safe_json(dados[0].get("numeros_atrasados"))
        frios = safe_json(dados[0].get("numeros_frios"))

        ciclo_final = faltam if faltam else frios

        return {
            "estatisticas": estatisticas,
            "analise": analise,
            "ciclo": {
                "faltam": ciclo_final,
                "total_faltam": len(ciclo_final),
            },
            "meta": {
                "data_referencia": ref,
                "total_numeros": len(estatisticas),
                "fonte": "vw_estatisticas_numeros_atuais",
            },
        }

    except Exception as e:
        print("❌ ERRO /estatisticas:", e)
        raise HTTPException(
            status_code=500,
            detail="Erro ao carregar estatísticas"
        )
