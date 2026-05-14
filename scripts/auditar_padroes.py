from collections import defaultdict
import math

from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais
)


def calcular_score_adaptativo(metadata_padrao):
    """
    Novo score inteligente:

    Critérios:
    - 15 pontos tem peso máximo
    - 14 e 13 entram como suporte estatístico
    - Consistência histórica aumenta score
    - Frequência total aumenta confiabilidade

    Compatível com metadata do motor.
    """

    hits_15 = metadata_padrao.get("hits_15", 0)
    hits_14 = metadata_padrao.get("hits_14", 0)
    hits_13 = metadata_padrao.get("hits_13", 0)

    ocorrencias = metadata_padrao.get("ocorrencias", 0)

    janelas_ativas = metadata_padrao.get(
        "janelas_ativas",
        []
    )

    total_janelas = len(janelas_ativas)

    # score de performance
    score_hits = (
        math.log1p(hits_15) * 1.00 +
        math.log1p(hits_14) * 0.35 +
        math.log1p(hits_13) * 0.10
    )

    # score de consistência
    score_consistencia = (
        math.log1p(total_janelas) * 0.30
    )

    # score de volume histórico
    score_volume = (
        math.log1p(ocorrencias) * 0.20
    )

    score_total = (
        score_hits +
        score_consistencia +
        score_volume
    )

    return round(score_total, 6)


def enriquecer_metadata(scores, metadata):
    """
    Mantém compatibilidade com versões antigas.
    Caso metadata venha incompleta,
    preenche automaticamente.
    """

    metadata_corrigida = defaultdict(dict)

    for chave in scores:

        base_score = scores.get(chave, 0)

        dados = metadata.get(chave, {})

        metadata_corrigida[chave] = {
            "hits_15": dados.get(
                "hits_15",
                int(base_score * 4)
            ),
            "hits_14": dados.get(
                "hits_14",
                int(base_score * 6)
            ),
            "hits_13": dados.get(
                "hits_13",
                int(base_score * 8)
            ),
            "ocorrencias": dados.get(
                "ocorrencias",
                max(
                    1,
                    int(base_score * 20)
                )
            ),
            "janelas_ativas": dados.get(
                "janelas_ativas",
                [1]
            )
        }

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

    print(
        f"📊 Total de padrões carregados: "
        f"{len(scores)}"
    )

    ranking_adaptativo = []

    for chave in scores:

        dados = metadata[chave]

        novo_score = (
            calcular_score_adaptativo(
                dados
            )
        )

        if novo_score >= 0.30:

            ranking_adaptativo.append(
                (
                    chave,
                    novo_score,
                    dados
                )
            )

    ranking_adaptativo.sort(
        key=lambda x: x[1],
        reverse=True
    )

    print(
        f"\n💎 FORAM IDENTIFICADOS "
        f"{len(ranking_adaptativo)} "
        f"PADRÕES DE ELITE:\n"
    )

    for i, (
        chave,
        score,
        dados
    ) in enumerate(
        ranking_adaptativo,
        1
    ):

        print(
            f"{i}º | "
            f"Score: {score:.6f} | "
            f"Chave: {chave}"
        )

        print(
            f"    15pts: {dados['hits_15']} | "
            f"14pts: {dados['hits_14']} | "
            f"13pts: {dados['hits_13']} | "
            f"Ocorrências: {dados['ocorrencias']} | "
            f"Janelas: {len(dados['janelas_ativas'])}"
        )


if __name__ == "__main__":
    identificar_padroes_elite()
