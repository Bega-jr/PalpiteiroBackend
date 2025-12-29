import pandas as pd
from app.services.historico_service import _carregar_historico


# =====================================================
# ESTATÍSTICAS BASE (FREQUÊNCIA + ATRASO)
# =====================================================

def obter_estatisticas_base():
    historico = _carregar_historico()
    if not historico:
        raise RuntimeError("Histórico vazio")

    df = pd.DataFrame(historico)

    df = df.explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    # -----------------------------
    # FREQUÊNCIA
    # -----------------------------
    freq = df["numeros"].value_counts().sort_index()

    freq_df = pd.DataFrame({
        "numero": freq.index,
        "frequencia": freq.values
    })

    # -----------------------------
    # ATRASO (baseado em ordem temporal)
    # -----------------------------
    df["concurso"] = pd.to_datetime(df["data"]).rank(method="dense").astype(int)
    ultimo_concurso = df["concurso"].max()

    atraso = {}
    for n in range(1, 26):
        ult = df[df["numeros"] == n]["concurso"].max()
        atraso[n] = int(ultimo_concurso - ult) if pd.notna(ult) else int(ultimo_concurso)

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return freq_df.reset_index(drop=True)


# =====================================================
# SCORE COMBINADO (NORMALIZADO)
# =====================================================

def obter_estatisticas_com_score(peso_frequencia=0.6, peso_atraso=0.4):
    df = obter_estatisticas_base().copy()

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
# SCORE ADAPTATIVO (APRENDIZADO REAL)
# =====================================================

def obter_estatisticas_adaptativas():
    historico = _carregar_historico()
    if not historico:
        return obter_estatisticas_com_score()

    df_hist = pd.DataFrame(historico)
    df_hist = df_hist.explode("numeros")
    df_hist["numeros"] = df_hist["numeros"].astype(int)

    df_hist["peso"] = (
        df_hist.get("acertos", 0).fillna(0) * 0.6 +
        df_hist.get("score_final", 0).fillna(0) * 0.4
    )

    aprendizado = (
        df_hist.groupby("numeros")["peso"]
        .mean()
        .reset_index()
        .rename(columns={"numeros": "numero"})
    )

    base = obter_estatisticas_com_score()

    base = base.merge(aprendizado, on="numero", how="left")
    base["peso"] = base["peso"].fillna(0)

    base["score_adaptativo"] = (
        base["score"] * 0.7 +
        base["peso"] * 0.3
    )

    return base.sort_values("score_adaptativo", ascending=False).reset_index(drop=True)


# =====================================================
# MÉTRICAS DE UM JOGO
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

