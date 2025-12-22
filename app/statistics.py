from app.services.lotofacil_service import load_lotofacil_data


def gerar_estatisticas_lotofacil():
    df = load_lotofacil_data()

    dezenas = [f"bola{i}" for i in range(1, 16)]

    total_concursos = int(df.shape[0])

    numeros_frequencia = (
        df[dezenas]
        .stack()
        .value_counts()
        .sort_index()
        .to_dict()
    )

    estatisticas = {
        "total_concursos": total_concursos,
        "frequencia_numeros": numeros_frequencia,
        "numero_mais_sorteado": max(numeros_frequencia, key=numeros_frequencia.get),
        "numero_menos_sorteado": min(numeros_frequencia, key=numeros_frequencia.get),
    }

    return estatisticas

