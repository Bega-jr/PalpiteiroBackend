from app.services.supabase_service import get_supabase
from collections import defaultdict
from typing import Dict, Tuple
import json

# ======================================================
# Pesos por faixa de acerto
# ======================================================
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00

# ======================================================
# Métricas estruturais
# ======================================================
def extrair_metricas_jogo(nums):
    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})

    linhas = (
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    )

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "linhas": linhas
    }

# ======================================================
# Score REAL por combinação estrutural
# ======================================================
def calcular_score_combinacoes_reais(
    ano: int = 2026
) -> Dict[Tuple, float]:
    """
    Aprende score estrutural REAL a partir de palpites
    já conferidos individualmente na tabela palpites_validos.
    """

    supabase = get_supabase()

    # Tenta buscar os dados. A coluna 'acertos' deve existir no banco.
    res = (
        supabase
        .table("palpites_validos")
        .select("numeros, acertos")
        .gte("data_referencia", f"{ano}-01-01")
        .lte("data_referencia", f"{ano}-12-31")
        .execute()
    )

    if not res.data:
        print(f"⚠️ Nenhuns dados encontrados para o ano {ano}")
        return {}

    scores = defaultdict(float)
    ocorrencias = defaultdict(int)

    for r in res.data:
        # Pula palpites sem acertos registrados ou abaixo do prêmio mínimo
        acertos = r.get("acertos")
        if acertos is None or acertos < 11:
            continue

        # Tratamento para o formato do campo 'numeros' (remove aspas extras se existirem)
        try:
            raw_nums = r["numeros"]
            if isinstance(raw_nums, str):
                # Remove aspas duplas escapadas se houver ex: "\" [1,2] \"" -> [1,2]
                nums = json.loads(raw_nums.strip('"'))
            else:
                nums = raw_nums
        except Exception as e:
            print(f"❌ Erro ao decodificar números: {e}")
            continue

        m = extrair_metricas_jogo(nums)

        # Cálculo do impacto baseado no peso da faixa de acerto
        impacto = (
            (1 if acertos == 11 else 0) * PESO_11 +
            (1 if acertos == 12 else 0) * PESO_12 +
            (1 if acertos == 13 else 0) * PESO_13 +
            (1 if acertos == 14 else 0) * PESO_14 +
            (1 if acertos == 15 else 0) * PESO_15
        )

        # A chave agrupa jogos com características similares (Soma arredondada, Pares, Primos, Distribuição)
        chave = (
            round(m["soma"] / 10) * 10,
            m["pares"],
            m["primos"],
            tuple(m["linhas"])  # Convertido para tuple para ser hashable no dict
        )

        scores[chave] += impacto
        ocorrencias[chave] += 1

    # Retorna a média de impacto por tipo de combinação
    return {
        k: round(scores[k] / ocorrencias[k], 6)
        for k in scores
    }

# ======================================================
# BACKWARD COMPATIBILITY
# ======================================================
calcular_score_combinacoes = calcular_score_combinacoes_reais

