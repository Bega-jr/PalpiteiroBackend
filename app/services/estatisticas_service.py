import pandas as pd
import os
from app.services.historico_service import _carregar_historico

# =====================================================
# AUXILIAR: CARREGAMENTO E CONVERSÃO DO CSV
# =====================================================

def carregar_dados_para_estatistica():
    """
    Lê o CSV com colunas bola1...bola15 e transforma no formato lista
    """
    caminho_csv = os.path.join(os.getcwd(), "data", "Lotofacil.csv")
    
    if os.path.exists(caminho_csv):
        try:
            df = pd.read_csv(caminho_csv)
            if df.empty:
                return []
            
            # Identifica as colunas de bola1 até bola15
            colunas_bolas = [f'bola{i}' for i in range(1, 16)]
            
            # Cria a coluna 'numeros' como uma lista das bolas
            df['numeros'] = df[colunas_bolas].values.tolist()
            
            # Mantém apenas o que o serviço precisa
            return df[['concurso', 'data', 'numeros']].to_dict('records')
        except Exception as e:
            print(f"Erro ao processar CSV: {e}")
    
    # Se o CSV falhar, tenta o banco (Supabase)
    return _carregar_historico()

# =====================================================
# ESTATÍSTICAS BASE (FREQUÊNCIA + ATRASO)
# =====================================================

def obter_estatisticas_base():
    historico = carregar_dados_para_estatistica()
    
    if not historico:
        raise RuntimeError("Histórico vazio: Verifique se /data/Lotofacil.csv está no repositório.")

    df = pd.DataFrame(historico)
    
    # Explode a lista de números para que cada bola vire uma linha
    df = df.explode("numeros")
    df["numeros"] = df["numeros"].astype(int)

    # -----------------------------
    # FREQUÊNCIA
    # -----------------------------
    freq = df["numeros"].value_counts().sort_index()

    freq_df = pd.DataFrame({
        "numero": freq.index,
        "frequencia": freq.values
    })

    # -----------------------------
    # ATRASO
    # -----------------------------
    # No seu CSV existe a coluna 'concurso', vamos usá-la
    ultimo_concurso = df["concurso"].max()

    atraso = {}
    for n in range(1, 26):
        # Filtra as linhas onde o número saiu e pega o maior concurso
        jogos_com_n = df[df["numeros"] == n]
        if not jogos_com_n.empty:
            ult = jogos_com_n["concurso"].max()
            atraso[n] = int(ultimo_concurso - ult)
        else:
            atraso[n] = int(ultimo_concurso)

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return freq_df.reset_index(drop=True)


# =====================================================
# SCORE COMBINADO (NORMALIZADO)
# =====================================================

def obter_estatisticas_com_score(peso_frequencia=0.6, peso_atraso=0.4):
    df = obter_estatisticas_base().copy()

    fmin, fmax = df["frequencia"].min(), df["frequencia"].max()
    amin, amax = df["atraso"].min(), df["atraso"].max()

    df["freq_norm"] = (
        (df["frequencia"] - fmin) / (fmax - fmin)
        if fmax != fmin else 0
    )

    df["atraso_norm"] = (
        (df["atraso"] - amin) / (amax - amin)
        if amax != amin else 0
    )

    df["score"] = (
        df["freq_norm"] * peso_frequencia +
        df["atraso_norm"] * peso_atraso
    )

    return df.sort_values("score", ascending=False).reset_index(drop=True)


# =====================================================
# SCORE ADAPTATIVO (APRENDIZADO REAL)
# =====================================================

def obter_estatisticas_adaptativas():
    historico = carregar_dados_para_estatistica()
    
    if not historico:
        return obter_estatisticas_com_score()

    df_hist = pd.DataFrame(historico)
    
    # Verifica se há dados de performance (acertos) no histórico
    if "acertos" not in df_hist.columns:
        return obter_estatisticas_com_score()

    df_hist = df_hist.explode("numeros")
    df_hist["numeros"] = df_hist["numeros"].astype(int)

    df_hist["peso"] = df_hist.get("acertos", 0).fillna(0) * 1.0

    aprendizado = (
        df_hist.groupby("numeros")["peso"]
        .mean()
        .reset_index()
        .rename(columns={"numeros": "numero"})
    )

    base = obter_estatisticas_com_score()
    base = base.merge(aprendizado, on="numero", how="left")
    base["peso"] = base["peso"].fillna(0)

    base["score_adaptativo"] = (
        base["score"] * 0.7 +
        base["peso"] * 0.3
    )

    return base.sort_values("score_adaptativo", ascending=False).reset_index(drop=True)


# =====================================================
# MÉTRICAS DE UM JOGO
# =====================================================

def calcular_metricas_jogo(jogo):
    jogo = sorted(set(jogo))

    soma = sum(jogo)
    pares = sum(1 for n in jogo if n % 2 == 0)

    maior_seq = seq = 1
    for i in range(1, len(jogo)):
        if jogo[i] == jogo[i - 1] + 1:
            seq += 1
            maior_seq = max(maior_seq, seq)
        else:
            seq = 1

    return {
        "soma": soma,
        "pares": pares,
        "impares": len(jogo) - pares,
        "maior_sequencia": maior_seq
    }

