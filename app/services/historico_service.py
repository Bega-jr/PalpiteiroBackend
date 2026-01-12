from uuid import UUID
from typing import List, Optional
import json

# Ajuste na importação para usar o serviço centralizado
from app.services.supabase_service import get_supabase
# Ajuste o schema de leitura para o que você usa para saved_games
# from app.schemas.historico_schema import HistoricoCreate, HistoricoRead 
# Supondo um schema SavedGameRead para o retorno

# Inicializa o cliente Supabase corretamente
supabase = get_supabase()

# ==========================================
# REGISTRAR JOGO (SAVED_GAMES)
# ==========================================
# Use o schema de criação da sua tabela saved_games
def registrar_jogo(user_id: UUID, jogo) -> dict: # Retorno alterado para dict
    """
    Salva um jogo na tabela saved_games vinculado ao usuário.
    """
    dados = {
        "user_id": str(user_id),
        "numeros": jogo.numeros,
        "tipo": jogo.tipo.value,
        "concurso_alvo": jogo.concurso_alvo,
        "valor_aposta": jogo.valor_aposta,
        "premio": 0.0,
        "conferido": False, # Adicionado campo conferido
        # Adicione quaisquer outros campos obrigatórios da saved_games aqui (ex: data_referencia)
    }

    try:
        # Tabela correta: saved_games
        res = supabase.table("saved_games").insert(dados).execute()
        if not res.data:
            raise Exception("Erro ao salvar jogo")
        # Retorna o primeiro item da lista gerada pelo insert
        return res.data[0] # Retorno alterado
    except Exception as e:
        raise Exception(f"Falha ao registrar jogo: {e}")

# ==========================================
# LISTAR HISTÓRICO (SAVED_GAMES)
# ==========================================
def listar_historico(user_id: UUID) -> List[dict]: # Retorno alterado para List[dict]
    """
    Lista o histórico de jogos do usuário na tabela saved_games.
    """
    try:
        # Tabela correta: saved_games
        res = (
            supabase.table("saved_games")
            .select("*")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .execute()
        )
        if not res.data:
            return []
        return res.data # Retorno alterado
    except Exception as e:
        # Em produção, você pode querer logar esse erro
        return []

# ==========================================
# RESUMO FINANCEIRO
# ==========================================
def resumo_financeiro(user_id: UUID):
    # Usa a função atualizada que lê de saved_games
    jogos = listar_historico(user_id) 
    total_apostado = sum(j['valor_aposta'] for j in jogos) # Acessa via chave de dict
    total_jogos = len(jogos)
    total_premio = sum(j.get('valor_premio', 0.0) for j in jogos if j.get('conferido', False)) # Soma prêmios conferidos

    return {
        "total_jogos": total_jogos,
        "total_apostado": total_apostado,
        "total_premio_recebido": total_premio
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
        # Tabela correta: lotofacil_concursos (ou a que você usa para resultados oficiais)
        res = (
            supabase.table("lotofacil_concursos")
            .select("concurso, data, dezenas") # Ajuste os nomes das colunas
            .order("concurso", desc=False)
            .execute()
        )
        
        if not res.data:
            return []
            
        return [
            {
                "concurso": r["concurso"],
                "data": r["data"], # Ajuste o nome da coluna de data se necessário
                "numeros": r["dezenas"] # Ajuste o nome da coluna de números se necessário
            }
            for r in res.data
        ]
    except Exception as e:
        print(f"Erro ao carregar histórico base: {e}")
        return []

