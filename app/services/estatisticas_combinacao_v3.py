from app.services.supabase_service import get_supabase
from collections import defaultdict
from typing import Dict, Tuple
import json

# ======================================================
# Métricas Estruturais Otimizadas
# ======================================================

def extrair_metricas_jogo(nums):
    """
    Extrai o DNA estrutural de uma combinação de 15 números.
    Utilizado para identificar padrões que se repetem no histórico.
    """
    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)
    # Lista de primos entre 1 e 25
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})

    # Distribuição por linhas (1-5, 6-10, 11-15, 16-20, 21-25)
    linhas = [0, 0, 0, 0, 0]
    for n in nums:
        idx = (n - 1) // 5
        if 0 <= idx < 5:
            linhas[idx] += 1

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "linhas": tuple(linhas)
    }

# ======================================================
# Aprendizado Dinâmico via Histórico Real (Gabarito 2026)
# ======================================================

def calcular_score_combinacoes_reais(limite_concursos: int = 1000) -> Dict[Tuple, float]:
    """
    Aprende a probabilidade de acerto analisando a frequência dos últimos 
    1000 resultados oficiais da Lotofácil.
    """
    supabase = get_supabase()

    # 1. Busca os últimos resultados oficiais (Gabarito Real)
    print(f"📊 Analisando os últimos {limite_concursos} concursos oficiais para aprendizado...")
    
    try:
        res = (
            supabase
            .table("lotofacil_concursos")
            .select("dezenas")
            .order("concurso", desc=True)
            .limit(limite_concursos)
            .execute()
        )
    except Exception as e:
        print(f"❌ Erro na conexão com Supabase: {e}")
        return {}

    if not res.data:
        print("⚠️ Histórico real não encontrado no banco. Usando fallback teórico.")
        # Fallback para não travar o gerador em caso de banco vazio
        return {(180, 8, 5, (3, 3, 3, 3, 3)): 1.0}

    frequencia_padroes = defaultdict(int)
    
    # 2. Mapeia a recorrência de cada padrão estrutural nos últimos 1000 sorteios
    for r in res.data:
        try:
            # Tratamento resiliente das dezenas (pode vir como string JSON ou lista)
            raw_dezenas = r["dezenas"]
            if isinstance(raw_dezenas, str):
                nums = json.loads(raw_dezenas)
            else:
                nums = raw_dezenas
            
            # Converte para inteiros e ordena
            nums = sorted([int(n) for n in nums])
            
            if len(nums) != 15:
                continue

            m = extrair_metricas_jogo(nums)
            
            # Chave de Identidade do Jogo:
            # (Soma Arredondada, Qtd Pares, Qtd Primos, Distribuição de Linhas)
            chave = (
                round(m["soma"] / 10) * 10,
                m["pares"],
                m["primos"],
                m["linhas"]
            )
            frequencia_padroes[chave] += 1
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Pula registros malformados sem interromper o aprendizado
            continue

    # 3. Normalização dos Scores (0.0 a 1.0)
    if not frequencia_padroes:
        return {}

    max_ocorrencias = max(frequencia_padroes.values())
    
    # Atribui score proporcional à frequência (ex: padrão mais comum = 1.0)
    scores_finais = {
        k: round(v / max_ocorrencias, 6)
        for k, v in frequencia_padroes.items()
    }

    print(f"✅ Aprendizado 2026 concluído: {len(scores_finais)} padrões identificados em {len(res.data)} concursos.")
    return scores_finais

# Mantém a compatibilidade com chamadas de outras versões
calcular_score_combinacoes = calcular_score_combinacoes_reais

