import traceback
from datetime import datetime

from app.services.supabase_service import (
    get_supabase
)

# =========================================================
# AUDITORIA
# =========================================================
from scripts.auditar_padroes import (
    identificar_padroes_elite
)

# =========================================================
# FEEDBACK ANALYTICS
# =========================================================
try:

    from scripts.processamento_feedback_analytics import (
        processar_feedback_analytics
    )

except:

    processar_feedback_analytics = None


# =========================================================
# META LEARNING
# =========================================================
try:

    from app.services.meta_learning_service import (
        atualizar_pesos_dinamicos
    )

except:

    atualizar_pesos_dinamicos = None


# =========================================================
# CLUSTERS
# =========================================================
try:

    from app.services.clusterizacao_service import (
        recalibrar_clusters
    )

except:

    recalibrar_clusters = None


# =========================================================
# TELEMETRIA
# =========================================================
try:

    from app.services.persistencia_analytics_service import (
        consolidar_telemetria
    )

except:

    consolidar_telemetria = None


# =========================================================
# COLAPSO ESTRATÉGICO
# =========================================================
try:

    from app.services.colapso_service import (
        detectar_colapso_estrategico
    )

except:

    detectar_colapso_estrategico = None


# =========================================================
# ELITE SERVICE
# =========================================================
try:

    from app.services.elite_service import (
        atualizar_ranking_elite
    )

except:

    atualizar_ranking_elite = None


VERSAO = "v20.0-hub-analytics"


# =========================================================
# HELPERS
# =========================================================
def executar_etapa(
    nome,
    func
):

    print(f"\n🚀 {nome}")

    if func is None:

        print(
            f"⚠️ Etapa não disponível: {nome}"
        )

        return False

    try:

        inicio = datetime.now()

        func()

        fim = datetime.now()

        delta = (
            fim - inicio
        ).total_seconds()

        print(
            f"✅ {nome} concluído "
            f"em {delta:.2f}s"
        )

        return True

    except Exception as e:

        print(
            f"❌ Erro em {nome}: {e}"
        )

        traceback.print_exc()

        return False


# =========================================================
# LOG EXECUÇÃO
# =========================================================
def salvar_execucao_hub(
    supabase,
    resultados
):

    try:

        payload = {

            "versao": VERSAO,

            "data_execucao": datetime.utcnow().isoformat(),

            "etapas_sucesso": sum(
                1 for x in resultados
                if x["sucesso"]
            ),

            "etapas_falha": sum(
                1 for x in resultados
                if not x["sucesso"]
            ),

            "resultado": resultados
        }

        supabase.table(
            "hub_analytics_execucoes"
        ).insert(payload).execute()

    except Exception as e:

        print(
            f"⚠️ Falha ao salvar log HUB: {e}"
        )


# =========================================================
# MAIN
# =========================================================
def main():

    print("\n")
    print("=" * 60)
    print(f"🧠 HUB ANALYTICS {VERSAO}")
    print("=" * 60)

    supabase = get_supabase()

    resultados = []

    # =====================================================
    # FEEDBACK
    # =====================================================
    ok = executar_etapa(

        "PROCESSAMENTO FEEDBACK",

        processar_feedback_analytics
    )

    resultados.append({

        "etapa": "feedback",

        "sucesso": ok
    })


    # =====================================================
    # AUDITORIA ELITE
    # =====================================================
    ok = executar_etapa(

        "AUDITORIA PADRÕES ELITE",

        identificar_padroes_elite
    )

    resultados.append({

        "etapa": "elite",

        "sucesso": ok
    })


    # =====================================================
    # CLUSTERS
    # =====================================================
    ok = executar_etapa(

        "RECALIBRAGEM CLUSTERS",

        recalibrar_clusters
    )

    resultados.append({

        "etapa": "clusters",

        "sucesso": ok
    })


    # =====================================================
    # META LEARNING
    # =====================================================
    ok = executar_etapa(

        "META LEARNING DINÂMICO",

        atualizar_pesos_dinamicos
    )

    resultados.append({

        "etapa": "meta_learning",

        "sucesso": ok
    })


    # =====================================================
    # TELEMETRIA
    # =====================================================
    ok = executar_etapa(

        "CONSOLIDAÇÃO TELEMETRIA",

        consolidar_telemetria
    )

    resultados.append({

        "etapa": "telemetria",

        "sucesso": ok
    })


    # =====================================================
    # COLAPSO ESTRATÉGICO
    # =====================================================
    ok = executar_etapa(

        "ANÁLISE COLAPSO",

        detectar_colapso_estrategico
    )

    resultados.append({

        "etapa": "colapso",

        "sucesso": ok
    })


    # =====================================================
    # RANKING ELITE
    # =====================================================
    ok = executar_etapa(

        "ATUALIZAÇÃO ELITE",

        atualizar_ranking_elite
    )

    resultados.append({

        "etapa": "ranking_elite",

        "sucesso": ok
    })


    # =====================================================
    # LOG FINAL
    # =====================================================
    salvar_execucao_hub(

        supabase,

        resultados
    )


    # =====================================================
    # RESUMO
    # =====================================================
    total_ok = sum(
        1 for x in resultados
        if x["sucesso"]
    )

    total_fail = sum(
        1 for x in resultados
        if not x["sucesso"]
    )

    print("\n")
    print("=" * 60)

    print(
        f"✅ HUB FINALIZADO | "
        f"Sucesso: {total_ok} | "
        f"Falhas: {total_fail}"
    )

    print("=" * 60)
    print("\n")


# =========================================================
# START
# =========================================================
if __name__ == "__main__":

    main()
