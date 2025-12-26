import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data


# =====================================================
# ESTATÍSTICAS BASE (DADOS REAIS)
# =====================================================

def obter_estatisticas_base():
    df = load_lotofacil_data()

    dezenas = [f"bola{i}" for i in range(1, 16)]

    frequencia = (
        df[dezenas]
        .stack()
        .value_counts()
        .sort_index()
    )

    freq_df = pd.DataFrame({
        "numero": frequencia.index.astype(int),
        "frequencia": frequencia.values
    })

    ultimo_concurso = df["concurso"].max()
    atraso = {}

    for n in range(1, 26):
        ult = df[df[dezenas].isin([n]).any(axis=1)]["concurso"].max()
        atraso[n] = int(ultimo_concurso - ult) if pd.notna(ult) else int(ultimo_concurso)

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return (
        freq_df
        .sort_values("frequencia", ascending=False)
        .reset_index(drop=True)
    )


# =====================================================
# SCORE COMBINADO (FREQUÊNCIA + ATRASO)
# ⚠️ NOVO – NÃO QUEBRA NADA
# =====================================================

def obter_estatisticas_com_score(
    peso_frequencia=0.6,
    peso_atraso=0.4
):
    df = obter_estatisticas_base()

    # Normalização segura (0–1)
    df["freq_norm"] = (
        (df["frequencia"] - df["frequencia"].min()) /
        (df["frequencia"].max() - df["frequencia"].min())
    )

    df["atraso_norm"] = (
        (df["atraso"] - df["atraso"].min()) /
        (df["atraso"].max() - df["atraso"].min())
    )

    df["score"] = (
        df["freq_norm"] * peso_frequencia +
        df["atraso_norm"] * peso_atraso
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)


# =====================================================
# MÉTRICAS DE UM JOGO
# =====================================================

def calcular_metricas_jogo(jogo):
    jogo = sorted(set(jogo))

    soma = sum(jogo)
    pares = len([n for n in jogo if n % 2 == 0])

    maior_seq = 1
    seq = 1

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
