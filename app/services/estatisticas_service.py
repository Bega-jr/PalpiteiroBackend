import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data


# =====================================================
# ESTATÍSTICAS BASE (FREQUÊNCIA + ATRASO)
# =====================================================

def obter_estatisticas_base():
    """
    Retorna DataFrame com:
    - numero
    - frequencia
    - atraso
    """

    df = load_lotofacil_data()

    dezenas = [f"bola{i}" for i in range(1, 16)]

    # -----------------------------
    # FREQUÊNCIA
    # -----------------------------
    frequencia = (
        df[dezenas]
        .astype(int)
        .stack()
        .value_counts()
        .sort_index()
    )

    freq_df = pd.DataFrame({
        "numero": frequencia.index.astype(int),
        "frequencia": frequencia.values
    })

    # -----------------------------
    # ATRASO
    # -----------------------------
    ultimo_concurso = df["concurso"].max()
    atraso = {}

    for n in range(1, 26):
        ult = (
            df[df[dezenas].isin([n]).any(axis=1)]
            ["concurso"]
            .max()
        )
        atraso[n] = int(ultimo_concurso - ult) if pd.notna(ult) else int(ultimo_concurso)

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return freq_df.reset_index(drop=True)


# =====================================================
# SCORE COMBINADO (FREQ + ATRASO NORMALIZADOS)
# =====================================================

def obter_estatisticas_com_score(
    peso_frequencia: float = 0.6,
    peso_atraso: float = 0.4
):
    """
    Retorna DataFrame ordenado por score decrescente
    """

    df = obter_estatisticas_base().copy()

    # Normalização segura
    fmin, fmax = df["frequencia"].min(), df["frequencia"].max()
    amin, amax = df["atraso"].min(), df["atraso"].max()

    df["freq_norm"] = (
        (df["frequencia"] - fmin) / (fmax - fmin)
        if fmax != fmin else 0
    )

    df["atraso_norm"] = (
        (df["atraso"] - amin) / (amax - amin)
        if amax != amin else 0
    )

    df["score"] = (
        df["freq_norm"] * peso_frequencia +
        df["atraso_norm"] * peso_atraso
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)


# =====================================================
# MÉTRICAS DE UM JOGO (USADO NO VALIDATOR)
# =====================================================

def calcular_metricas_jogo(jogo):
    jogo = sorted(set(jogo))

    soma = sum(jogo)
    pares = sum(1 for n in jogo if n % 2 == 0)

    maior_seq = seq = 1
    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            seq += 1
            maior_seq = max(maior_seq, seq)
        else:
            seq = 1

    return {
        "soma": soma,
        "pares": pares,
        "impares": len(jogo) - pares,
        "maior_sequencia": maior_seq
    }

