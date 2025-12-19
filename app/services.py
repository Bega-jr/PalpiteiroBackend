from fastapi import HTTPException
from app.loader import load_lotofacil_data
from app.utils import format_dezena


def get_concurso(concurso_id: int):
    df = load_lotofacil_data()

    resultado = df[df["concurso"] == concurso_id]

    if resultado.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Concurso {concurso_id} não encontrado"
        )

    row = resultado.iloc[0]

    dezenas = sorted(
        format_dezena(row[f"bola{i}"])
        for i in range(1, 16)
    )

    return {
        "concurso": int(row["concurso"]),
        "data_sorteio": str(row["data_sorteio"]),
        "dezenas": dezenas,
        "premio_principal": float(row["rateio_15"]),
        "ganhadores_15": int(row["ganhadores_15"]),
        "arrecadacao": float(row["arrecadacao"]),
        "observacao": row["observacao"]
    }


def get_ultimos_concursos(qtd: int = 5):
    df = load_lotofacil_data()

    df = df.sort_values(by="concurso", ascending=False).head(qtd)

    concursos = []

    for _, row in df.iterrows():
        concursos.append({
            "concurso": int(row["concurso"]),
            "data_sorteio": str(row["data_sorteio"]),
            "dezenas": sorted(
                format_dezena(row[f"bola{i}"])
                for i in range(1, 16)
            ),
            "premio_principal": float(row["rateio_15"]),
            "ganhadores_15": int(row["ganhadores_15"]),
            "acumulado": float(row["acumulado_15"])
        })

    return concursos
