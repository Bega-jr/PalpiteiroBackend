import sys
from pathlib import Path
import numpy as np

# -----------------------------------
# Configuração de diretório base
# -----------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    obter_estatisticas_com_score,
    obter_top_listas,
    carregar_historico
)

# -----------------------------------
# Funções auxiliares
# -----------------------------------
def normalizar(col):
    return (col - col.min()) / (col.max() - col.min() + 1e-9)

def calcular_tendencia(historico, numero, janela=25):
    ultimos = historico[-janela:]
    presencas = [1 if numero in h["numeros"] else 0 for h in ultimos]
    return float(np.mean(presencas))

def calcular_ciclo_historico_completo(historico):
    todos_25 = set(range(1, 26))
    sorteados_no_ciclo = set()
    numero_do_ciclo = 1

    for conc in historico:
        sorteados_no_ciclo.update(conc["numeros"])
        if sorteados_no_ciclo == todos_25:
            sorteados_no_ciclo = set()
            numero_do_ciclo += 1

    faltam = sorted(todos_25 - sorteados_no_ciclo)
    if not faltam:
        faltam = list(range(1, 26))

    return faltam, numero_do_ciclo

# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    supabase = get_supabase()
    print("🚀 Processamento Estatístico Probabilístico iniciado")

    try:
        # 1. Histórico completo
        historico = carregar_historico()
        ultimo = historico[-1]

        concurso_atual = ultimo["concurso"]
        data_atual = ultimo["data"]
        dezenas_hoje = set(ultimo["numeros"])

        print(f"📌 Concurso {concurso_atual} | Data {data_atual}")

        # 2. Estatísticas base
        df = obter_estatisticas_com_score()
        medias = calcular_medias_recentes()

        # 3. Zera atraso dos números sorteados hoje
        df.loc[df["numero"].isin(dezenas_hoje), "atraso"] = 0

        # 4. Calcula tendência
        df["tendencia"] = df["numero"].apply(
            lambda n: calcular_tendencia(historico, n)
        )

        # 5. Normalizações
        df["freq_norm"] = normalizar(df["frequencia"])
        df["atraso_norm"] = 1 - normalizar(df["atraso"])
        df["tendencia_norm"] = normalizar(df["tendencia"])
        df["score_norm"] = normalizar(df["score"])

        # 6. Novo score probabilístico (substitui o score antigo)
        df["score"] = (
            df["freq_norm"] * 0.35 +
            df["tendencia_norm"] * 0.30 +
            df["atraso_norm"] * 0.20 +
            df["score_norm"] * 0.15
        )

        # 7. Rankings e ciclo
        listas = obter_top_listas(df)
        numeros_faltantes, ciclo_contagem = calcular_ciclo_historico_completo(historico)

        # 8. Estatísticas globais (mantidas)
        payload_diario = {
            "data_referencia": data_atual,
            "concurso": int(concurso_atual),
            "numero_ciclo": int(ciclo_contagem),
            "numeros_quentes": listas["numeros_quentes"],
            "numeros_frios": listas["numeros_frios"],
            "numeros_atrasados": numeros_faltantes,
            "atrasados_ranking": listas["atrasados_ranking"],
            "media_soma": float(medias.get("soma_media", 0)),
            "media_pares": float(medias.get("pares_media", 0)),
            "media_impares": float(medias.get("impares_media", 0)),
            "media_primos": float(medias.get("primos_media", 0)),
            "sequencias_comuns": [3, 4]
        }

        supabase.table("estatisticas_diarias_v2") \
            .delete().eq("data_referencia", data_atual).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()

        # 9. Estatísticas por número (compatível com a tabela atual)
        payload_numeros = [
            {
                "data_referencia": data_atual,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"]),
                "tendencia": float(row["tendencia"])
            }
            for _, row in df.iterrows()
        ]

        supabase.table("estatisticas_numeros") \
            .delete().eq("data_referencia", data_atual).execute()
        supabase.table("estatisticas_numeros").insert(payload_numeros).execute()

        print("✅ Estatísticas atualizadas com score probabilístico")
        print(f"🎯 Ciclo {ciclo_contagem} | Base pronta para geração")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

