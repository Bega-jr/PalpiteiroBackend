import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data


def gerar_estatisticas_lotofacil():
    """
    Gera estatísticas básicas da Lotofácil a partir do histórico carregado.
    Compatível com CSV remoto (acentos, ;, colunas da Caixa).
    """

    df = load_lotofacil_data()

    if df.empty:
        raise RuntimeError("DataFrame da Lotofácil está vazio")

    # 🔹 Normaliza nomes das colunas (remove acento, espaço, caixa)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("á", "a")
        .str.replace("ã", "a")
        .str.replace("ç", "c")
        .str.replace("é", "e")
        .str.replace("í", "i")
        .str.replace("ó", "o")
        .str.replace("ú", "u")
    )

    # 🔹 Colunas das dezenas
    dezenas = [f"bola{i}" for i in range(1, 16)]

    # 🔹 Validação defensiva
    for col in dezenas:
        if col not in df.columns:
            raise RuntimeError(f"Coluna '{col}' não encontrada no histórico")

    total_concursos = int(df.shape[0])

    # 🔹 Frequência dos números
    numeros_frequencia = (
        df[dezenas]
        .astype(int)
        .stack()
        .value_counts()
        .sort_index()
        .to_dict()
    )

    numero_mais_sorteado = max(
        numeros_frequencia,
        key=numeros_frequencia.get
    )

    numero_menos_sorteado = min(
        numeros_frequencia,
        key=numeros_frequencia.get
    )

    estatisticas = {
        "total_concursos": total_concursos,
        "frequencia_numeros": numeros_frequencia,
        "numero_mais_sorteado": int(numero_mais_sorteado),
        "numero_menos_sorteado": int(numero_menos_sorteado),
    }

    return estatisticas
