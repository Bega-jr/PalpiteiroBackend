from uuid import UUID
from typing import List

from app.services.supabase_service import get_supabase

def registrar_jogo(user_id: UUID, jogo) -> dict:
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

    res = get_supabase().table("saved_games").insert(dados).execute()
    if not res.data:
        raise RuntimeError("Supabase não retornou o jogo criado.")
    return res.data[0]

# ==========================================
# LISTAR HISTÓRICO (SAVED_GAMES)
# ==========================================
def listar_historico(user_id: UUID, page: int = 1, limit: int = 50) -> List[dict]:
    """
    Lista o histórico de jogos do usuário na tabela saved_games.
    """
    if page < 1 or limit < 1:
        raise ValueError("page e limit devem ser positivos.")

    offset = (page - 1) * limit
    res = (
        get_supabase().table("saved_games")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data or []

# ==========================================
# RESUMO FINANCEIRO
# ==========================================
def resumo_financeiro(user_id: UUID):
    page_size = 1000
    offset = 0
    total_jogos = 0
    total_apostado = 0.0
    total_premio = 0.0

    while True:
        response = (
            get_supabase().table("saved_games")
            .select("valor_aposta, premio, conferido")
            .eq("user_id", str(user_id))
            .range(offset, offset + page_size - 1)
            .execute()
        )
        jogos = response.data or []

        total_jogos += len(jogos)
        total_apostado += sum(float(jogo.get("valor_aposta") or 0) for jogo in jogos)
        total_premio += sum(
            float(jogo.get("premio") or 0)
            for jogo in jogos
            if jogo.get("conferido", False)
        )

        if len(jogos) < page_size:
            break
        offset += page_size

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
    res = (
        get_supabase().table("lotofacil_concursos")
        .select("concurso, data, dezenas")
        .order("concurso", desc=False)
        .execute()
    )

    if not res.data:
        return []

    return [
        {
            "concurso": row["concurso"],
            "data": row["data"],
            "numeros": row["dezenas"],
        }
        for row in res.data
    ]

