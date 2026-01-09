import pandas as pd
from typing import Dict, Any, List
from app.services.supabase_service import get_supabase

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

# -------------------------------------------------
def carregar_historico():
    supabase = get_supabase()
    all_data = []
    chunk_size = 1000
    start = 0
    
    while True:
        res = (
            supabase.table("lotofacil_concursos")
            .select("concurso,data,dezenas")
            .order("concurso", desc=False)
            .range(start, start + chunk_size - 1)
            .execute()
        )
        all_data.extend(res.data)
        if len(res.data) < chunk_size:
            break
        start += chunk_size

    if not all_data:
        raise RuntimeError("Histórico vazio")

    return [
        {
            "concurso": r["concurso"],
            "data": r["data"],
            "numeros": [int(n) for n in r["dezenas"]],
        }
        for r in all_data
    ]

# -------------------------------------------------
def obter_estatisticas_base() -> pd.DataFrame:
    historico = carregar_historico()
    df = pd.DataFrame(historico).explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    freq = df["numeros"].value_counts().sort_index()
    ultimo = df["concurso"].max()

    atraso = {
        n: int(ultimo - df[df["numeros"] == n]["concurso"].max())
        for n in range(1, 26)
    }

    return pd.DataFrame({
        "numero": range(1, 26),
        "frequencia": [freq.get(n, 0) for n in range(1, 26)],
        "atraso": [atraso[n] for n in range(1, 26)],
    })

# -------------------------------------------------
def obter_estatisticas_com_score(peso_freq=0.6, peso_atraso=0.4) -> pd.DataFrame:
    df = obter_estatisticas_base()

    # Normalização segura para evitar divisão por zero
    max_f, min_f = df["frequencia"].max(), df["frequencia"].min()
    df["freq_norm"] = (df["frequencia"] - min_f) / (max_f - min_f) if max_f > min_f else 0

    max_a, min_a = df["atraso"].max(), df["atraso"].min()
    df["atraso_norm"] = (df["atraso"] - min_a) / (max_a - min_a) if max_a > min_a else 0

    df["score"] = df["freq_norm"] * peso_freq + df["atraso_norm"] * peso_atraso

    return df.sort_values("score", ascending=False)

# -------------------------------------------------
def calcular_medias_recentes(qtd: int = 10) -> Dict[str, Any]:
    historico = carregar_historico()
    recentes = historico[-qtd:]

    soma = pares = impares = primos = 0

    for r in recentes:
        jogo = r["numeros"]
        soma += sum(jogo)
        pares += sum(1 for n in jogo if n % 2 == 0)
        impares += sum(1 for n in jogo if n % 2 != 0)
        primos += sum(1 for n in jogo if n in PRIMOS)

    return {
        "soma_media": round(soma / qtd, 2),
        "pares_media": round(pares / qtd, 2),
        "impares_media": round(impares / qtd, 2),
        "primos_media": round(primos / qtd, 2),
    }

# -------------------------------------------------
def obter_ciclo_atual() -> Dict[str, Any]:
    """Calcula corretamente os números que faltam para fechar o ciclo"""
    historico = carregar_historico()
    
    todos_25 = set(range(1, 26))
    vistos = set()
    
    # Percorre do mais recente para o mais antigo
    for r in reversed(historico):
        vistos.update(r["numeros"])
        if len(vistos) == 25:
            # Aqui identificamos onde o ciclo anterior fechou. 
            # Mas queremos os que faltam no ciclo ATUAL.
            break

    # Reinicia a lógica para pegar apenas o ciclo aberto atual
    vistos_atual = set()
    for r in reversed(historico):
        # Se ao adicionar esses números completarmos 25, 
        # significa que este concurso fechou um ciclo.
        temp_set = vistos_atual | set(r["numeros"])
        if temp_set == todos_25:
            break
        vistos_atual = temp_set

    faltam = sorted(todos_25 - vistos_atual)

    return {
        "faltam": faltam,
        "total_faltam": len(faltam)
    }

# -------------------------------------------------
def obter_top_listas(df: pd.DataFrame) -> Dict[str, List[int]]:
    return {
        "numeros_quentes": df.head(5)["numero"].tolist(),
        "numeros_frios": df.tail(5)["numero"].tolist(),
        "atrasados_ranking": (
            df.sort_values("atraso", ascending=False)
            .head(5)["numero"]
            .tolist()
        )
    }

