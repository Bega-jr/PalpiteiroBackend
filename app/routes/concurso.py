from fastapi import APIRouter, HTTPException
# Correção do import para o novo nome do arquivo de serviço
from app.services.resultados_service import load_lotofacil_data, fetch_concurso_api, normalizar_api

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/{numero}")
def obter_concurso(numero: int):
    try:
        # 1. Carrega os dados do CSV (Lotofacil.csv)
        dados = load_lotofacil_data()
        
        # 2. Busca o concurso específico na lista
        resultado = None
        for row in dados:
            # Comparamos o número do concurso (garantindo que ambos sejam int)
            if int(row.get("concurso", 0)) == numero:
                resultado = row
                break

        # 3. Se não achou no CSV, tenta buscar direto na API da Caixa
        if not resultado:
            api_data = fetch_concurso_api(str(numero))
            if api_data:
                return normalizar_api(api_data)
            
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {numero} não encontrado na base local nem na API."
            )

        # 4. Formata as dezenas (aceita bola1...15 ou dezena1...15)
        dezenas = []
        for i in range(1, 16):
            valor = resultado.get(f'bola{i}') or resultado.get(f'dezena{i}')
            if valor:
                dezenas.append(int(valor))

        # 5. Retorna no formato exato que o seu Front-end usa
        return {
            "concurso": int(resultado["concurso"]),
            "data": str(resultado.get("data") or resultado.get("data_sorteio")),
            "dezenas": dezenas
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar concurso: {str(e)}")

@router.get("/ultimo/concurso") # Alterado levemente o path para evitar conflito com a rota /{numero}
def obter_ultimo_concurso():
    """Rota auxiliar para pegar o concurso mais recente"""
    try:
        dados = load_lotofacil_data()
        
        if not dados:
            # Fallback para API da Caixa caso o CSV falhe
            api_data = fetch_concurso_api("latest")
            if api_data:
                return normalizar_api(api_data)
            raise HTTPException(status_code=404, detail="Nenhum dado disponível")

        # Pega a última linha do CSV
        ultimo_row = dados[-1]
        
        dezenas = []
        for i in range(1, 16):
            valor = ultimo_row.get(f'bola{i}') or ultimo_row.get(f'dezena{i}')
            if valor:
                dezenas.append(int(valor))

        return {
            "concurso": int(ultimo_row["concurso"]),
            "data": str(ultimo_row.get("data") or ultimo_row.get("data_sorteio")),
            "dezenas": dezenas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


