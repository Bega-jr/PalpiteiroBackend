from app.services.supabase_service import get_supabase
from collections import defaultdict
from typing import Dict, Tuple
import json
import numpy as np

# ======================================================
# MÉTRICAS ESTRUTURAIS
# ======================================================
def extrair_metricas_jogo(nums):
    """
    Extrai estrutura estatística do jogo (15 números)
    """

    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})

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
# SCORE DE COMBINAÇÕES REAIS (VERSÃO ESTÁVEL)
# ======================================================
def calcular_score_combinacoes_reais(limite_concursos: int = 1000):
    """
    Aprende padrões reais sem distorcer distribuição.
    Retorna:
        - base_scores (estrutura geral)
        - rec_scores (recência leve)
    """

    supabase = get_supabase()

    print(f"📊 Aprendizado: últimos {limite_concursos} concursos")

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
        print(f"❌ erro Supabase: {e}")
        return {}, {}

    if not res.data:
        print("⚠️ fallback ativado (dados vazios)")
        return {}, {}

    freq_base = defaultdict(int)
    freq_rec = defaultdict(int)

    total = len(res.data)

    # ==================================================
    # LEITURA DOS CONCURSOS
    # ==================================================
    for idx, r in enumerate(res.data):

        try:
            raw = r["dezenas"]

            if isinstance(raw, str):
                nums = json.loads(raw)
            else:
                nums = raw

            nums = sorted(int(n) for n in nums)

            if len(nums) != 15:
                continue

            m = extrair_metricas_jogo(nums)

            # CHAVE ESTÁVEL (CRÍTICO)
            chave = (
                round(m["soma"] / 10) * 10,
                m["pares"],
                m["primos"],
                m["linhas"]
            )

            freq_base[chave] += 1

            # recência ponderada (últimos concursos valem mais)
            peso_rec = 1 + (1 - (idx / total))
            freq_rec[chave] += peso_rec

        except Exception:
            continue

    # ======================================================
    # NORMALIZAÇÃO SEGURA
    # ======================================================
    if not freq_base:
        return {}, {}

    max_base = max(freq_base.values())
    max_rec = max(freq_rec.values())

    base_scores = {
        k: v / max_base
        for k, v in freq_base.items()
    }

    rec_scores = {
        k: v / max_rec
        for k, v in freq_rec.items()
    }

    print(
        f"✅ Aprendizado concluído: "
        f"{len(base_scores)} padrões"
    )

    return base_scores, rec_scores

# ======================================================
# COMPATIBILIDADE LEGACY
# ======================================================
calcular_score_combinacoes = calcular_score_combinacoes_reais

