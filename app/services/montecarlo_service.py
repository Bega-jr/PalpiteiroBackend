import numpy as np

# =========================================================
# MONTE CARLO COM RECÊNCIA
# =========================================================
def simular_probabilidade_jogo(
    jogo,
    historico=None,
    simulacoes=400,
    expoente_recencia=2.0,  # Substitui o peso fixo para controlar a curva
    **kwargs
):
    # Fallback seguro para histórico vazio ou nulo
    if not historico:
        return 0.65  

    # Garante o tamanho máximo da janela baseado nas simulações
    janela = historico[-simulacoes:]
    total_elementos = len(janela)

    if total_elementos == 0:
        return 0.0

    resultados = []
    pesos = []

    # Processamento em lote dos acertos e geração de pesos
    for i, concurso in enumerate(janela):
        dezenas = concurso.get("numeros", [])
        acertos = len(set(jogo) & set(dezenas))
        resultados.append(acertos)
        
        # Peso progressivo baseado na posição na janela (evita divisão por zero)
        proporcao = (i + 1) / total_elementos
        pesos.append(proporcao ** expoente_recencia)

    # Convertendo para arrays NumPy para eficiência matemática
    resultados = np.array(resultados)
    pesos = np.array(pesos)

    # Média e Desvio Padrão Ponderados pela recência
    media_ponderada = np.average(resultados, weights=pesos)
    
    # Variância ponderada para um cálculo estritamente correto da estabilidade
    variancia_ponderada = np.average((resultados - media_ponderada)**2, weights=pesos)
    std_ponderado = np.sqrt(variancia_ponderada)

    # Cálculo do Score (Pesos ajustados conforme sua nova regra)
    estabilidade = 1 - min(std_ponderado / 6.0, 1.0)
    score = (media_ponderada / 15.0) * 0.78 + (estabilidade * 0.22)

    # Bônus por consistência de alta performance na janela (11 ou mais acertos)
    acertos_altos = np.sum(resultados >= 11)
    if acertos_altos > 8:
        score *= 1.08

    return round(float(score), 6)
