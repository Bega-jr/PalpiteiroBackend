from app.core.supabase import supabase
from app.services.estatisticas_service import carregar_dados_para_estatistica
import pandas as pd

def processar_premios(acertos: int) -> float:
    """Retorna o valor do prêmio baseado nos acertos da Lotofácil (Valores 2025)."""
    premios = {
        11: 6.0,
        12: 12.0,
        13: 30.0,
        14: 1500.0, # Valor aproximado, varia por concurso
        15: 500000.0 # Valor aproximado, varia por concurso
    }
    return premios.get(acertos, 0.0)

def conferir_jogos_do_dia():
    """
    Busca o último resultado no CSV e confere com os jogos salvos no banco.
    """
    # 1. Pega o último resultado real do CSV
    historico_real = carregar_dados_para_estatistica()
    if not historico_real:
        return "Erro: CSV de resultados está vazio."
    
    ultimo_sorteio = historico_real[-1]
    concurso_atual = ultimo_sorteio['concurso']
    dezenas_sorteadas = set(ultimo_sorteio['numeros'])

    # 2. Busca no Supabase todos os jogos salvos para este concurso que ainda não foram conferidos
    # Filtramos por concurso_alvo e onde acertos é nulo (ou status pendente)
    jogos_pendentes = supabase.table("historico_jogos")\
        .select("*")\
        .eq("concurso_alvo", concurso_atual)\
        .execute()

    if not jogos_pendentes.data:
        return f"Nenhum jogo pendente para o concurso {concurso_atual}."

    total_conferidos = 0
    
    # 3. Itera e compara
    for jogo in jogos_pendentes.data:
        dezenas_jogo = set(jogo['numeros'])
        acertos = len(dezenas_jogo & dezenas_sorteadas)
        valor_premio = processar_premios(acertos)

        # 4. Atualiza o registro no banco com o resultado
        supabase.table("historico_jogos").update({
            "acertos": acertos,
            "valor_premio": valor_premio,
            "conferido": True
        }).eq("id", jogo["id"]).execute()
        
        total_conferidos += 1

    return f"Sucesso: {total_conferidos} jogos conferidos para o concurso {concurso_atual}."
