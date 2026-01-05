from datetime import date
import pandas as pd
from app.core.supabase import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    analisar_ciclo,
    obter_estatisticas_com_score
)

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()
    
    print(f"🚀 Iniciando consolidação estatística para: {hoje}")

    try:
        # 1️⃣ Obter dados de diferentes fontes de serviço
        print("📊 Calculando médias e análise de ciclo...")
        analise_medias = calcular_medias_recentes()
        faltantes_ciclo = analisar_ciclo()
        
        print("📈 Calculando scores e frequências...")
        df_scores = obter_estatisticas_com_score()

        if df_scores is None or df_scores.empty:
            print("⚠️ Erro: Nenhum dado retornado de obter_estatisticas_com_score()")
            return

        # 2️⃣ Processar Rankings (Quentes, Frios e Atrasados)
        quentes = df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()
        frios = df_scores.sort_values("score").head(5)["numero"].tolist()
        atrasados_ranking = df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()

        # 3️⃣ Montar Payload Único (Unificando Script 1 e Script 2)
        payload_diario = {
            "data_referencia": hoje,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": sorted(faltantes_ciclo), # Dados do Script 1
            "atrasados_ranking": atrasados_ranking,       # Top 5 mais atrasados
            "media_soma": round(analise_medias["soma_media"], 2),
            "media_pares": round(analise_medias["pares_media"], 2),
            "media_impares": round(analise_medias["impares_media"], 2),
            "media_primos": round(analise_medias["primos_media"], 2),
            "sequencias_comuns": [3, 4],
            "faixa_pares": {
                "min": 6,
                "max": 9,
                "mais_comum": "7-8"
            }
        }

        # 4️⃣ Operação no Supabase (Idempotente)
        # Limpa para evitar duplicidade no mesmo dia
        supabase.table("estatisticas_diarias_v2") \
            .delete() \
            .eq("data_referencia", hoje) \
            .execute()

        # Insere o payload consolidado
        supabase.table("estatisticas_diarias_v2") \
            .insert(payload_diario) \
            .execute()
        
        print("✅ Tabela 'estatisticas_diarias_v2' atualizada com sucesso.")

        # 5️⃣ Atualizar também a tabela individual de números (Script 3)
        registros_individuais = [
            {
                "data_referencia": hoje,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"]),
            }
            for _, row in df_scores.iterrows()
        ]

        supabase.table("estatisticas_numeros") \
            .delete() \
            .eq("data_referencia", hoje) \
            .execute()

        supabase.table("estatisticas_numbers") \
            .insert(registros_individuais) \
            .execute()

        print(f"✅ {len(registros_individuais)} registros individuais atualizados.")

    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")

if __name__ == "__main__":
    main()
