import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data


def obter_estatisticas_base():
    """
    Carrega a base real da Lotofácil (CSV/XLSX da Caixa)
    e calcula frequência e atraso de cada número.
    """

    df = load_lotofacil_data()

    if df is None or df.empty:
        raise RuntimeError("Base da Lotofácil vazia ou não carregada")

    dezenas = [f"bola{i}" for i in range(1, 16)]

    # Frequência absoluta
    frequencia = (
        df[dezenas]
        .stack()
        .value_counts()
        .sort_index()
    )

    if frequencia.empty:
        raise RuntimeError("Falha ao calcular frequência das dezenas")

    freq_df = pd.DataFrame({
        "numero": frequencia.index.astype(int),
        "frequencia": frequencia.values
    }).sort_values("frequencia", ascending=False)

    # Cálculo de atraso
    ultimo_concurso = df["concurso"].max()
    atraso = {}

    for n in range(1, 26):
        ult = df[df[dezenas].isin([n]).any(axis=1)]["concurso"].max()
        atraso[n] = (
            ultimo_concurso - ult
            if pd.notna(ult)
            else ultimo_concurso
        )

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return freq_df.reset_index(drop=True)


def calcular_metricas_jogo(jogo):
    """
    Calcula métricas estatísticas de um jogo específico
    """

    if not jogo or len(jogo) != 15:
        raise ValueError("Jogo inválido para cálculo de métricas")

    jogo_ordenado = sorted(jogo)

    soma = sum(jogo_ordenado)
    pares = sum(1 for n in jogo_ordenado if n % 2 == 0)
    impares = 15 - pares

    # Maior sequência consecutiva
    maior_seq = 1
    atual = 1

    for i in range(1, len(jogo_ordenado)):
        if jogo_ordenado[i] == jogo_ordenado[i - 1] + 1:
            atual += 1
            maior_seq = max(maior_seq, atual)
        else:
            atual = 1

    return {
        "soma": soma,
        "pares": pares,
        "impares": impares,
        "maior_sequencia": maior_seq
    }

