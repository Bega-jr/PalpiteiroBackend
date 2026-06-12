import sys
import json  # 💡 CORREÇÃO: Adicionado o import do json no topo para o Supabase aceitar
import traceback
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# =========================================================
# IMPORTS BLINDADOS (Tratamento limpo de caminhos)
# =========================================================
try:
    from scripts.auditar_padroes import identificar_padroes_elite
except ImportError:
    identificar_padroes_elite = None

try:
    from scripts.processamento_feedback_meta import avaliar_desempenho_concurso as processar_feedback_analytics
except ImportError:
    processar_feedback_analytics = None

try:
    from app.services.meta_learning_service import atualizar_pesos_dinamicos
except ImportError:
    atualizar_pesos_dinamicos = None

try:
    from app.services.clusterizacao_service import recalibrar_clusters
except ImportError:
    recalibrar_clusters = None

try:
    from app.services.persistencia_analytics_service import consolidar_telemetria
except ImportError:
    consolidar_telemetria = None

try:
    from app.services.colapso_service import detectar_colapso_estrategico
except ImportError:
    detectar_colapso_estrategico = None

try:
    from app.services.elite_service import atualizar_ranking_elite
except ImportError:
    atualizar_ranking_elite = None

VERSAO = "v20.0-hub-analytics"

# =========================================================
# HELPERS
# =========================================================
def executar_etapa(nome, func):
    print(f"\n🚀 {nome}")

    if func is None:
        print(f"⚠️ Módulo não implementado ou erro severo de sintaxe no arquivo: {nome}")
        return False

    try:
        inicio = datetime.now()
        func() 
        fim = datetime.now()
        delta = (fim - inicio).total_seconds()
        print(f"✅ {nome} concluído em {delta:.2f}s")
        return True

    except Exception as e:
        print(f"❌ Erro de execução em {nome}: {e}")
        traceback.print_exc()
        return False

# =========================================================
# LOG EXECUÇÃO (Corrigido com escopo global do json)
# =========================================================
def salvar_execucao_hub(supabase, resultados):
    try:
        payload = {
            "versao": VERSAO,
            "data_execucao": datetime.now().isoformat(),
            "etapas_sucesso": sum(1 for x in resultados if x["sucesso"]),
            "etapas_falha": sum(1 for x in resultados if not x["sucesso"]),
            "resultado": json.dumps(resultados)  # Agora funciona perfeitamente
        }
        supabase.table("hub_analytics_execucoes").insert(payload).execute()
        print("📡 Execução do HUB registrada em hub_analytics_execucoes.")
    except Exception as e:
        print(f"⚠️ Falha ao persistir telemetria do HUB no Supabase: {e}")

# =========================================================
# MAIN
# =========================================================
def main():
    print("\n" + "=" * 60)
    print(f"🧠 HUB ANALYTICS {VERSAO}")
    print("=" * 60)

    supabase = get_supabase()
    resultados = []

    etapas = [
        ("PROCESSAMENTO FEEDBACK", processar_feedback_analytics, "feedback"),
        ("AUDITORIA PADRÕES ELITE", identificar_padroes_elite, "elite"),
        ("RECALIBRAGEM CLUSTERS", recalibrar_clusters, "clusters"),
        ("META LEARNING DINÂMICO", atualizar_pesos_dinamicos, "meta_learning"),
        ("CONSOLIDAÇÃO TELEMETRIA", consolidar_telemetria, "telemetria"),
        ("ANÁLISE COLAPSO", detectar_colapso_estrategico, "colapso"),
        ("ATUALIZAÇÃO ELITE", atualizar_ranking_elite, "ranking_elite")
    ]

    for nome, func, chave in etapas:
        ok = executar_etapa(nome, func)
        resultados.append({"etapa": chave, "sucesso": ok})

    salvar_execucao_hub(supabase, resultados)

    total_ok = sum(1 for x in resultados if x["sucesso"])
    total_fail = sum(1 for x in resultados if not x["sucesso"])

    print("\n" + "=" * 60)
    print(f"✅ HUB FINALIZADO | Sucesso: {total_ok} | Falhas: {total_fail}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
