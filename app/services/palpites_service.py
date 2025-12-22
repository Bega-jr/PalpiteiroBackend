import random
from functools import lru_cache
from app.services.estatisticas_service import obter_estatisticas_base


def classificar_numeros():
    """
    Classifica os números da Lotofácil em:
    - quentes
    - equilibrados
    - frios
    - atrasados (exclusivos)
    """

    df = obter_estatisticas_base()

    # 🔒 Garantia defensiva
    df = df.copy()
    df["numero"] = df["numero"].astype(int)

    # 🔥 QUENTES → alta frequência + baixo atraso
    quentes = (
        df.sort_values(["frequencia", "atraso"], ascending=[False, True])
        .head(8)["numero"]
        .tolist()
    )

    # ❄️ FRIOS → baixa frequência
    frios = (
        df.sort_values("frequencia", ascending=True)
        .head(8)["numero"]
        .tolist()
    )

    # ⚖️ EQUILIBRADOS → meio estatístico
    usados = set(quentes + frios)

    equilibrados = (
        df[~df["numero"].isin(usados)]
        .sort_values("frequencia", ascending=False)
        .head(9)["numero"]
        .tolist()
    )

    # 💤 ATRASADOS → maior atraso, sem repetir
    usados = set(quentes + frios + equilibrados)

    atrasados = (
        df[~df["numero"].isin(usados)]
        .sort_values("atraso", ascending=False)
        .head(8)["numero"]
        .tolist()
    )

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }
