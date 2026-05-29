import sys
import json
import math
import statistics
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "v1.0-meta-validacao-final"


# ======================================================
# CONFIG
# ======================================================
QTD_PALPITES = 7

LIMITE_OVERLAP_MEDIO = 11.2

LIMITE_EXPOSICAO_DEZENA = 6

LIMITE_ENTROPIA = 2.70

LIMITE_DIVERSIDADE = 16


# ======================================================
# HELPERS
# ======================================================
def calcular_overlap(j1, j2):

    return len(
        set(j1) & set(j2)
    )


def calcular_entropia(contagem):

    total = sum(contagem.values())

    if total == 0:
        return 0

    entropia = 0

    for v in contagem.values():

        p = v / total

        if p > 0:
            entropia -= p * math.log2(p)

    return entropia


def calcular_score_diversidade(jogos):

    dezenas = set()

    for j in jogos:
        dezenas.update(j)

    return len(dezenas)


def calcular_risco_colapso(
    overlap_medio,
    entropia,
    diversidade
):

    risco = 0

    if overlap_medio >= 11:
        risco += 1

    if entropia <= 2.75:
        risco += 1

    if diversidade <= 17:
        risco += 1

    return risco


def interpretar_risco(risco):

    if risco <= 1:
        return "BAIXO"

    if risco == 2:
        return "MODERADO"

    return "ALTO"


# ======================================================
# MAIN
# ======================================================
def main():

    print(
        f"🧠 {VERSAO}"
    )

    supabase = get_supabase()

    # ==================================================
    # ÚLTIMO CONCURSO
    # ==================================================
    ultimo = (

        supabase
        .table("palpites_validos")
        .select(
            "concurso_referencia"
        )
        .order(
            "concurso_referencia",
            desc=True
        )
        .limit(1)
        .execute()
        .data
    )

    if not ultimo:

        print(
            "❌ Nenhum concurso encontrado."
        )

        return

    concurso = ultimo[0][
        "concurso_referencia"
    ]


    # ==================================================
    # CARREGA PALPITES
    # ==================================================
    palpites = (

        supabase
        .table("palpites_validos")
        .select("*")
        .eq(
            "concurso_referencia",
            concurso
        )
        .order(
            "indice_palpite"
        )
        .execute()
        .data
    )

    if len(palpites) < QTD_PALPITES:

        print(
            "⚠️ Quantidade insuficiente de palpites."
        )

        return


    jogos = []

    for p in palpites:

        nums = json.loads(
            p["numeros"]
        )

        jogos.append(nums)


    # ==================================================
    # OVERLAP MÉDIO
    # ==================================================
    overlaps = []

    for i in range(len(jogos)):

        for j in range(i + 1, len(jogos)):

            ov = calcular_overlap(
                jogos[i],
                jogos[j]
            )

            overlaps.append(ov)

    overlap_medio = round(
        statistics.mean(overlaps),
        4
    )


    # ==================================================
    # EXPOSIÇÃO DE DEZENAS
    # ==================================================
    contador = Counter()

    for jogo in jogos:

        for dezena in jogo:
            contador[dezena] += 1


    dezenas_superexpostas = [

        dez

        for dez, qtd in contador.items()

        if qtd >= LIMITE_EXPOSICAO_DEZENA
    ]


    # ==================================================
    # ENTROPIA
    # ==================================================
    entropia = round(

        calcular_entropia(
            contador
        ),

        6
    )


    # ==================================================
    # DIVERSIDADE
    # ==================================================
    diversidade = calcular_score_diversidade(
        jogos
    )


    # ==================================================
    # RISCO DE COLAPSO
    # ==================================================
    risco_colapso = calcular_risco_colapso(

        overlap_medio,

        entropia,

        diversidade
    )

    nivel_risco = interpretar_risco(
        risco_colapso
    )


    # ==================================================
    # STATUS
    # ==================================================
    status = "OK"

    alertas = []


    if overlap_medio >= LIMITE_OVERLAP_MEDIO:

        status = "ALERTA"

        alertas.append(
            "Overlap excessivo"
        )


    if entropia <= LIMITE_ENTROPIA:

        status = "ALERTA"

        alertas.append(
            "Baixa entropia"
        )


    if diversidade <= LIMITE_DIVERSIDADE:

        status = "ALERTA"

        alertas.append(
            "Baixa diversidade"
        )


    if dezenas_superexpostas:

        status = "ALERTA"

        alertas.append(
            f"Dezenas superexpostas: {dezenas_superexpostas}"
        )


    # ==================================================
    # LOG
    # ==================================================
    payload = {

        "concurso_referencia": concurso,

        "overlap_medio": overlap_medio,

        "entropia_global": entropia,

        "diversidade_global": diversidade,

        "risco_colapso": risco_colapso,

        "nivel_risco": nivel_risco,

        "dezenas_superexpostas": dezenas_superexpostas,

        "status_validacao": status,

        "alertas": alertas,

        "versao": VERSAO
    }


    # ==================================================
    # UPSERT
    # ==================================================
    try:

        supabase.table(
            "meta_validacao_execucoes"
        ).upsert(

            payload,

            on_conflict="concurso_referencia"

        ).execute()

    except Exception as e:

        print(
            f"⚠️ Erro ao salvar meta-validação: {e}"
        )


    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n==============================")
    print("🧠 META VALIDAÇÃO FINAL")
    print("==============================\n")

    print(
        f"🎯 Concurso: {concurso}"
    )

    print(
        f"📊 Overlap médio: {overlap_medio}"
    )

    print(
        f"🧬 Entropia global: {entropia}"
    )

    print(
        f"🌎 Diversidade global: {diversidade}"
    )

    print(
        f"⚠️ Risco colapso: {nivel_risco}"
    )

    print(
        f"📌 Status: {status}"
    )

    if dezenas_superexpostas:

        print(
            f"🔥 Superexpostas: {dezenas_superexpostas}"
        )

    if alertas:

        print("\n🚨 ALERTAS:")

        for a in alertas:

            print(
                f"- {a}"
            )

    print("\n==============================\n")


if __name__ == "__main__":
    main()
