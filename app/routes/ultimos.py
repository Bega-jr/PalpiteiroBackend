from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data
import pandas as pd

router = APIRouter()


@router.get("/ultimos/{quantidade}")
def ultimos_concursos(quantidade: int):
    try:
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        df = load_lotofacil_data()

        if quantidade > len(df):
            quantidade = len(df)

        ultimos = df.tail(quantidade).copy()

        # 🔧 SANITIZAÇÃO (resolve erro 500)
        ultimos = ultimos.where(pd.notnull(ultimos), None)

        # Converte tudo para tipos simples
        registros = []
        for _, row in ultimos.iterrows():
            item = {}
            for col, val in row.items():
                if hasattr(val, "item"):
                    item[col] = val.item()
                else:
                    item[col] = val
            registros.append(item)

        return {
            "status": "ok",
            "quantidade": quantidade,
            "concursos": registros
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar últimos concursos: {str(e)}"
        )
