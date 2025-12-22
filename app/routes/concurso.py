from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("/concurso/{numero}")
def obter_concurso(numero: int):
    try:
        df = load_lotofacil_data()

        # ✅ coluna já vem normalizada
        if "concurso" not in df.columns:
            raise HTTPException(
                status_code=500,
                detail="Coluna 'concurso' não encontrada"
            )

        df["concurso"] = df["concurso"].astype(int)

        resultado = df[df["concurso"] == numero]

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
