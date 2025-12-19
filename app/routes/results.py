from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter(
    prefix="/lotofacil",
    tags=["Lotofácil"]
)


@router.get("/concurso/{numero}")
def obter_concurso(numero: int):
    try:
        df = load_lotofacil_data()

        resultado = df[df["Concurso"] == numero]

        if resultado.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {numero} não encontrado"
            )

        return {
            "status": "ok",
            "concurso": resultado.iloc[0].to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
