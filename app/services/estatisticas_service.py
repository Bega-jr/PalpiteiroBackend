import pandas as pd
import os
from typing import Dict, Any
from app.services.historico_service import _carregar_historico

# Constantes Estratégicas para 2025/2026
PRIMOS = [2, 3, 5, 7, 11, 13, 17, 19, 23]
MOLDURA = [1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25]
CENTRO = [7, 8, 9, 12, 13, 14, 17, 18, 19]

def carregar_dados_para_estatistica():
    caminho_csv = os.path.join(os.getcwd(), "data", "Lotofacil.csv")
    if os.path.exists(caminho_csv):
        try:
            df = pd.read_csv(caminho_csv)
            if df.empty: return []
            colunas_bolas = [f'bola{i}' for i in range(1, 16)]
            df['numeros'] = df[colunas_bolas].values.tolist()
            return df[['concurso', 'data', 'numeros']].to_dict('records')
        except Exception as e:
            print(f"Erro ao processar CSV: {e}")
    return _carregar_historico()

def obter_proximo_concurso():
    caminho_csv = os.path.join(os.getcwd(), "data", "Lotofacil.csv")
    if os.path.exists(caminho_csv):
        try:
            df = pd.read_csv(caminho_csv)
            if not df.empty: return int(df["concurso"].max() + 1)
        except: pass
    return 1

def obter_ultimo_resultado():
    historico = carregar_dados_para_estatistica()
    if not historico: return []
    return historico[-1]['numeros']

def analisar_ciclo():
    historico = carregar_dados_para_estatistica()
    if not historico: return []
    
    numeros_sorteados_no_ciclo = set()
    for sorteio in reversed(historico):
        numeros_sorteados_no_ciclo.update(sorteio['numeros'])
        if len(numeros_sorteados_no_ciclo) == 25:
            numeros_sorteados_no_ciclo = set(sorteio['numeros'])
            break
            
    faltantes = set(range(1, 26)) - numeros_sorteados_no_ciclo
    return list(faltantes)

def obter_estatisticas_base():
    historico = carregar_dados_para_estatistica()
    if not historico: raise RuntimeError("Histórico vazio.")
    df = pd.DataFrame(historico).explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    freq = df["numeros"].value_counts().sort_index()
    freq_df = pd.DataFrame({"numero": freq.index, "frequencia": freq.values})

    ultimo_concurso = df["concurso"].max()
    atraso = {n: int(ultimo_concurso - (df[df["numeros"] == n]["concurso"].max() or 0)) for n in range(1, 26)}
    freq_df["atraso"] = freq_df["numero"].map(atraso)
    return freq_df.reset_index(drop=True)

def obter_estatisticas_com_score(peso_frequencia=0.6, peso_atraso=0.4):
    df = obter_estatisticas_base().copy()
    fmin, fmax = df["frequencia"].min(), df["frequencia"].max()
    amin, amax = df["atraso"].min(), df["atraso"].max()
    df["freq_norm"] = (df["frequencia"] - fmin) / (fmax - fmin) if fmax != fmin else 0
    df["atraso_norm"] = (df["atraso"] - amin) / (amax - amin) if amax != amin else 0
    df["score"] = df["freq_norm"] * peso_frequencia + df["atraso_norm"] * peso_atraso
    return df.sort_values("score", ascending=False).reset_index(drop=True)

def calcular_metricas_jogo(jogo):
    jogo = sorted(set(jogo))
    pares = sum(1 for n in jogo if n % 2 == 0)
    primos = sum(1 for n in jogo if n in PRIMOS)
    moldura = sum(1 for n in jogo if n in MOLDURA)
    
    maior_seq = seq = 1
    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            seq += 1
            maior_seq = max(maior_seq, seq)
        else: seq = 1
            
    return {
        "soma": sum(jogo),
        "pares": pares,
        "impares": 15 - pares,
        "primos": primos,
        "moldura": moldura,
        "centro": 15 - moldura,
        "maior_sequencia": maior_seq
    }

# --- NOVA FUNÇÃO DE INTEGRAÇÃO COM O FRONTEND ---

def montar_dashboard_estatisticas() -> Dict[str, Any]:
    """
    Consolida todos os cálculos acima no formato JSON esperado pelo Layout React.
    """
    try:
        # 1. Obtém estatísticas individuais de cada número
        df_stats = obter_estatisticas_com_score()
        # Converte para lista de dicionários e ordena pelo número (01 a 25) para o gráfico
        lista_stats = df_stats.to_dict('records')
        lista_stats_ordenada = sorted(lista_stats, key=lambda x: x['numero'])

        # 2. Calcula médias dos últimos 10 concursos para o resumo
        historico = carregar_dados_para_estatistica()
        ultimos_sorteios = historico[-10:] if historico else []
        
        metricas_acumuladas = {"soma": [], "pares": [], "impares": [], "primos": []}
        for s in ultimos_sorteios:
            m = calcular_metricas_jogo(s['numeros'])
            metricas_acumuladas["soma"].append(m["soma"])
            metricas_acumuladas["pares"].append(m["pares"])
            metricas_acumuladas["impares"].append(m["impares"])
            metricas_acumuladas["primos"].append(m["primos"])

        qtd = len(ultimos_sorteios) if ultimos_sorteios else 1
        
        # 3. Obtém números que faltam para fechar o ciclo
        faltantes_ciclo = analisar_ciclo()

        # 4. Retorno formatado para o componente React
        return {
            "estatisticas": lista_stats_ordenada,
            "analise": {
                "soma_media": sum(metricas_acumuladas["soma"]) / qtd,
                "pares_media": sum(metricas_acumuladas["pares"]) / qtd,
                "impares_media": sum(metricas_acumuladas["impares"]) / qtd,
                "primos_media": sum(metricas_acumuladas["primos"]) / qtd,
                "data_referencia": historico[-1]['data'] if historico else None
            },
            "ciclo": {
                "faltam": sorted(faltantes_ciclo),
                "total_faltam": len(faltantes_ciclo)
            }
        }
    except Exception as e:
        print(f"Erro ao montar dashboard: {e}")
        return {
            "estatisticas": [],
            "analise": None,
            "ciclo": {"faltam": [], "total_faltam": 0}
        }
