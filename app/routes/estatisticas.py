from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase
from postgrest.exceptions import APIError

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas_dashboard():
    # Converte para string 'YYYY-MM-DD' para evitar problemas de tipos no Supabase
    hoje = date.today().isoformat()

    try:
        # 1. Busca estatísticas por número
        response_numeros = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score") \
            .eq("data_referencia", hoje) \
            .execute()

        estatisticas = response_numeros.data or []

        # 2. Busca resumo diário
        # Usamos .limit(1) em vez de .single() para evitar que o código quebre 
        # caso os dados de hoje ainda não tenham sido gerados.
        response_diarias = supabase.table("estatisticas_diarias_v2") \
            .select("*") \
            .eq("data_referencia", hoje) \
            .limit(1) \
            .execute()

        # Se houver dados, pega o primeiro item; caso contrário, usa um dict vazio
        diarias = response_diarias.data[0] if response_diarias.data else {}

        # 3. Tratamento de lógica para evitar erros de None/Missing
        media_pares = diarias.get("media_pares", 7.2)
        
        # Tenta pegar atrasados, senão frios, senão lista vazia
        faltam = diarias.get("numeros_atrasados") or diarias.get("numeros_frios") or []

        # Se não houver nenhum dado no banco para hoje
        if not estatisticas and not diarias:
            return {
                "status": "warning",
                "mensagem": f"Nenhum dado encontrado para a data {hoje}",
                "data_referencia": hoje
            }

        return {
            "estatisticas": estatisticas,
            "analise": {
                "soma_media": diarias.get("media_soma", 0.0),
                "pares_media": media_pares,
                "impares_media": 15 - media_pares,
                "primos_media": diarias.get("media_primos", 0.0),
                "data_referencia": hoje,
            },
            "ciclo": {
                "faltam": sorted(faltam),
                "total_faltam": len(faltam),
            }
        }

    except Exception as e:
        # Log detalhado no terminal para diagnóstico
        print(f"Erro no endpoint /estatisticas: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao carregar estatísticas: {str(e)}"
        )

# Endpoint de Score (Mantido por compatibilidade)
@router.get("/score")
def get_score():
    hoje = date.today().isoformat()
    try:
        response = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score") \
            .eq("data_referencia", hoje) \
            .execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de Ciclo (Mantido por compatibilidade)
@router.get("/ciclo")
def get_ciclo():
    hoje = date.today().isoformat()
    try:
        response = supabase.table("estatisticas_diarias_v2") \
            .select("numeros_atrasados, numeros_frios") \
            .eq("data_referencia", hoje) \
            .limit(1) \
            .execute()
        
        diarias = response.data[0] if response.data else {}
        faltam = diarias.get("numeros_atrasados") or diarias.get("numeros_frios") or []
        
        return {
            "faltam": sorted(faltam), 
            "total_faltam": len(faltam),
            "data_referencia": hoje
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
