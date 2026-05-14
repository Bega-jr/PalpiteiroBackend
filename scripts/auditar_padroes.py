import math
from collections import defaultdict

from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais
)


def calcular_score_adaptativo(dados):
    hits_15 = dados.get("hits_15", 0)
    hits_14 = dados.get("hits_14", 0)
    hits_13 = dados.get("hits_13", 0)

    ocorrencias = dados.get("ocorrencias", 1)

    janelas_ativas = dados.get(
        "janelas_ativas",
        []
    )

    total_janelas = len(janelas_ativas)

    score_hits = (
        math.log1p(hits_15) * 1.00 +
        math.log1p(hits_14) * 0.35 +
        math.log1p(hits_13) * 0.10
    )

    score_consistencia = (
        math.log1p(total_janelas) * 0.30
    )

    score_volume = (
        math.log1p(ocorrencias) * 0.20
    )

    return round(
        score_hits +
        score_consistencia +
        score_volume,
        6
    )


def converter_para_metadata(score_base, dados_brutos):
    """
    Compatibilidade total:
    - dict → usa normalmente
    - float/int → converte
    - None → cria fallback
    """

    if isinstance(dados_brutos, dict):
        return {
            "hits_15": dados_brutos.get(
                "hits_15",
                0
            ),
            "hits_14": dados_brutos.get(
                "hits_14",
                0
            ),
            "hits_13": dados_brutos.get(
                "hits_13",
                0
            ),
            "ocorrencias": dados_brutos.get(
                "ocorrencias",
                1
            ),
            "janelas_ativas": dados_brutos.get(
                "janelas_ativas",
                [1]
            )
        }

    score_base = float(score_base)

    return {
        "hits_15": int(score_base * 4),
        "hits_14": int(score_base * 6),
        "hits_13": int(score_base * 8),
        "ocorrencias": max(
            1,
            int(score_base * 20)
        ),
        "janelas_ativas": [1]
    }


def enriquecer_metadata(scores, metadata):
    metadata_corrigida = defaultdict(dict)

    for chave in scores:

        score_base = scores[chave]

        dados_brutos = metadata.get(
            chave,
            None
        )

        metadata_corrigida[chave] = (
            converter_para_metadata(
                score_base,
                dados_brutos
            )
        )

    return metadata_corrigida


def identificar_padroes_elite():

    print(
        "📊 Aprendizado: últimos 1000 concursos"
    )

    scores, metadata = (
        calcular_score_combinacoes_reais(
            1000
        )
    )

    metadata = enriquecer_metadata(
        scores,
        metadata
    )

    print(
        f"✅ Aprendizado concluído: "
        f"{len(scores)} padrões"
    )

    ranking = []

    for chave in scores:

        dados = metadata[chave]

        score_final = (
            calcular_score_adaptativo(
                dados
            )
        )

        if score_final >= 0.30:

            ranking.append(
                (
                    chave,
                    score_final,
                    dados
                )
            )

    ranking.sort(
        key=lambda x: x[1],
        reverse=True
    )

    print(
        f"📊 Total de padrões carregados: "
        f"{len(scores)}"
    )

    print(
        f"\n💎 FORAM IDENTIFICADOS "
        f"{len(ranking)} PADRÕES DE ELITE:\n"
    )

    for i, (
        chave,
        score,
        dados
    ) in enumerate(
        ranking,
        1
    ):

        print(
            f"{i}º | "
            f"Score: {score:.6f} | "
            f"Chave: {chave}"
        )

        print(
            f"    15pts={dados['hits_15']} | "
            f"14pts={dados['hits_14']} | "
            f"13pts={dados['hits_13']} | "
            f"Freq={dados['ocorrencias']}"
        )


if __name__ == "__main__":
    identificar_padroes_elite()
