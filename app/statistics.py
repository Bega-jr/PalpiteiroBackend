from app.services.lotofacil_service import carregar_dataframe


def gerar_estatisticas():
    df = carregar_dataframe()

    dezenas = []
    for i in range(1, 16):
        dezenas.extend(df[f"Bola{i}"].tolist())

    frequencia = {i: dezenas.count(i) for i in range(1, 26)}

    return {
        "total_concursos": int(df.shape[0]),
        "frequencia_dezenas": frequencia,
        "mais_sorteados": sorted(frequencia, key=frequencia.get, reverse=True)[:5],
        "menos_sorteados": sorted(frequencia, key=frequencia.get)[:5],
    }
