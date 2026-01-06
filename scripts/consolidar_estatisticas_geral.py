from datetime import date
import json
from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    analisar_ciclo,
    obter_estatisticas_com_score
)

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()
    
    print(f"🚀 [05/01/2026] Iniciando Processamento Geral: {hoje}")

    try:
        # 1️⃣ COLETA DE DADOS (Fontes do Service)
        print("📊 Calculando médias, ciclos e scores...")
        analise_medias = calcular_medias_recentes()
        faltantes_ciclo = analisar_ciclo()
        df_scores = obter_estatisticas_com_score()

        if df_scores is None or df_scores.empty:
            print("⚠️ Falha ao obter scores. Abortando.")
            return

        # 2️⃣ PREPARAÇÃO PARA 'estatisticas_diarias_v2' (Cards e Tendências)
        quentes = [int(n) for n in df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()]
        frios = [int(n) for n in df_scores.sort_values("score").head(5)["numero"].tolist()]
        atrasados_ranking = [int(n) for n in df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()]

        payload_diario = {
            "data_referencia": hoje,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": sorted(faltantes_ciclo),
            "media_soma": float(round(analise_medias["soma_media"], 2)),
            "media_pares": float(round(analise_medias["pares_media"], 2)),
            "media_impares": float(round(analise_medias.get("impares_media", 0), 2)),
            "media_primos": float(round(analise_medias.get("primos_media", 0), 2)),
            "sequencias_comuns": [3, 4],
            "faixa_pares": json.dumps({"max": 9, "min": 6, "mais_comum": "7-8"}),
            "atrasados_ranking": atrasados_ranking
        }

        # 3️⃣ PREPARAÇÃO PARA 'estatisticas_numeros' (Gráficos)
        registros_numeros = [
            {
                "data_referencia": hoje,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"]),
            }
            for _, row in df_scores.iterrows()
        ]

        # 4️⃣ EXECUÇÃO NO SUPABASE (Limpeza e Inserção)
        print("💾 Salvando dados no banco...")
        
        # Tabela 1: Resumo Diário
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        # Tabela 2: Números Individuais (O que faltava para os gráficos)
        supabase.table("estatisticas_numeros").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_numeros").insert(registros_numeros).execute()

        print(f"✅ Sucesso! Tabelas de resumo e de gráficos atualizadas para {hoje}.")

    except Exception as e:
        print(f"❌ Erro crítico na consolidação: {e}")

if __name__ == "__main__":
    main()

