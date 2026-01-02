from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data
import pandas as pd

router = APIRouter(prefix="/ultimos", tags=["Últimos Resultados"])

@router.get("/{quantidade}")
def ultimos_concursos(quantidade: int):
    try:
        if quantidade <= 0:
            return []

        df = load_lotofacil_data()
        
        # Pega os últimos registros e inverte para o mais recente aparecer primeiro
        ultimos = df.tail(quantidade).iloc[::-1].copy()

        registros = []
        for _, row in ultimos.iterrows():
            # Agrupa as colunas bola1...bola15 em uma lista 'dezenas'
            # Isso é o que o seu frontend espera para renderizar as bolinhas
            dezenas = [int(row[f'bola{i}']) for i in range(1, 16) if f'bola{i}' in row]
            
            registros.append({
                "concurso": int(row["concurso"]),
                "data": str(row["data"]),
                "dezenas": dezenas
            })

        # Retorna a lista pura para o .map() do frontend funcionar
        return registros

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar últimos concursos: {str(e)}"
        )
