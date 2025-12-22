import random
import datetime
from functools import lru_cache
from app.services.estatisticas_service import obter_estatisticas_base


def classificar_numeros():
    df = obter_estatisticas_base()

    total = len(df)

    quentes = df.head(int(total * 0.30))["numero"].tolist()
    equilibrados = df.iloc[int(total * 0.30):int(total * 0.70)]["numero"].tolist()
    frios = df.tail(int(total * 0.30))["numero"].tolist()

    atrasados = (
        df.sort_values("atraso", ascending=False)
        .head(8)["numero"]
        .tolist()
    )

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }
