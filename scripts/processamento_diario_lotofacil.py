import sys
from pathlib import Path
import numpy as np
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    obter_estatisticas_com_score,
    carregar_historico
)

# ======================================================
# UTILITÁRIOS
# ======================================================
def normalizar(col):
    return (col - col.min()) / (col.max() - col.min() + 1e-9)

def calcular_tendencia(historico, numero, janela=25):
    ultimos = historico[-janela:]
    presencas = [1 if numero in h["numeros"] else 0 for h in ultimos]
    return float(np.mean(presencas))

def calcular_ciclo_historico_completo(historico):
    todos_25 = set(range(1, 26))
    sorteados = set()
    ciclo = 1
    for conc in historico:
        sorteados.update(conc["numeros"])
        if sorteados == todos_25:
            sorteados = set()
            ciclo += 1
    faltam = sorted(todos_25 - sorteados)
    return (faltam if faltam else list(range(1, 26))), ciclo

def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }

# ======================================================
# INTELIGÊNCIA DE MEMÓRIA (SCORE REAL)
# ======================================================
def buscar_cenario_similar(supabase, estrutura):
    res = supabase.table("memoria_cenarios").select("*") \
        .eq("soma_faixa", estrutura["soma_faixa"]) \
        .eq("pares", estrutura["pares"]) \
        .eq("primos", estrutura["primos"]) \
        .execute()

    if not res.data: return None

    melhor = None
    menor_diff = 999
    for r in res.data:
        diff = sum(abs(a - b) for a, b in zip(r["linhas"], estrutura["linhas"]))
        if diff < menor_diff:
            menor_diff = diff
            melhor = r
    return melhor

def ajustar_por_memoria(df, memoria):
    if not memoria:
        print("🧠 Sem memória prévia (Novo Cenário). Score Real: 0.0")
        return df

    score_real = float(memoria.get("score_medio_real", 0))
    vezes = memoria.get("vezes_gerado", 0)
    
    print(f"🧠 Memória Ativa | Score Real: {score_real:.2f} | Testado: {vezes}x")

    if score_real >= 5:
        print("🔥 BÔNUS: Cenário de alta performance detectado (+15%)")
        df["score"] *= 1.15
    elif score_real >= 1:
        print("📈 BÔNUS: Cenário consistente (+5%)")
        df["score"] *= 1.05
    elif vezes > 5 and score_real == 0:
        print("❄️ PENALIDADE: Cenário testado 5x sem prêmio (-15%)")
        df["score"] *= 0.85

    return df

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    print("🚀 [v4.1] Processamento Inteligente Iniciado")

    try:
        historico = carregar_historico()
        ultimo = historico[-1]
        concurso, data, dezenas = ultimo["concurso"], ultimo["data"], ultimo["numeros"]

        print(f"📌 Concurso {concurso} | Data {data}")

        df = obter_estatisticas_com_score()
        df.loc[df["numero"].isin(dezenas), "atraso"] = 0
        df["tendencia"] = df["numero"].apply(lambda n: calcular_tendencia(historico, n))

        # Normalização
        df["freq_norm"] = normalizar(df["frequencia"])
        df["atraso_norm"] = 1 - normalizar(df["atraso"])
        df["tendencia_norm"] = normalizar(df["tendencia"])
        df["score_norm"] = normalizar(df["score"])

        # Cálculo do Score Base
        df["score"] = (df["freq_norm"] * 0.35 + df["tendencia_norm"] * 0.30 +
                       df["atraso_norm"] * 0.20 + df["score_norm"] * 0.15)

        # Inteligência de Memória
        est = extrair_estrutura(dezenas)
        memoria = buscar_cenario_similar(supabase, est)
        df = ajustar_por_memoria(df, memoria)

        # Upsert Memória Estrutural
        payload_memoria = {
            "soma_faixa": est["soma_faixa"], "pares": est["pares"],
            "primos": est["primos"], "linhas": est["linhas"],
            "ultima_aparicao": data, "updated_at": datetime.now().isoformat()
        }
        supabase.table("memoria_cenarios").upsert(payload_memoria, on_conflict="soma_faixa,pares,primos,linhas").execute()
        print("✅ Memória estrutural atualizada")

        # Regimes e Ciclos
        faltantes, ciclo = calcular_ciclo_historico_completo(historico)
        media_score = df[df["numero"].isin(dezenas)]["score"].mean()
        
        regime = "NEUTRO"
        if media_score > 0.55: regime = "EXPANSAO_QUENTES"
        elif media_score < 0.45: regime = "CONTRACAO_FRIAS"

        # Memória de Regimes
        check = supabase.table("memoria_regimes").select("id").eq("concurso", int(concurso)).execute()
        if not check.data:
            payload_regime = {
                "data_referencia": data, "concurso": int(concurso),
                "numero_ciclo": int(ciclo), "tipo_regime": regime,
                "score_global": float(media_score), "media_soma": float(sum(dezenas)),
                "media_pares": int(est["pares"])
            }
            supabase.table("memoria_regimes").insert(payload_regime).execute()
            print(f"📡 Memória de Regimes atualizada: {regime} (Score Global: {media_score:.4f})")
        else:
            print(f"ℹ️ Regime do concurso {concurso} já existe na base. Pulando registro.")

        print("✅ Estatísticas prontas")
        print(f"🎯 Ciclo {ciclo}")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


