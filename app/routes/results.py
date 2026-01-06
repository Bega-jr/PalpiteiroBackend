from fastapi import APIRouter, HTTPException, Query
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("")
def listar_resultados(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    try:
        df = load_lotofacil_data()

        total = len(df)

        if total == 0:
            return {
                "status": "ok",
                "page": page,
                "limit": limit,
                "total": 0,
                "data": []
            }

        # 🔁 ORDENAR DO MAIS RECENTE PARA O MAIS ANTIGO
        df = df.sort_values(by="Concurso", ascending=False)

        start = (page - 1) * limit
        end = start + limit

        page_df = df.iloc[start:end]

        return {
            "status": "ok",
            "page": page,
            "limit": limit,
            "total": total,
            "data": page_df.to_dict(orient="records")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar resultados: {str(e)}"
        )


@router.get("/total")
def total_resultados():
    try:
        df = load_lotofacil_data()
        return {
            "status": "ok",
            "total": len(df)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter total: {str(e)}"
        )


@router.get("/{numero}")
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
