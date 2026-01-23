from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

def identificar_padroes_elite():
    # Obtém o dicionário de scores baseado nos últimos 1000 jogos
    scores = calcular_score_combinacoes_reais(1000)
    
    # Filtra apenas os padrões que possuem score significativo 
    # (Padrões que apareceram mais de uma vez terão score > 1/max_freq)
    padroes_elite = {k: v for k, v in scores.items() if v > 0.05}
    
    # Ordena pelos melhores scores
    ranking = sorted(padroes_elite.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n💎 FORAM IDENTIFICADOS {len(ranking)} PADRÕES DE ELITE:\n")
    for i, (chave, score) in enumerate(ranking, 1):
        print(f"{i}º | Score: {score:.4f} | Chave: {chave}")
        # Formato da chave: (Soma, Pares, Primos, Linhas)

if __name__ == "__main__":
    identificar_padroes_elite()
