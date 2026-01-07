import os
import sys
import json
import random
from datetime import date
from pathlib import Path

# Configuração de Caminho para imports internos
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    analisar_ciclo,
    obter_estatisticas_com_score
)

def calcular_metricas_base(dezenas):
    """Calcula métricas rápidas para validação de um palpite."""
    pares = sum(1 for n in dezenas if n % 2 == 0)
    return {
        "soma": sum(dezenas),
        "pares": pares,
        "impares": 15 - pares
    }

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()
    
    print(f"🚀 [2026] Iniciando Processamento Consolidado: {hoje}")

    try:
        # 1️⃣ CÁLCULO DE ESTATÍSTICAS REAIS
        print("📊 Calculando médias, ciclos e scores...")
        analise_medias = calcular_medias_recentes()
        faltantes_ciclo = sorted([int(n) for n in analisar_ciclo()])
        df_scores = obter_estatisticas_com_score()

        if df_scores is None or df_scores.empty:
            print("⚠️ Falha ao obter dados. Abortando.")
            return

        # 2️⃣ PREPARAÇÃO: estatisticas_diarias_v2
        quentes = [int(n) for n in df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()]
        frios = [int(n) for n in df_scores.sort_values("score").head(5)["numero"].tolist()]
        atrasados_ranking = [int(n) for n in df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()]

        payload_diario = {
            "data_referencia": hoje,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": faltantes_ciclo,
            "media_soma": float(round(analise_medias.get("soma_media", 0), 2)),
            "media_pares": float(round(analise_medias.get("pares_media", 0), 2)),
            "media_impares": float(round(analise_medias.get("impares_media", 0), 2)),
            "media_primos": float(round(analise_medias.get("media_primos", 0), 2)),
            "sequencias_comuns": [3, 4],
            "atrasados_ranking": atrasados_ranking
        }

        # 3️⃣ PREPARAÇÃO: estatisticas_numeros
        registros_numeros = [
            {"data_referencia": hoje, "numero": int(row["numero"]), "frequencia": int(row["frequencia"]), 
             "atraso": int(row["atraso"]), "score": float(row["score"])}
            for _, row in df_scores.iterrows()
        ]

        # 4️⃣ GERAÇÃO DE PALPITES (Fixo + Estatísticos)
        print("🎲 Gerando palpites estratégicos (Ciclo + Ranking)...")
        registros_palpites = []
        meta_pares = int(round(analise_medias.get("pares_media", 7)))
        
        # Base de Elite: Top 18 Scores
        base_elite = [int(n) for n in df_scores.sort_values("score", ascending=False).head(18)["numero"].tolist()]

        # --- A) Palpite Fixo (Índice 0): O Mestre do Ciclo ---
        # Prioriza fechar o ciclo + completar com os maiores scores
        fixo_numeros = sorted(list(set(faltantes_ciclo + base_elite))[:15])
        m_fixo = calcular_metricas_base(fixo_numeros)
        registros_palpites.append({
            "data_referencia": hoje, "indice_palpite": 0, "numeros": fixo_numeros,
            "soma_total": m_fixo["soma"], "pares": m_fixo["pares"], "impares": m_fixo["impares"],
            "tipo": "fixo", "origem": "sistema", "qtd_sequencias": 3,
            "metricas": {"score": 0.98, "metodo": "ciclo_fechamento_mestre"},
            "filtros_aplicados": ["ciclo_total", "top_scores"]
        })

        # --- B) Palpites Estatísticos (Índices 1 a 10): Dinâmicos ---
        for i in range(1, 11):
            tentativas = 0
            while tentativas < 100:
                # Estratégia: Incluir 50% dos faltantes do ciclo aleatoriamente para diversificar
                amostra_ciclo = random.sample(faltantes_ciclo, min(len(faltantes_ciclo), 3))
                # Completa com o restante da elite
                restante = random.sample([n for n in base_elite if n not in amostra_ciclo], 15 - len(amostra_ciclo))
                combinacao = sorted(amostra_ciclo + restante)
                
                m = calcular_metricas_base(combinacao)
                
                # REGRAS 2026: Soma entre 145 e 240 + Equilíbrio de Pares
                if (145 <= m["soma"] <= 240) and abs(m["pares"] - meta_pares) <= 1:
                    registros_palpites.append({
                        "data_referencia": hoje, "indice_palpite": i, "numeros": combinacao,
                        "soma_total": m["soma"], "pares": m["pares"], "impares": m["impares"],
                        "tipo": "estatistico", "origem": "sistema", "qtd_sequencias": 3,
                        "metricas": {"score": 0.88, "metodo": "compensacao_ciclo_soma"},
                        "filtros_aplicados": ["soma_dinamica", "validacao_ciclo"]
                    })
                    break
                tentativas += 1

        # 5️⃣ SALVAMENTO
        print("💾 Atualizando Supabase...")
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        supabase.table("estatisticas_numeros").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_numeros").insert(registros_numeros).execute()

        supabase.table("palpites_validos").delete().eq("data_referencia", hoje).execute()
        supabase.table("palpites_validos").insert(registros_palpites).execute()

        print(f"✅ Processamento 2026 concluído com sucesso!")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")

if __name__ == "__main__":
    main()
