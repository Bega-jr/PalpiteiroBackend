import pandas as pd
from collections import Counter
from app.loader import load_lotofacil_data


# ----------------------------
# Helpers
# ----------------------------

def _get_dezenas_df(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna apenas as colunas das dezenas (bola1 a bola15)."""
    return df[[f"bola{i}" for i in range(1, 16)]]


def _flatten_dezenas(df: pd.DataFrame) -> list[int]:
    """Lista plana com todas as dezenas sorteadas."""
    dezenas_df = _get_dezenas_df(df)
    return dezenas_df.values.flatten().tolist()


# ----------------------------
# Estatísticas Globais
# ----------------------------

def estatisticas_globais():
    df = load_lotofacil_data()

    dezenas_flat = _flatten_dezenas(df)

    return {
        "total_concursos": int(df.shape[0]),
        "primeiro_concurso": int(df["concurso"].min()),
        "ultimo_concurso": int(df["concurso"].max()),

        "frequencia_dezenas": _frequencia_dezenas(dezenas_flat),
        "dezenas_mais_sorteadas": _top_dezenas(dezenas_flat, top=10),
        "dezenas_menos_sorteadas": _bottom_dezenas(dezenas_flat, bottom=10),

        "pares_impares": _pares_impares(df),
        "soma_dezenas": _estatistica_soma(df),

        "premios": _estatistica_premios(df),
        "arrecadacao": _estatistica_arrecadacao(df),

        "sequencias": _estatistica_sequencias(df),
    }


# ----------------------------
# Frequência das dezenas
# ----------------------------

def _frequencia_dezenas(dezenas: list[int]) -> dict:
    freq = Counter(dezenas)
    return {str(k).zfill(2): int(v) for k, v in sorted(freq.items())}


def _top_dezenas(dezenas: list[int], top=10) -> list[dict]:
    freq = Counter(dezenas).most_common(top)
    return [
        {"dezena": str(d).zfill(2), "frequencia": int(f)}
        for d, f in freq
    ]


def _bottom_dezenas(dezenas: list[int], bottom=10) -> list[dict]:
    freq = Counter(dezenas)
    menos = sorted(freq.items(), key=lambda x: x[1])[:bottom]
    return [
        {"dezena": str(d).zfill(2), "frequencia": int(f)}
        for d, f in menos
    ]


# ----------------------------
# Pares x Ímpares
# ----------------------------

def _pares_impares(df: pd.DataFrame) -> dict:
    dezenas_df = _get_dezenas_df(df)

    pares = dezenas_df.applymap(lambda x: x % 2 == 0).sum(axis=1)
    impares = 15 - pares

    return {
        "media_pares": round(pares.mean(), 2),
        "media_impares": round(impares.mean(), 2),
        "distribuicao": Counter(pares).most_common(),
    }


# ----------------------------
# Soma das dezenas
# ----------------------------

def _estatistica_soma(df: pd.DataFrame) -> dict:
    dezenas_df = _get_dezenas_df(df)
    soma = dezenas_df.sum(axis=1)

    return {
        "media": round(soma.mean(), 2),
        "min": int(soma.min()),
        "max": int(soma.max()),
    }


# ----------------------------
# Estatísticas de prêmios
# ----------------------------

def _estatistica_premios(df: pd.DataFrame) -> dict:
    return {
        "maior_premio_15": float(df["rateio_15"].max()),
        "media_premio_15": round(float(df["rateio_15"].mean()), 2),

        "media_ganhadores_15": round(float(df["ganhadores_15"].mean()), 2),
        "media_ganhadores_14": round(float(df["ganhadores_14"].mean()), 2),
        "media_ganhadores_13": round(float(df["ganhadores_13"].mean()), 2),
        "media_ganhadores_12": round(float(df["ganhadores_12"].mean()), 2),
        "media_ganhadores_11": round(float(df["ganhadores_11"].mean()), 2),
    }


# ----------------------------
# Arrecadação
# ----------------------------

def _estatistica_arrecadacao(df: pd.DataFrame) -> dict:
    return {
        "total": round(float(df["arrecadacao"].sum()), 2),
        "media": round(float(df["arrecadacao"].mean()), 2),
        "max": round(float(df["arrecadacao"].max()), 2),
    }


# ----------------------------
# Sequências consecutivas
# ----------------------------

def _estatistica_sequencias(df: pd.DataFrame) -> dict:
    dezenas_df = _get_dezenas_df(df)

    def max_sequencia(linha):
        seq = 1
        max_seq = 1
        for i in range(1, len(linha)):
            if linha[i] == linha[i - 1] + 1:
                seq += 1
                max_seq = max(max_seq, seq)
            else:
                seq = 1
        return max_seq

    max_seqs = dezenas_df.apply(
        lambda row: max_sequencia(sorted(row.tolist())),
        axis=1
    )

    return {
        "media_sequencias": round(max_seqs.mean(), 2),
        "mais_comum": Counter(max_seqs).most_common(1)[0][0],
        "distribuicao": Counter(max_seqs),
    }
