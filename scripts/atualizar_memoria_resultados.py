import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


PRIMOS = {
    2, 3, 5, 7, 11,
    13, 17, 19, 23
}


# ======================================================
# BONUS DE CONTEXTO
# ======================================================
PESO_REGIME = {

    "EXPANSAO_QUENTES": 1.00,

    "NEUTRO": 1.03,

    "CONTRACAO_FRIAS": 1.06
}


# ======================================================
# AUX
# ======================================================
def parse_numeros(valor):

    if isinstance(
        valor,
        list
    ):

        return [
            int(x)
            for x in valor
        ]

    if isinstance(
        valor,
        str
    ):

        try:

            return [

                int(x)

                for x in json.loads(
                    valor
                )
            ]

        except:

            return []

    return []


def extrair_estrutura(nums):

    linhas = [

        sum(
            1 for n in nums
            if 1 <= n <= 5
        ),

        sum(
            1 for n in nums
            if 6 <= n <= 10
        ),

        sum(
            1 for n in nums
            if 11 <= n <= 15
        ),

        sum(
            1 for n in nums
            if 16 <= n <= 20
        ),

        sum(
            1 for n in nums
            if 21 <= n <= 25
        )
    ]

    return {

        "pares":

            sum(
                1 for n in nums
                if n % 2 == 0
            ),

        "primos":

            sum(
                1 for n in nums
                if n in PRIMOS
            ),

        "hash_estrutura":

            "-".join(
                map(
                    str,
                    linhas
                )
            )
    }


def calcular_acertos(
    palpite,
    resultado
):

    return len(
        set(palpite)
        &
        set(resultado)
    )


# ======================================================
# PESO BASE
# ======================================================
def peso_acerto(acertos):

    pesos = {

        11: 0.10,
        12: 0.25,
        13: 0.50,
        14: 0.80,
        15: 1.00
    }

    return pesos.get(
        acertos,
        0.02
    )


# ======================================================
# SCORE V15
# ======================================================
def score_v15(row):

    return (

        row.get(
            "score_medio_real",
            0
        ) * 0.50

        +

        row.get(
            "taxa_7d",
            0
        ) * 0.30

        +

        row.get(
            "taxa_30d",
            0
        ) * 0.20
    )


# ======================================================
# TELEMETRIA
# ======================================================
def obter_contexto_geracao(
    supabase,
    concurso_ref
):

    try:

        rows = (

            supabase
            .table(
                "telemetria_geracao"
            )
            .select(
                "regime,versao_gerador"
            )
            .eq(
                "concurso_referencia",
                concurso_ref
            )
            .limit(1)
            .execute()
            .data
        )

        if not rows:

            return {
                "regime": None,
                "versao": None
            }

        return {

            "regime":
                rows[0].get(
                    "regime"
                ),

            "versao":
                rows[0].get(
                    "versao_gerador"
                )
        }

    except:

        return {
            "regime": None,
            "versao": None
        }


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        "🧠 Atualizando memória v16"
    )

    concurso = (

        supabase
        .table(
            "lotofacil_concursos"
        )
        .select(
            "concurso,dezenas"
        )
        .order(
            "concurso",
            desc=True
        )
        .limit(1)
        .execute()
        .data[0]
    )

    concurso_ref = int(
        concurso[
            "concurso"
        ]
    )

    resultado = parse_numeros(
        concurso[
            "dezenas"
        ]
    )

    contexto = obter_contexto_geracao(
        supabase,
        concurso_ref
    )

    regime = contexto[
        "regime"
    ]

    fator_regime = PESO_REGIME.get(
        regime,
        1.0
    )

    palpites = (

        supabase
        .table(
            "palpites_validos"
        )
        .select("*")
        .eq(
            "concurso_referencia",
            concurso_ref
        )
        .execute()
        .data
    )

    if not palpites:

        print(
            "⚠️ Nenhum palpite encontrado"
        )

        return

    for p in palpites:

        numeros = parse_numeros(
            p[
                "numeros"
            ]
        )

        if not numeros:
            continue

        estrutura = extrair_estrutura(
            numeros
        )

        acertos = calcular_acertos(
            numeros,
            resultado
        )

        peso = peso_acerto(
            acertos
        )

        # bônus contextual
        peso *= fator_regime

        busca = (

            supabase
            .table(
                "memoria_cenarios"
            )
            .select("*")
            .eq(
                "hash_estrutura",
                estrutura[
                    "hash_estrutura"
                ]
            )
            .execute()
        )

        if not busca.data:
            continue

        row = busca.data[0]

        vezes = int(

            row.get(
                "vezes_gerado",
                0
            )
        )

        score_antigo = float(

            row.get(
                "score_medio_real",
                0
            )
        )

        novo_vezes = (
            vezes + 1
        )

        # ===================================
        # MÉDIA INCREMENTAL
        # ===================================
        score_novo = (

            (
                score_antigo
                *
                vezes
            )

            +

            peso

        ) / novo_vezes

        # proteção contra explosão
        score_novo = min(
            1.20,
            score_novo
        )

        taxa_7d = row.get(
            "taxa_7d",
            0
        )

        taxa_30d = row.get(
            "taxa_30d",
            0
        )

        score_final = (

            score_novo * 0.70

            +

            taxa_7d * 0.20

            +

            taxa_30d * 0.10
        )

        update = {

            "vezes_gerado":
                novo_vezes,

            "score_medio_real":
                round(
                    score_novo,
                    4
                ),

            "score_v15":
                round(
                    score_final,
                    4
                ),

            "ultima_aparicao":
                datetime.now()
                .date()
                .isoformat(),

            "updated_at":
                datetime.now()
                .isoformat()
        }

        # distribuição real
        if acertos >= 11:

            col = (
                f"acertos_{acertos}"
            )

            update[col] = (

                row.get(
                    col,
                    0
                )

                +

                1
            )

        (
            supabase
            .table(
                "memoria_cenarios"
            )
            .update(
                update
            )
            .eq(
                "id",
                row["id"]
            )
            .execute()
        )

    print(
        f"✅ Memória atualizada | Regime={regime}"
    )


if __name__ == "__main__":
    main()
