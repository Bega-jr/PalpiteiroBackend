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

VERSAO = "v15.2-blindada-logs"
QTD_FINAL = 7
MAX_TENTATIVAS = 150000

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

MOLDURA = {
    1,2,3,4,5,
    6,10,11,15,16,20,
    21,22,23,24,25
}

# ======================================================
# UTILS
# ======================================================

def media_segura(v, f=0.5):
    return float(np.mean(v)) if v else f


def log(msg):
    print(f"[v15.2] {msg}")


def calcular_filtros(nums, ultimo):
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in PRIMOS)
    moldura = sum(1 for n in nums if n in MOLDURA)
    soma = sum(nums)
    repetidos = len(set(nums) & set(ultimo))

    seq_max = atual = 1
    for i in range(len(nums) - 1):
        if nums[i+1] == nums[i] + 1:
            atual += 1
            seq_max = max(seq_max, atual)
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


def validar(f):
    return (
        165 <= f["soma"] <= 210 and
        7 <= f["pares"] <= 9 and
        4 <= f["primos"] <= 7 and
        9 <= f["moldura"] <= 12 and
        8 <= f["repetidos"] <= 10 and
        f["seq_max"] <= 4
    )


def score(j, base):
    s1 = media_segura([base.get((n,), 0.5) for n in j])
    s2 = media_segura([base.get(tuple(sorted(p))) for p in itertools.combinations(j, 2)])
    s3 = media_segura([base.get(tuple(sorted(t))) for t in itertools.combinations(j, 3)])
    return (s1 * 0.25 + s2 * 0.35 + s3 * 0.40)


# ======================================================
# MAIN
# ======================================================

def main():

    supabase = get_supabase()

    log(f"START {VERSAO}")

    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()

    historico = carregar_historico()

    if not historico:
        log("HISTORICO VAZIO")
        return

    ultimo = historico[-1]
    ultimo_jogo = ultimo["numeros"]
    concurso_ref = int(ultimo["concurso"]) + 1

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    memoria = {
        m["hash_estrutura"]: m
        for m in supabase.table("memoria_cenarios").select("*").execute().data
    }

    usados = set(tuple(sorted(h["numeros"])) for h in historico)

    candidatos = []
    pool = list(range(1, 26))

    log("GERANDO CANDIDATOS...")

    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 6000:
            break

        jogo = sorted(random.sample(pool, 15))

        if tuple(jogo) in usados:
            continue

        f = calcular_filtros(jogo, ultimo_jogo)

        if not validar(f):
            continue

        estr = extrair_estrutura(jogo)
        mem = memoria.get(estr["hash_estrutura"])

        score_final = score(jogo, base_scores) * fator_global

        candidatos.append({
            "nums": jogo,
            "score": score_final,
            "filtros": f
        })

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = []

    log("FILTRANDO TOP 7...")

    for c in candidatos:

        if len(finais) >= QTD_FINAL:
            break

        if all(len(set(c["nums"]) ^ set(f["nums"])) >= 10 for f in finais):
            finais.append(c)

    # ==================================================
    # PROTEÇÃO CRÍTICA
    # ==================================================

    if not finais:
        log("ERRO: nenhum resultado gerado")
        return

    log("TOP 7 GERADO COM SUCESSO")

    payload = []
    telegram = []

    print("\n🏆 TOP 7")

    for i, c in enumerate(finais, 1):

        jogo = c["nums"]

        linha = f"{i}º | {c['score']:.4f} | {jogo}"
        print(linha)

        telegram.append(linha)

        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(jogo),
            "pares": c["filtros"]["pares"],
            "impares": 15 - c["filtros"]["pares"],
            "soma_total": c["filtros"]["soma"],
            "processado": False,
            "conferido": False,
            "versao_gerador": VERSAO,
            "metricas": {
                "score": round(c["score"], 6),
                "primos": c["filtros"]["primos"],
                "moldura": c["filtros"]["moldura"]
            }
        })

    # limpeza segura
    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    supabase.table("palpites_validos") \
        .upsert(payload, on_conflict="concurso_referencia,indice_palpite") \
        .execute()

    # ==================================================
    # TELEGRAM FULL PAYLOAD
    # ==================================================

    print("\n📲 TELEGRAM_PAYLOAD_START")
    print("\n".join(telegram))
    print("📲 TELEGRAM_PAYLOAD_END")

    log("PIPELINE FINALIZADO")


if __name__ == "__main__":
    main()
