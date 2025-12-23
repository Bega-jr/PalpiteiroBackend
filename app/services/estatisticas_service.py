import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


def obter_estatisticas_base():
    """
    Retorna estatísticas base da Lotofácil:
    - frequência absoluta
    - atraso por número
    """

    df = load_lotofacil_data()

    dezenas = [f"bola{i}" for i in range(1, 16)]

    # ===============================
    # FREQUÊNCIA
    # ===============================
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

    # ===============================
    # ATRASO
    # ===============================
    ultimo_concurso = df["concurso"].max()
    atraso = {}

    for n in range(1, TOTAL_NUMEROS + 1):
        ult = df[df[dezenas].isin([n]).any(axis=1)]["concurso"].max()
        atraso[n] = int(ultimo_concurso - ult) if pd.notna(ult) else int(ultimo_concurso)

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    # ===============================
    # ORDENAÇÃO FINAL
    # ===============================
    freq_df = freq_df.sort_values("frequencia", ascending=False).reset_index(drop=True)

    return freq_df


# =====================================================
# MÉTRICAS PARA VALIDAÇÃO DOS JOGOS
# =====================================================

def calcular_metricas_jogo(jogo):
    """
    Calcula métricas estatísticas de um jogo
    """
    jogo = sorted(jogo)

    pares = sum(1 for n in jogo if n % 2 == 0)
    impares = NUMEROS_POR_JOGO - pares
    soma = sum(jogo)

    # Sequências consecutivas
    seq_atual = 1
    maior_seq = 1

    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            seq_atual += 1
            maior_seq = max(maior_seq, seq_atual)
        else:
            seq_atual = 1

    return {
        "pares": pares,
        "impares": impares,
        "soma": soma,
        "maior_sequencia": maior_seq
    }


def validar_jogo_estatisticamente(jogo):
    """
    Validação estatística automática do jogo
    """

    metricas = calcular_metricas_jogo(jogo)

    regras = {
        "soma_ok": 170 <= metricas["soma"] <= 210,
        "pares_ok": 6 <= metricas["pares"] <= 9,
        "sequencia_ok": metricas["maior_sequencia"] <= 5
    }

    aprovado = all(regras.values())

    return {
        "aprovado": aprovado,
        "metricas": metricas,
        "regras": regras
    }
