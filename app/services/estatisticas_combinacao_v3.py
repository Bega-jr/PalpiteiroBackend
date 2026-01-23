from app.services.supabase_service import get_supabase
from collections import defaultdict
from typing import Dict, Tuple
import json

# ======================================================
# Configurações de Pesos (Baseado em Lógica de Frequência)
# ======================================================

def extrair_metricas_jogo(nums):
    """Extrai o DNA estrutural de uma combinação de 15 números."""
    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})

    linhas = [0, 0, 0, 0, 0]
    for n in nums:
        idx = (n - 1) // 5
        linhas[idx] += 1

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "linhas": tuple(linhas)
    }

# ======================================================
# Aprendizado Dinâmico via Histórico Real (Gabarito)
# ======================================================
def calcular_score_combinacoes_reais(limite_concursos: int = 100) -> Dict[Tuple, float]:
    """
    Analisa os últimos 100 resultados REAIS da Lotofácil para definir
    o score das combinações estruturais. Ideal para início do zero.
    """
    supabase = get_supabase()

    # 1. Busca os últimos resultados oficiais da Caixa
    print(f"📊 Analisando os últimos {limite_concursos} resultados oficiais para aprendizado...")
    res = (
        supabase
        .table("lotofacil_concursos")
        .select("dezenas")
        .order("concurso", desc=True)
        .limit(limite_concursos)
        .execute()
    )

    if not res.data:
        print("⚠️ Histórico real não encontrado. Usando fallback teórico.")
        return {(180, 8, 5, (3, 3, 3, 3, 3)): 1.0}

    frequencia_padroes = defaultdict(int)
    
    # 2. Mapeia a recorrência de cada padrão estrutural
    for r in res.data:
        try:
            # Garante que dezenas sejam uma lista de inteiros
            nums = r["dezenas"]
            if isinstance(nums, str):
                nums = json.loads(nums)
            nums = [int(n) for n in nums]
            
            m = extrair_metricas_jogo(nums)
            
            # Chave: (Soma arredondada, Pares, Primos, Distribuição de Linhas)
            chave = (
                round(m["soma"] / 10) * 10,
                m["pares"],
                m["primos"],
                m["linhas"]
            )
            frequencia_padroes[chave] += 1
        except Exception as e:
            continue

    # 3. Normaliza os scores (0.0 a 1.0) baseados na frequência
    if not frequencia_padroes:
        return {}

    max_ocorrencias = max(frequencia_padroes.values())
    
    scores_finais = {
        k: round(v / max_ocorrencias, 6)
        for k, v in frequencia_padroes.items()
    }

    print(f"✅ Aprendizado concluído: {len(scores_finais)} padrões identificados.")
    return scores_finais

# Compatibilidade com o script de geração
calcular_score_combinacoes = calcular_score_combinacoes_reais

