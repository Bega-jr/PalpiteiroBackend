from app.core.supabase import supabase
from uuid import UUID
from typing import List
from app.schemas.historico_schema import HistoricoCreate, HistoricoRead

# ==========================================
# REGISTRAR JOGO
# ==========================================
def registrar_jogo(user_id: UUID, jogo: HistoricoCreate) -> HistoricoRead:
    """
    Salva um jogo no histórico vinculado ao usuário.
    """
    dados = {
        "user_id": str(user_id),
        "numeros": jogo.numeros,
        "tipo": jogo.tipo.value,
        "score_medio": jogo.score_medio,
        "score_final": jogo.score_final,
        "penalidade_sequencia": jogo.penalidade_sequencia,
        "concurso_referente": jogo.concurso_alvo,
        "valor_aposta": jogo.valor_aposta,
        "premio": 0.0
    }

    try:
        res = supabase.table("historico_jogos").insert(dados).execute()
        if not res.data:
            raise Exception("Erro ao salvar jogo")
        # Retorna o primeiro item da lista gerada pelo insert
        return HistoricoRead(**res.data[0])
    except Exception as e:
        raise Exception(f"Falha ao registrar jogo: {e}")

# ==========================================
# LISTAR HISTÓRICO
# ==========================================
def listar_historico(user_id: UUID) -> List[HistoricoRead]:
    try:
        res = (
            supabase.table("historico_jogos")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        if not res.data:
            return []
        return [HistoricoRead(**j) for j in res.data]
    except Exception as e:
        return []

# ==========================================
# RESUMO FINANCEIRO
# ==========================================
def resumo_financeiro(user_id: UUID):
    jogos = listar_historico(user_id)
    total_apostado = sum(j.valor_aposta for j in jogos)
    total_jogos = len(jogos)
    return {
        "total_jogos": total_jogos,
        "total_apostado": total_apostado,
    }

# ==========================================
# FUNÇÃO PARA ESTATÍSTICAS (ESSENCIAL PARA O DEPLOY)
# ==========================================
def _carregar_historico():
    """
    Carrega o histórico global de resultados para cálculos de estatísticas.
    Esta função resolve o erro ImportError no estatisticas_service.py.
    """
    try:
        # Busca resultados oficiais do banco
        res = (
            supabase.table("historico_resultados")
            .select("concurso, data_sorteio, numeros")
            .order("concurso", desc=False)
            .execute()
        )
        
        if not res.data:
            return []
            
        return [
            {
                "concurso": r["concurso"],
                "data": r["data_sorteio"],
                "numeros": r["numeros"]
            }
            for r in res.data
        ]
    except Exception as e:
        print(f"Erro ao carregar histórico base: {e}")
        return []
