from fastapi import APIRouter, HTTPException
from app.services.resultados_service import load_lotofacil_data, fetch_concurso_api, normalizar_api

router = APIRouter(prefix="/ultimos", tags=["Últimos Resultados"])

@router.get("/{quantidade}")
def ultimos_concursos(quantidade: int):
    try:
        if quantidade <= 0:
            return []

        # 1. Tenta carregar do seu arquivo Lotofacil.csv
        dados_csv = load_lotofacil_data()
        
        # 2. Se o CSV tiver dados, processa eles
        if dados_csv:
            # Pega os últimos do CSV (geralmente os mais recentes estão no fim)
            ultimos_registros = dados_csv[-quantidade:][::-1]
            
            resultado = []
            for row in ultimos_registros:
                # Busca dezenas em colunas bola1...15 ou dezena1...15
                dezenas = []
                for i in range(1, 16):
                    v = row.get(f'bola{i}') or row.get(f'dezena{i}') or row.get(f'BOLA{i}')
                    if v: dezenas.append(int(v))
                
                resultado.append({
                    "concurso": int(row.get("concurso") or row.get("Concurso") or 0),
                    "data": row.get("data") or row.get("Data") or "",
                    "dezenas": dezenas
                })
            return resultado

        # 3. Se o CSV falhar ou estiver vazio, busca o último direto da API da Caixa
        api_data = fetch_concurso_api()
        if api_data:
            return [normalizar_api(api_data)]

        raise HTTPException(status_code=404, detail="Não foi possível obter dados.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
