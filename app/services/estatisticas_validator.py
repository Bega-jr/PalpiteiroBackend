from app.services.estatisticas_service import (
    calcular_metricas_jogo, 
    obter_ultimo_resultado
)

NUMEROS_POR_JOGO = 15

def validar_estrutura(jogo):
    jogo_unico = set(jogo)
    return {
        "faltantes": max(0, NUMEROS_POR_JOGO - len(jogo_unico)),
        "repetidos": len(jogo) != len(jogo_unico),
        "total": len(jogo_unico)
    }

def validar_jogo(jogo):
    metricas = calcular_metricas_jogo(jogo)
    ultimo_res = obter_ultimo_resultado()
    
    # Cálculo de Repetidos do Anterior
    repetidos_anterior = len(set(jogo) & set(ultimo_res)) if ultimo_res else 9

    # Filtros Profissionais (Baseados em 2025)
    filtro_soma = 170 <= metricas["soma"] <= 220
    filtro_pares = 7 <= metricas["pares"] <= 9
    filtro_primos = 5 <= metricas["primos"] <= 6
    filtro_moldura = 9 <= metricas["moldura"] <= 11
    filtro_repetidos = 8 <= repetidos_anterior <= 10
    filtro_sequencia = metricas["maior_sequencia"] <= 5

    # Um jogo é aprovado se passar na maioria dos filtros essenciais
    aprovado = all([
        filtro_soma, 
        filtro_pares, 
        filtro_primos, 
        filtro_moldura, 
        filtro_repetidos,
        filtro_sequencia
    ])

    return {
        "aprovado": aprovado,
        "metricas": metricas,
        "repetidos_anterior": repetidos_anterior,
        "detalhes_filtros": {
            "soma": filtro_soma,
            "pares": filtro_pares,
            "primos": filtro_primos,
            "moldura": filtro_moldura,
            "repetidos": filtro_repetidos
        }
    }
