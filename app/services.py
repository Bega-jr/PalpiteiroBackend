from app.loader import load_lotofacil_data
from app.utils import format_dezena

def get_concurso(concurso_id: int):
    df = load_lotofacil_data()
    row = df[df["concurso"] == concurso_id].iloc[0]

    dezenas = sorted([
        format_dezena(row[f"bola{i}"])
        for i in range(1, 16)
    ])

    return {
        "concurso": int(row["concurso"]),
        "data_sorteio": row["data_sorteio"],
        "dezenas": dezenas,
        "premio_principal": row["rateio_15"],
        "rateios": [
            {
                "faixa": 15,
                "ganhadores": row["ganhadores_15"],
                "premio_individual": row["rateio_15"],
                "total": row["ganhadores_15"] * row["rateio_15"],
            },
            {
                "faixa": 14,
                "ganhadores": row["ganhadores_14"],
                "premio_individual": row["rateio_14"],
                "total": row["ganhadores_14"] * row["rateio_14"],
            },
            {
                "faixa": 13,
                "ganhadores": row["ganhadores_13"],
                "premio_individual": row["rateio_13"],
                "total": row["ganhadores_13"] * row["rateio_13"],
            },
            {
                "faixa": 12,
                "ganhadores": row["ganhadores_12"],
                "premio_individual": row["rateio_12"],
                "total": row["ganhadores_12"] * row["rateio_12"],
            },
            {
                "faixa": 11,
                "ganhadores": row["ganhadores_11"],
                "premio_individual": row["rateio_11"],
                "total": row["ganhadores_11"] * row["rateio_11"],
            },
        ],
        "arrecadacao": row["arrecadacao"],
        "estimativa_premio": row["estimativa_premio"],
        "observacao": row["observacao"],
    }
