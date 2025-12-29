import pandas as pd
from pathlib import Path
from typing import Dict


# =====================================================
# CONFIGURAÇÃO
# =====================================================

CSV_PATH = Path("app/data/Lotofacil.CSV")


# =====================================================
# LEITURA DO CSV (FONTE ÚNICA DA VERDADE)
# =====================================================

def carregar_lotofacil_df() -> pd.DataFrame:
    """
    Carrega o CSV da Lotofácil e retorna apenas as colunas das dezenas.
    Detecta automaticamente colunas bola/dez/n.
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError("Arquivo Lotofacil.CSV não encontrado em app/data")

    df = pd.read_csv(CSV_PATH)

    # Detecta colunas das dezenas automaticamente
    dezenas = [
        c for c in df.columns
        if c.lower().startswith(("bola", "dez", "n"))
    ]

    if len(dezenas) != 15:
        raise ValueError(
            f"CSV inválido: esperado 15 dezenas, encontrado {len(dezenas)}"
        )

    return df[dezenas].astype(int)


# =====================================================
# ESTATÍSTICAS BASE (FREQUÊNCIA)
# =====================================================

def calcular_frequencia() -> Dict[int, int]:
    """
    Retorna a frequência absoluta de cada número (1–25)
    com base em TODO o histórico do CSV.
    """
    df = carregar_lotofacil_df()
    todos_numeros = df.values.flatten()

    frequencia = {
        numero: int((todos_numeros == numero).sum())
        for numero in range(1, 26)
    }

    return frequencia


# =====================================================
# ATRASO POR NÚMERO
# =====================================================

def calcular_atraso() -> Dict[int, int]:
    """
    Calcula o atraso de cada número com base no índice do concurso.
    """
    df = carregar_lotofacil_df()
    total_concursos = len(df)

    atraso = {}

    for numero in range(1, 26):
        linhas = df.eq(numero).any(axis=1)
        ult_aparicao = linhas[linhas].index.max()

        atraso[numero] = (
            int(total_concursos - ult_aparicao - 1)
            if pd.notna(ult_aparicao)
            else total_concursos
        )

    return atraso


# =====================================================
# ESTATÍSTICAS CONSOLIDADAS
# =====================================================

def estatisticas_base() -> dict:
    """
    Estatísticas completas da Lotofácil baseadas no CSV.
    """
    df = carregar_lotofacil_df()
    frequencia = calcular_frequencia()
    atraso = calcular_atraso()

    return {
        "total_concursos": len(df),
        "frequencia_numeros": frequencia,
        "atraso": atraso,
        "numero_mais_sorteado": max(frequencia, key=frequencia.get),
        "numero_menos_sorteado": min(frequencia, key=frequencia.get),
        "numero_mais_atrasado": max(atraso, key=atraso.get),
    }
