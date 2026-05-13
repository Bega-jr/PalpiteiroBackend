import sys
import json
import random
import itertools
import numpy as np
import pytz

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

from scripts.processamento_diario_lotofacil import (
    carregar_historico,
    extrair_estrutura
)

# ======================================================
# CONFIG
# ======================================================
VERSAO = "v15.7-premium-estrutural"
QTD_FINAL = 7
MAX_TENTATIVAS = 120000

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15, 16, 20,
    21, 22, 23, 24, 25
}

# ======================================================
# AUX / FILTROS
# ======================================================
def media_segura(v, f=0.5):
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if len(v) > 0 else f


def calcular_filtros(nums, ultimo):
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in PRIMOS)
    moldura = sum(1 for n in nums if n in MOLDURA)
    soma = sum(nums)
    repetidos = len(set(nums) & set(ultimo))

    seq_max = atual = 1
    for i in range(len(nums) - 1):
        if nums[i + 1] == nums[i] + 1:
            atual += 1
            seq_max = max(seq_max, ... if atual > seq_max else seq_max)
        else:
            atual = 1

    return {
        "pares": pares,
        "primos": primos,
        "moldura": moldura,
        "soma": soma,
        "repetidos": repetidos,
        "seq_max": seq_max
    }


def validar(f, linhas):
    return (
        165 <= f["soma"] <= 210 and
        7 <= f["pares"] <= 9 and
        4 <= f["primos"] <= 7 and
        9 <= f["moldura"] <= 12 and
        8 <= f["repetidos"] <= 10 and
        f["seq_max"] <= 5 and           # Padrão estatístico realista
        max(linhas) <= 6                # Evita acúmulo excessivo em uma única linha
    )

# ======================================================
# SCORE COM DISPERSÃO NÃO-LINEAR (FIM DOS EMPATES)
# ======================================================
def score(j, base):
    s1 = media_segura([base.get((n,), 0.5) for n in j])
    s2 = media_segura([base.get(tuple(sorted(p)), 0.5) for p in itertools.combinations(j, 2)])
    s3 = media_segura([base.get(tuple(sorted(t)), 0.5) for t in itertools.combinations(j, 3)])

    score_combinado = (s1 * 0.25) + (s2 * 0.35) + (s3 * 0.40)
    
    # Diferencia as casas decimais finais para quebrar o achatamento do TOP 7
    return float(np.tanh(score_combinado * 1.8)) if score_combinado > 0 else 0.0


# ======================================================
# RESTAURADO: BÔNUS DE MOLDURA E ESTRUTURA DE LINHAS
# ======================================================
def calcular_bonus_estrutural(estr, mem):
    linhas = estr["linhas"]
    factor = 1.0

    # 1. Análise de distribuição por linhas (Evita blocos vazios ou superlotados)
    if 2 <= max(linhas) <= 4:
        factor *= 1.08  # Excelente distribuição lateral
    elif max(linhas) >= 6:
        factor *= 0.92  # Penaliza concentração excessiva

    # 2. Integração com a Memória Ativa do Supabase
    if mem:
        score_real = float(mem.get("score_medio_real", 0))
        vezes = int(mem.get("vezes_gerado", 0))
        
        factor += min(score_real * 0.04, 0.12)  # Bonifica cenários de alta performance real
        factor -= min(vezes * 0.01, 0.08)       # Penaliza exaustão por repetição excessiva

    return max(0.80, min(factor, 1.25))


def penalidade_diversidade(jogo):
    return len(set(jogo[:6])) / 100.0


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print(f"🛡️ {VERSAO}")

    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()

    hist = carregar_historico()
    ultimo = hist[-1]["numeros"]
    concurso_ref = int(hist[-1]["concurso"]) + 1

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    memoria_map = {
        m["hash_estrutura"]: m
        for m in supabase.table("memoria_cenarios").select("*").execute().data
    }

    usados = set(tuple(sorted(h["numeros"])) for h in hist)

    candidatos = []
    pool = list(range(1, 26))

    # ==================================================
    # GERAÇÃO CONTROLED
    # ==================================================
    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 5000:
            break

        jogo = sorted(random.sample(pool, 15))

        if tuple(jogo) in usados:
            continue

        f = calcular_filtros(jogo, ultimo)
        estr = extrair_estrutura(jogo)

        if not validar(f, estr["linhas"]):
            continue

        mem = memoria_map.get(estr["hash_estrutura"])

        base = score(jogo, base_scores)
        bonus_estrutural = calcular_bonus_estrutural(estr, mem)
        pen = penalidade_diversidade(jogo)

        # O bônus de linhas e moldura agora atua diretamente no peso do ranking
        score_final = base * fator_global * bonus_estrutural - pen

        candidatos.append({
            "nums": jogo,
            "score": score_final,
            "filtros": f,
            "memoria": bool(mem)
        })

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = []
    for c in candidatos:
        if len(finais) >= QTD_FINAL:
            break

        if len(finais) == 0 or all(len(set(c["nums"]) ^ set(f["nums"])) >= 10 for f in finais):
            finais.append(c)

    # ==================================================
    # OUTPUT & CLEAN SAVE
    # ==================================================
    print("🏆 TOP 7")

    payload = []
    telegram = []

    for i, c in enumerate(finais, 1):
        nums = c["nums"]
        f = c["filtros"]

        linha = f"{i}º | {c['score']:.6f} | {nums}"
        print(linha)
        telegram.append(linha)

        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(nums),
            "pares": f["pares"],
            "impares": 15 - f["pares"],
            "soma_total": f["soma"],
            "processado": False,
            "conferido": False,
            "versao_gerador": VERSAO,
            "metricas": {
                "score": round(c["score"], 6),
                "primos": f["primos"],
                "moldura": f["moldura"],
                "memoria_match": c["memoria"]
            }
        })

    # Abordagem estável Clear & Insert para garantir execução lisa no GitHub Actions
    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    supabase.table("palpites_validos") \
        .insert(payload).execute()

    print("\n📲 TELEGRAM_PAYLOAD_START")
    print("\n".join(telegram))
    print("📲 TELEGRAM_PAYLOAD_END")


if __name__ == "__main__":
    main()

