import pandas as pd
import os
from typing import Dict, Any, List
from app.services.historico_service import _carregar_historico

# --- CONSTANTES ---
PRIMOS = [2, 3, 5, 7, 11, 13, 17, 19, 23]

# ---------------------------------------------------------------------
# HISTÓRICO
# ---------------------------------------------------------------------

def carregar_dados_para_estatistica():
    caminho_csv = os.path.join(os.getcwd(), "data", "Lotofacil.csv")
    if os.path.exists(caminho_csv):
        df = pd.read_csv(caminho_csv)
        colunas = [f"bola{i}" for i in range(1, 16)]
        df["numeros"] = df[colunas].values.tolist()
        return df[["concurso", "data", "numeros"]].to_dict("records")
    return _carregar_historico()

# ---------------------------------------------------------------------
# ÚLTIMO RESULTADO  ✅ (FUNÇÃO QUE ESTAVA FALTANDO)
# ---------------------------------------------------------------------

def obter_ultimo_resultado() -> Dict[str, Any] | None:
    """
    Retorna o último concurso do histórico.
    Usado pelo serviço de palpites.
    """
    historico = carregar_dados_para_estatistica()

    if not historico:
        return None

    return historico[-1]

# ---------------------------------------------------------------------
# MÉTRICAS DE UM JOGO
# ---------------------------------------------------------------------

def calcular_metricas_jogo(jogo: List[int]) -> Dict[str, int]:
    jogo = sorted(set(jogo))

    pares = sum(1 for n in jogo if n % 2 == 0)
    primos = sum(1 for n in jogo if n in PRIMOS)

    maior_seq = seq = 1
    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            seq += 1
            maior_seq = max(maior_seq, seq)
        else:
            seq = 1

    return {
        "soma": sum(jogo),
        "pares": pares,
        "impares": 15 - pares,
        "primos": primos,
        "maior_sequencia": maior_seq
    }

# ---------------------------------------------------------------------
# ESTATÍSTICAS BASE (frequência + atraso)
# ---------------------------------------------------------------------

def obter_estatisticas_base():
    historico = carregar_dados_para_estatistica()
    df = pd.DataFrame(historico).explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    freq = df["numeros"].value_counts().sort_index()
    freq_df = pd.DataFrame({
        "numero": freq.index,
        "frequencia": freq.values
    })

    ultimo = df["concurso"].max()
    atraso = {
        n: int(ultimo - df[df["numeros"] == n]["concurso"].max())
        for n in range(1, 26)
    }

    freq_df["atraso"] = freq_df["numero"].map(atraso)
    return freq_df.reset_index(drop=True)

# ---------------------------------------------------------------------
# SCORE
# ---------------------------------------------------------------------

def obter_estatisticas_com_score(peso_freq=0.6, peso_atraso=0.4):
    df = obter_estatisticas_base()

    df["freq_norm"] = (df["frequencia"] - df["frequencia"].min()) / (
        df["frequencia"].max() - df["frequencia"].min()
    )

    df["atraso_norm"] = (df["atraso"] - df["atraso"].min()) / (
        df["atraso"].max() - df["atraso"].min()
    )

    df["score"] = (
        df["freq_norm"] * peso_freq +
        df["atraso_norm"] * peso_atraso
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)

# ---------------------------------------------------------------------
# MÉDIAS REAIS (ÚLTIMOS N CONCURSOS)
# ---------------------------------------------------------------------

def calcular_medias_recentes(qtd: int = 10):
    historico = carregar_dados_para_estatistica()
    if len(historico) < qtd:
        raise RuntimeError("Histórico insuficiente")

    recentes = historico[-qtd:]

    soma = pares = impares = primos = 0

    for s in recentes:
        m = calcular_metricas_jogo(s["numeros"])
        soma += m["soma"]
        pares += m["pares"]
        impares += m["impares"]
        primos += m["primos"]

    return {
        "soma_media": soma / qtd,
        "pares_media": pares / qtd,
        "impares_media": impares / qtd,
        "primos_media": primos / qtd,
        "data_referencia": recentes[-1]["data"]
    }

# ---------------------------------------------------------------------
# CICLO
# ---------------------------------------------------------------------

def analisar_ciclo():
    historico = carregar_dados_para_estatistica()
    vistos = set()

    for s in reversed(historico):
        vistos.update(s["numeros"])
        if len(vistos) == 25:
            break

    return list(set(range(1, 26)) - vistos)
