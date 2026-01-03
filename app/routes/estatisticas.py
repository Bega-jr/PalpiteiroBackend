from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])


@router.get("/")
def get_estatisticas_dashboard():
    hoje = date.today().isoformat()

    try:
        # 🔹 Fonte ÚNICA de dados
        response = (
            supabase
            .table("estatisticas_diarias_v2")
            .select("*")
            .eq("data_referencia", hoje)
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Estatísticas ainda não geradas para {hoje}"
            )

        dados = response.data[0]

        # Conversão segura
        def safe_float(valor, default=0.0):
            try:
                return float(valor)
            except (TypeError, ValueError):
                return default

        media_pares = safe_float(dados.get("media_pares"))
        numeros_atrasados = dados.get("numeros_atrasados") or []

        return {
            "estatisticas": [],  # Mantido por compatibilidade visual no frontend
            "analise": {
                "soma_media": safe_float(dados.get("media_soma")),
                "pares_media": media_pares,
                "impares_media": round(15 - media_pares, 1),
                "primos_media": safe_float(dados.get("media_primos")),
                "faixa_pares": dados.get("faixa_pares", {}),
                "sequencias_comuns": dados.get("sequencias_comuns", []),
                "data_referencia": hoje
            },
            "ciclo": {
                "faltam": sorted(numeros_atrasados),
                "total_faltam": len(numeros_atrasados),
                "numeros_quentes": dados.get("numeros_quentes", []),
                "numeros_frios": dados.get("numeros_frios", [])
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"[ERRO ESTATISTICAS] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao carregar estatísticas"
        )
