from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas_dashboard():
    # Hoje: 2026-01-02
    hoje = date.today().isoformat()

    try:
        # 1. Busca estatísticas individuais por número
        res_numeros = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score") \
            .eq("data_referencia", hoje) \
            .execute()

        # 2. Busca resumo diário (estatisticas_diarias_v2)
        res_diarias = supabase.table("estatisticas_diarias_v2") \
            .select("*") \
            .eq("data_referencia", hoje) \
            .limit(1) \
            .execute()

        # Verifica se há dados em ao menos uma das tabelas
        if not res_numeros.data and not res_diarias.data:
            return {
                "mensagem": "Nenhum dado encontrado para a data de hoje.",
                "data_referencia": hoje,
                "estatisticas": [],
                "analise": {},
                "ciclo": {}
            }

        # Extrai o primeiro registro de diárias (ou um dicionário vazio)
        # Usamos .data[0] pois o .limit(1) retorna uma lista
        dados_diarios = res_diarias.data[0] if res_diarias.data else {}

        # Função auxiliar para converter valores numéricos do Supabase (que vêm como String)
        def safe_float(valor, default=0.0):
            try:
                return float(valor) if valor is not None else default
            except (ValueError, TypeError):
                return default

        # Processamento de médias (conversão necessária conforme seu SQL)
        m_soma = safe_float(dados_diarios.get("media_soma"))
        m_pares = safe_float(dados_diarios.get("media_pares"), 7.2)
        
        # Recupera as listas de números (conforme nomes exatos das colunas no seu SQL)
        atrasados = dados_diarios.get("numeros_atrasados") or []
        quentes = dados_diarios.get("numeros_quentes") or []
        frios = dados_diarios.get("numeros_frios") or []

        return {
            "estatisticas": res_numeros.data or [],
            "analise": {
                "soma_media": m_soma,
                "pares_media": m_pares,
                "impares_media": round(15 - m_pares, 1),
                "primos_media": 0.0,  # Coluna não existe no seu banco, mantida como 0
                "faixa_pares": dados_diarios.get("faixa_pares", {}),
                "sequencias_comuns": dados_diarios.get("sequencias_comuns", []),
                "data_referencia": hoje,
            },
            "ciclo": {
                "faltam": sorted(atrasados),
                "total_faltam": len(atrasados),
                "numeros_quentes": quentes,
                "numeros_frios": frios
            }
        }

    except Exception as e:
        # Log detalhado para depuração no terminal
        print(f"Erro ao processar dashboard: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao carregar estatísticas do banco: {str(e)}"
        )

# --- Endpoints de Compatibilidade ---

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

@router.get("/ciclo")
def get_ciclo():
    hoje = date.today().isoformat()
    try:
        response = supabase.table("estatisticas_diarias_v2") \
            .select("numeros_atrasados, numeros_frios") \
            .eq("data_referencia", hoje) \
            .limit(1) \
            .execute()
        
        dados = response.data[0] if response.data else {}
        faltam = dados.get("numeros_atrasados") or dados.get("numeros_frios") or []
        
        return {
            "faltam": sorted(faltam), 
            "total_faltam": len(faltam),
            "data_referencia": hoje
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
