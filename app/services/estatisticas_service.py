import pandas as pd
from typing import Dict, Any, List
from app.services.supabase_service import get_supabase

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}


# -------------------------------------------------
# HISTÓRICO DIRETO DO SUPABASE
# -------------------------------------------------
def carregar_historico():
    supabase = get_supabase()

    res = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,data,dezenas")
        .order("concurso")
        .execute()
    )

    if not res.data:
        return []

    return [
        {
            "concurso": r["concurso"],
            "data": r["data"],
            "numeros": [int(n) for n in r["dezenas"]],
        }
        for r in res.data
    ]


# -------------------------------------------------
# MÉTRICAS DE UM JOGO
# -------------------------------------------------
def calcular_metricas_jogo(jogo: List[int]) -> Dict[str, int]:
    pares = sum(1 for n in jogo if n % 2 == 0)
    primos = sum(1 for n in jogo if n in PRIMOS)

    seq = maior_seq = 1
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
        "maior_sequencia": maior_seq,
    }


# -------------------------------------------------
# ESTATÍSTICAS BASE (frequência + atraso)
# -------------------------------------------------
def obter_estatisticas_base() -> pd.DataFrame:
    historico = carregar_historico()

    df = pd.DataFrame(historico).explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    freq = df["numeros"].value_counts().sort_index()

    ultimo_concurso = df["concurso"].max()

    atraso = {
        n: int(ultimo_concurso - df[df["numeros"] == n]["concurso"].max())
        for n in range(1, 26)
    }

    return pd.DataFrame({
        "numero": range(1, 26),
        "frequencia": [freq.get(n, 0) for n in range(1, 26)],
        "atraso": [atraso[n] for n in range(1, 26)],
    })


# -------------------------------------------------
# SCORE
# -------------------------------------------------
def obter_estatisticas_com_score(peso_freq=0.6, peso_atraso=0.4) -> pd.DataFrame:
    df = obter_estatisticas_base()

    df["freq_norm"] = (
        df["frequencia"] - df["frequencia"].min()
    ) / (df["frequencia"].max() - df["frequencia"].min())

    df["atraso_norm"] = (
        df["atraso"] - df["atraso"].min()
    ) / (df["atraso"].max() - df["atraso"].min())

    df["score"] = (
        df["freq_norm"] * peso_freq +
        df["atraso_norm"] * peso_atraso
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)


# -------------------------------------------------
# MÉDIAS REAIS
# -------------------------------------------------
def calcular_medias_recentes(qtd: int = 10) -> Dict[str, Any]:
    historico = carregar_historico()

    if len(historico) < qtd:
        raise RuntimeError("Histórico insuficiente")

    recentes = historico[-qtd:]

    soma = pares = impares = primos = 0

    for r in recentes:
        m = calcular_metricas_jogo(r["numeros"])
        soma += m["soma"]
        pares += m["pares"]
        impares += m["impares"]
        primos += m["primos"]

    return {
        "soma_media": soma / qtd,
        "pares_media": pares / qtd,
        "impares_media": impares / qtd,
        "primos_media": primos / qtd,
    }


# -------------------------------------------------
# 🔥 FUNÇÃO QUE ESTAVA FALTANDO
# -------------------------------------------------
def obter_numeros_mais_atrasados(qtd: int = 5) -> List[int]:
    df = obter_estatisticas_base()
    return (
        df.sort_values("atraso", ascending=False)
        .head(qtd)["numero"]
        .astype(int)
        .tolist()
    )
