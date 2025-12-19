import pandas as pd
from collections import Counter
from app.loader import load_lotofacil_data


def estatisticas_globais():
    df = load_lotofacil_data()

    dezenas = df[[f"bola{i}" for i in range(1, 16)]].values.flatten()

    freq = Counter(dezenas)

    return {
        "total_concursos": int(df.shape[0]),
        "primeiro_concurso": int(df["concurso"].min()),
        "ultimo_concurso": int(df["concurso"].max()),

        "frequencia_dezenas": {
            f"{k:02d}": int(v) for k, v in sorted(freq.items())
        },

        "mais_sorteadas": [
            {"dezena": f"{d:02d}", "frequencia": int(f)}
            for d, f in freq.most_common(10)
        ],

        "menos_sorteadas": [
            {"dezena": f"{d:02d}", "frequencia": int(f)}
            for d, f in sorted(freq.items(), key=lambda x: x[1])[:10]
        ]
    }
