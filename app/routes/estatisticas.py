from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("/estatisticas")
def estatisticas():
    try:
        df = load_lotofacil_data()

        bolas = [f"bola{i}" for i in range(1, 16)]

        total_concursos = len(df)

        # Frequência dos números
        frequencia = (
            df[bolas]
            .stack()
            .value_counts()
            .sort_index()
            .to_dict()
        )

        numero_mais_sorteado = max(frequencia, key=frequencia.get)
        numero_menos_sorteado = min(frequencia, key=frequencia.get)

        # Atraso dos números
        ultimo_concurso = df["concurso"].max()
        atraso = {}

        for n in range(1, 26):
            concursos_numero = df[df[bolas].isin([n]).any(axis=1)]["concurso"]
            atraso[n] = int(ultimo_concurso - concursos_numero.max())

        return {
            "status": "ok",
            "total_concursos": total_concursos,
            "frequencia": frequencia,
            "numero_mais_sorteado": numero_mais_sorteado,
            "numero_menos_sorteado": numero_menos_sorteado,
            "atraso": atraso
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar estatísticas: {str(e)}"
        )
