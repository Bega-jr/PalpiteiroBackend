from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase
import json

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])


def safe_float(valor, default=0.0):
    try:
        if valor is None:
            return default
        return float(valor)
    except (ValueError, TypeError):
        return default


@router.get("/")
def get_estatisticas():
    hoje = date.today().isoformat()

    try:
        # =========================
        # 1. Estatísticas por número
        # =========================
        response_numeros = (
            supabase.table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score, data_referencia")
            .eq("data_referencia", hoje)
            .execute()
        )

        numeros = response_numeros.data or []

        # Fallback automático para última data disponível
        if not numeros:
            fallback = (
                supabase.table("estatisticas_numeros")
                .select("numero, frequencia, atraso, score, data_referencia")
                .order("data_referencia", desc=True)
                .limit(25)
                .execute()
            )
            numeros = fallback.data or []
            if numeros:
                hoje = numeros[0]["data_referencia"]

        # Normalização de tipos + ordenação por score
        numeros = sorted(
            [
                {
                    "numero": int(n["numero"]),
                    "frequencia": int(n["frequencia"]),
                    "atraso": int(n["atraso"]),
                    "score": round(safe_float(n["score"]), 6),
                }
                for n in numeros
            ],
            key=lambda x: x["score"],
            reverse=True,
        )

        # =========================
        # 2. Estatísticas diárias
        # =========================
        response_diario = (
            supabase.table("estatisticas_diarias_v2")
            .select("*")
            .eq("data_referencia", hoje)
            .limit(1)
            .execute()
        )

        if not response_diario.data:
            response_diario = (
                supabase.table("estatisticas_diarias_v2")
                .select("*")
                .order("data_referencia", desc=True)
                .limit(1)
                .execute()
            )

        diario = response_diario.data[0] if response_diario.data else {}

        # =========================
        # 3. Ciclo (números faltantes)
        # =========================
        faltam = diario.get("numeros_atrasados", [])
        if isinstance(faltam, str):
            try:
                faltam = json.loads(faltam)
            except Exception:
                faltam = []

        numeros_frios = diario.get("numeros_frios", [])
        if isinstance(numeros_frios, str):
            try:
                numeros_frios = json.loads(numeros_frios)
            except Exception:
                numeros_frios = []

        ciclo_final = faltam if faltam else numeros_frios

        # =========================
        # 4. Resposta final
        # =========================
        return {
            "estatisticas": numeros,
            "analise": {
                "soma_media": round(safe_float(diario.get("media_soma")), 2),
                "pares_media": round(safe_float(diario.get("media_pares")), 2),
                "impares_media": round(safe_float(diario.get("media_impares")), 2),
                "primos_media": round(safe_float(diario.get("media_primos")), 2),
                "data_referencia": hoje,
            },
            "ciclo": {
                "faltam": ciclo_final,
                "total_faltam": len(ciclo_final),
            },
            "meta": {
                "data_referencia": hoje,
                "total_numeros": len(numeros),
                "fonte": "estatisticas_diarias_v2",
            },
        }

    except Exception as e:
        print(f"❌ Erro no endpoint /estatisticas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao carregar estatísticas")
