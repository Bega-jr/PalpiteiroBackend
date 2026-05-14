from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais
)


def identificar_padroes_elite():

    # sua função retorna tuple
    scores, metadata = calcular_score_combinacoes_reais(1000)

    print(
        f"📊 Total de padrões carregados: {len(scores)}"
    )

    # filtra apenas padrões fortes
    padroes_elite = {

        k: v

        for k, v in scores.items()

        if v >= 0.05
    }

    ranking = sorted(

        padroes_elite.items(),

        key=lambda x: x[1],

        reverse=True
    )

    print(
        f"\n💎 FORAM IDENTIFICADOS "
        f"{len(ranking)} PADRÕES DE ELITE:\n"
    )

    for i, (chave, score) in enumerate(
        ranking,
        1
    ):

        print(
            f"{i}º | "
            f"Score: {score:.6f} | "
            f"Chave: {chave}"
        )


if __name__ == "__main__":
    identificar_padroes_elite()
