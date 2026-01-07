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
        faltantes_ciclo = analisar_ciclo()
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
            "numeros_atrasados": sorted(faltantes_ciclo),
            "media_soma": float(round(analise_medias.get("soma_media", 0), 2)),
            "media_pares": float(round(analise_medias.get("pares_media", 0), 2)),
            "media_impares": float(round(analise_medias.get("impares_media", 0), 2)),
            "media_primos": float(round(analise_medias.get("primos_media", 0), 2)),
            "sequencias_comuns": [3, 4],
            "atrasados_ranking": atrasados_ranking
        }

        # 3️⃣ PREPARAÇÃO: estatisticas_numeros (Gráficos)
        registros_numeros = [
            {"data_referencia": hoje, "numero": int(row["numero"]), "frequencia": int(row["frequencia"]), 
             "atraso": int(row["atraso"]), "score": float(row["score"])}
            for _, row in df_scores.iterrows()
        ]

        # 4️⃣ GERAÇÃO DE PALPITES (Fixo + Estatísticos)
        print("🎲 Gerando palpites inteligentes...")
        registros_palpites = []
        
        # Meta de pares baseada na média real de hoje
        meta_pares = int(round(analise_medias.get("pares_media", 7)))
        # Base de elite: 18 números com maiores scores para variar os palpites
        base_elite = [int(n) for n in df_scores.sort_values("score", ascending=False).head(18)["numero"].tolist()]

        # --- A) Geração do Palpite Fixo (Índice 0) ---
        # O Fixo são puramente os 15 melhores scores, sem sorteio
        fixo_numeros = sorted(base_elite[:15])
        m_fixo = calcular_metricas_base(fixo_numeros)
        registros_palpites.append({
            "data_referencia": hoje, "indice_palpite": 0, "numeros": fixo_numeros,
            "soma_total": m_fixo["soma"], "pares": m_fixo["pares"], "impares": m_fixo["impares"],
            "tipo": "fixo", "origem": "sistema", "qtd_sequencias": 3,
            "metricas": {"score": 0.95, "metodo": "top_scores_puros"}
        })

        # --- B) Geração dos Estatísticos (Índices 1 a 10) ---
        for i in range(1, 11):
            tentativas = 0
            while tentativas < 50:
                # Sorteia 15 números dentro do grupo de 18 elite
                combinacao = sorted(random.sample(base_elite, 15))
                m = calcular_metricas_base(combinacao)
                
                # Validação: deve estar próximo à média de pares calculada
                if abs(m["pares"] - meta_pares) <= 1:
                    registros_palpites.append({
                        "data_referencia": hoje, "indice_palpite": i, "numeros": combinacao,
                        "soma_total": m["soma"], "pares": m["pares"], "impares": m["impares"],
                        "tipo": "estatistico", "origem": "sistema", "qtd_sequencias": 3,
                        "metricas": {"score": 0.85, "metodo": "elite_random_weighted"}
                    })
                    break
                tentativas += 1

        # 5️⃣ SALVAMENTO NO SUPABASE
        print("💾 Atualizando banco de dados...")
        
        # Limpeza e Inserção Consolidada
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_diarias_v2").insert(payload_diario).execute()
        
        supabase.table("estatisticas_numeros").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_numeros").insert(registros_numeros).execute()

        supabase.table("palpites_validos").delete().eq("data_referencia", hoje).execute()
        supabase.table("palpites_validos").insert(registros_palpites).execute()

        print(f"✅ Sucesso total! Dados e palpites de {hoje} consolidados.")

    except Exception as e:
        print(f"❌ Erro crítico no processamento: {e}")

if __name__ == "__main__":
    main()

