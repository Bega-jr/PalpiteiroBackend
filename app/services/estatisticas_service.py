import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data

# =====================================================
# BASE ESTATÍSTICA (FREQUÊNCIA + ATRASO)
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
    }).sort_values("frequencia", ascending=False)

    # atraso
    ultimo_concurso = df["concurso"].max()
    atraso = {}

    for n in range(1, 26):
        ult = df[df[dezenas].isin([n]).any(axis=1)]["concurso"].max()
        atraso[n] = ultimo_concurso - ult if pd.notna(ult) else ultimo_concurso

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return freq_df.reset_index(drop=True)

# =====================================================
# MÉTRICAS DE UM JOGO (USADO PELO VALIDATOR)
# =====================================================

def calcular_metricas_jogo(jogo):
    """
    Calcula métricas estatísticas básicas de um jogo da Lotofácil
    """

    jogo = sorted(jogo)

    soma = sum(jogo)
    pares = sum(1 for n in jogo if n % 2 == 0)

    # sequência consecutiva
    maior_sequencia = 1
    atual = 1

    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            atual += 1
            maior_sequencia = max(maior_sequencia, atual)
        else:
            atual = 1

    return {
        "soma": soma,
        "pares": pares,
        "impares": len(jogo) - pares,
        "maior_sequencia": maior_sequencia
    }

