from typing import Dict, Any, List
import pandas as pd
from app.services.supabase_service import get_supabase

# ---------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
TABELA_CONCURSOS = "lotofacil_concursos"

# ---------------------------------------------------------------------
# HISTÓRICO (SUPABASE)
# ---------------------------------------------------------------------

def carregar_dados_para_estatistica() -> List[Dict[str, Any]]:
    """
    Carrega TODO o histórico diretamente do Supabase.
    Fonte única de verdade.
    """
    supabase = get_supabase()

    resp = (
        supabase
        .table(TABELA_CONCURSOS)
        .select("concurso, data, dezenas")
        .order("concurso")
        .execute()
    )

    if not resp.data:
        return []

    return [
        {
            "concurso": int(r["concurso"]),
            "data": r["data"],
            "numeros": [int(n) for n in r["dezenas"]],
        }
        for r in resp.data
    ]

# ---------------------------------------------------------------------
# ÚLTIMO RESULTADO
# ---------------------------------------------------------------------

def obter_ultimo_resultado() -> Dict[str, Any] | None:
    historico = carregar_dados_para_estatistica()
    return historico[-1] if historico else None

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
        "impares": len(jogo) - pares,
        "primos": primos,
        "maior_sequencia": maior_seq,
    }

# ---------------------------------------------------------------------
# ESTATÍSTICAS BASE (FREQUÊNCIA + ATRASO REAL)
# ---------------------------------------------------------------------

def obter_estatisticas_base() -> pd.DataFrame:
    historico = carregar_dados_para_estatistica()
    if not historico:
        return pd.DataFrame()

    df = pd.DataFrame(historico).explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    # Frequência absoluta
    freq = df["numeros"].value_counts().sort_index()

    ultimo_concurso = df["concurso"].max()

    # Última aparição real de cada número
    ultima_aparicao = (
        df.groupby("numeros")["concurso"]
        .max()
        .to_dict()
    )

    dados = []
    for n in range(1, 26):
        dados.append({
            "numero": n,
            "frequencia": int(freq.get(n, 0)),
            "atraso": int(ultimo_concurso - ultima_aparicao.get(n, ultimo_concurso)),
        })

    return pd.DataFrame(dados)

# ---------------------------------------------------------------------
# SCORE (NORMALIZADO)
# ---------------------------------------------------------------------

def obter_estatisticas_com_score(peso_freq: float = 0.6, peso_atraso: float = 0.4) -> pd.DataFrame:
    df = obter_estatisticas_base()
    if df.empty:
        return df

    # Normalizações seguras
    df["freq_norm"] = (
        (df["frequencia"] - df["frequencia"].min()) /
        max(1, df["frequencia"].max() - df["frequencia"].min())
    )

    df["atraso_norm"] = (
        (df["atraso"] - df["atraso"].min()) /
        max(1, df["atraso"].max() - df["atraso"].min())
    )

    df["score"] = (
        df["freq_norm"] * peso_freq +
        df["atraso_norm"] * peso_atraso
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)

# ---------------------------------------------------------------------
# MÉDIAS REAIS (ÚLTIMOS N CONCURSOS)
# ---------------------------------------------------------------------

def calcular_medias_recentes(qtd: int = 10) -> Dict[str, float]:
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
        "soma_media": round(soma / qtd, 2),
        "pares_media": round(pares / qtd, 2),
        "impares_media": round(impares / qtd, 2),
        "primos_media": round(primos / qtd, 2),
        "data_referencia": recentes[-1]["data"],  # data REAL do concurso
    }

# ---------------------------------------------------------------------
# CICLO (BASEADO NO HISTÓRICO TOTAL)
# ---------------------------------------------------------------------

def analisar_ciclo() -> List[int]:
    """
    Retorna os números que ainda NÃO apareceram
    desde o início do ciclo atual (histórico completo).
    """
    historico = carregar_dados_para_estatistica()
    vistos = set()

    for s in reversed(historico):
        vistos.update(s["numeros"])
        if len(vistos) == 25:
            break

    return sorted(set(range(1, 26)) - vistos)


    return list(set(range(1, 26)) - vistos)
