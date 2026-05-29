import sys
import importlib
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))


MODULOS_CRITICOS = [

    "app.services.feature_store_service",

    "app.services.clusterizacao_service",

    "app.services.persistencia_analytics_service",

    "app.services.recompensa_evolutiva_service",

    "app.services.diversidade_service",

    "app.services.meta_learning_service",

    "app.services.montecarlo_service",

    "app.services.selecao_genetica_service",

    "app.services.motores_ensemble_service"
]


FUNCOES_CRITICAS = {

    "app.services.persistencia_analytics_service": [

        "salvar_feature_store_jogo",

        "salvar_cluster_jogo",

        "persistir_telemetria"
    ],

    "app.services.feature_store_service": [

        "gerar_features_jogo"
    ],

    "app.services.clusterizacao_service": [

        "identificar_cluster_jogo"
    ],

    "app.services.recompensa_evolutiva_service": [

        "calcular_recompensa_evolutiva"
    ],

    "app.services.montecarlo_service": [

        "simular_probabilidade_jogo"
    ],

    "app.services.selecao_genetica_service": [

        "selecionar_populacao_final"
    ]
}


def validar_modulo(nome):

    print("\n==================================================")
    print(f"📦 Validando módulo:")
    print(nome)
    print("==================================================")

    try:

        modulo = importlib.import_module(
            nome
        )

        print("✅ Import OK")

        return modulo

    except Exception as e:

        print(f"❌ ERRO IMPORT: {e}")

        return None


def validar_funcoes(
    modulo,
    nome_modulo
):

    funcoes = FUNCOES_CRITICAS.get(
        nome_modulo,
        []
    )

    if not funcoes:
        return True

    ok = True

    for func in funcoes:

        if hasattr(modulo, func):

            print(f"✅ Função OK: {func}")

        else:

            print(f"❌ Função ausente: {func}")

            ok = False

    return ok


def main():

    print("\n🧠 v1.0-validacao-integridade")
    print("==================================================")

    sucesso = 0
    falhas = 0

    for nome in MODULOS_CRITICOS:

        modulo = validar_modulo(nome)

        if modulo is None:

            falhas += 1
            continue

        ok = validar_funcoes(
            modulo,
            nome
        )

        if ok:
            sucesso += 1
        else:
            falhas += 1

    print("\n==================================================")
    print("📊 RESUMO FINAL")
    print("==================================================")

    print(f"✅ Módulos íntegros: {sucesso}")
    print(f"❌ Falhas encontradas: {falhas}")

    if falhas == 0:

        print("🚀 Pipeline íntegro")

    else:

        print("⚠️ Existem inconsistências")


if __name__ == "__main__":
    main()
