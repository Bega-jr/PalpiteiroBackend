from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("/ultimos/{quantidade}")
def ultimos_concursos(quantidade: int):
    try:
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        df = load_lotofacil_data()

        if quantidade > len(df):
            quantidade = len(df)

        ultimos = df.tail(quantidade)

        return {
            "status": "ok",
            "quantidade": quantidade,
            "concursos": ultimos.to_dict(orient="records")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar últimos concursos: {str(e)}"
        )
