from fastapi import APIRouter, HTTPException
from datetime import date
from typing import List
from app.core.supabase import supabase
from postgrest.exceptions import APIError

# Se você tiver schemas, mantenha-os. Caso contrário, pode remover ou ajustar
# from app.schemas.historico_schema import DashboardEstatisticas, EstatisticaNumero

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas_dashboard():
    """
    Rota principal do dashboard de estatísticas.
    Lê dados pré-calculados do Supabase e retorna no formato esperado pelo frontend React.
    """
    hoje = date.today()

    try:
        # 1. Estatísticas por número (com score)
        response_numeros = (
            supabase.table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .eq("data_referencia", hoje)
            .execute()
        )

        estatisticas = response_numeros.data or []

        if not estatisticas:
            # Fallback para o último registro disponível
            fallback_numeros = (
                supabase.table("estatisticas_numeros")
                .select("numero, frequencia, atraso, score")
                .order("data_referencia", desc=True)
                .limit(25)
                .execute()
            )
            estatisticas = fallback_numeros.data or []

        # 2. Resumo diário consolidado
        response_diarias = (
            supabase.table("estatisticas_diarias_v2")
            .select("*")
            .eq("data_referencia", hoje)
            .single()
            .execute()
        )

        diarias = response_diarias.data if response_diarias.data else {}

        # Monta o objeto final compatível com o frontend
        dashboard = {
            "estatisticas": estatisticas,
            "analise": {
                "soma_media": diarias.get("media_soma", 0.0),
                "pares_media": diarias.get("media_pares", 7.2),
                "impares_media": round(15 - diarias.get("media_pares", 7.2), 1),
                "primos_media": diarias.get("media_primos", 0.0),  # se adicionar no script
                "data_referencia": hoje.isoformat(),
            },
            "ciclo": {
                "faltam": diarias.get("numeros_atrasados", []) or diarias.get("numeros_frios", []),
                "total_faltam": len(diarias.get("numeros_atrasados", []) or diarias.get("numeros_frios", [])),
            }
        }

        return dashboard

    except APIError as e:
        print("Erro Supabase no dashboard:", e)
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco de dados.")
    except Exception as e:
        print("Erro inesperado no dashboard:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao gerar estatísticas.")


# Mantém compatibilidade com chamadas antigas
@router.get("/score")
def get_estatisticas_score_apenas():
    hoje = date.today()
    try:
        response = (
            supabase.table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .eq("data_referencia", hoje)
            .execute()
        )
        dados = response.data or []
        if not dados:
            fallback = (
                supabase.table("estatisticas_numeros")
                .select("numero, frequencia, atraso, score")
                .order("data_referencia", desc=True)
                .limit(25)
                .execute()
            )
            dados = fallback.data or []
        return dados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ciclo")
def get_numeros_ciclo():
    hoje = date.today()
    try:
        response = (
            supabase.table("estatisticas_diarias_v2")
            .select("numeros_atrasados, numeros_frios")
            .eq("data_referencia", hoje)
            .single()
            .execute()
        )
        diarias = response.data if response.data else {}
        faltam = diarias.get("numeros_atrasados") or diarias.get("numeros_frios") or []
        return {"faltam": sorted(faltam), "total_faltam": len(faltam)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))