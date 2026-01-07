import os
import sys
import json
from datetime import date
from pathlib import Path

# Configuração de Caminho para imports internos
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Imports dos seus serviços
from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    analisar_ciclo,
    obter_estatisticas_com_score
)

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()
    
    print(f"🚀 [2026] Iniciando Processamento de Estatísticas: {hoje}")

    try:
        # 1️⃣ CÁLCULO DE ESTATÍSTICAS REAIS (Baseado na lotofacil_concursos)
        print("📊 Calculando médias, ciclos e scores...")
        analise_medias = calcular_medias_recentes()
        faltantes_ciclo = analisar_ciclo()
        df_scores = obter_estatisticas_com_score()

        if df_scores is None or df_scores.empty:
            print("⚠️ Falha ao obter dados para cálculo de estatísticas. Abortando.")
            return

        # 2️⃣ PREPARAÇÃO: estatisticas_diarias_v2 (Resumo/Cards)
        quentes = [int(n) for n in df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()]
        frios = [int(n) for n in df_scores.sort_values("score").head(5)["numero"].tolist()]
        atrasados_ranking = [int(n) for n in df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()]

        payload_diario = {
            "data_referencia": hoje,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": sorted(faltantes_ciclo),
            "media_soma": float(round(analise_medias.get("soma_media", 0), 2)),
            "media_pares": float(round(analise_medias.get("pares_media", 0), 2)),
            "media_impares": float(round(analise_medias.get("impares_media", 0), 2)),
            "media_primos": float(round(analise_medias.get("primos_media", 0), 2)),
            "sequencias_comuns": [3, 4],
            "atrasados_ranking": atrasados_ranking
        }

        # 3️⃣ PREPARAÇÃO: estatisticas_numeros (Gráficos por número)
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

        # 4️⃣ PREPARAÇÃO: palpites_validos (Gerador)
        # Exemplo usando os números com melhor score (quentes) + alguns aleatórios da base
        base_palpite = sorted(quentes + [int(n) for n in df_scores.sort_values("score", ascending=False).iloc[5:15]["numero"].tolist()])
        
        registros_palpites = []
        for i in range(1, 11): # Gera 10 palpites
            registros_palpites.append({
                "data_referencia": hoje,
                "indice_palpite": i,
                "numeros": base_palpite,
                "tipo": "estatistico",
                "origem": "sistema"
            })

        # 5️⃣ SALVAMENTO NO SUPABASE (Limpa o dia e insere novos)
        print("💾 Salvando tudo no banco de dados...")
        
        # Tabela: estatisticas_diarias_v2
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        # Tabela: estatisticas_numeros
        supabase.table("estatisticas_numeros").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_numeros").insert(registros_numeros).execute()

        # Tabela: palpites_validos
        supabase.table("palpites_validos").delete().eq("data_referencia", hoje).execute()
        supabase.table("palpites_validos").insert(registros_palpites).execute()

        print(f"✅ Sucesso total! Dados de {hoje} consolidados.")

    except Exception as e:
        print(f"❌ Erro crítico no processamento: {e}")

if __name__ == "__main__":
    main()
