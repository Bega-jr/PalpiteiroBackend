import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


TABELAS_CRITICAS = {

    "palpites_validos": [

        "concurso_referencia",
        "indice_palpite",
        "numeros",
        "score",
        "score_montecarlo",
        "score_estrutural",
        "cluster_id"
    ],

    "telemetria_geracao": [

        "concurso_referencia",
        "versao_gerador",
        "score_medio",
        "qtd_candidatos"
    ],

    "feature_store_jogos": [

        "concurso_referencia",
        "hash_jogo",
        "numeros",
        "cluster_id",
        "score"
    ],

    "memoria_clusters": [

        "cluster_id",
        "score_medio"
    ],

    "meta_learning_execucoes": [

        "concurso_referencia",
        "score_medio",
        "qtd_candidatos"
    ],

    "memoria_feedback_loop": [

        "concurso_referencia"
    ],

    "memoria_cenarios": [

        "hash_estrutura",
        "score_medio_real"
    ]
}


def auditar_tabela(
    supabase,
    tabela,
    colunas_criticas
):

    print("\n==================================================")
    print(f"📊 AUDITORIA: {tabela}")
    print("==================================================")

    try:

        rows = (
            supabase
            .table(tabela)
            .select("*")
            .limit(3)
            .execute()
            .data
        )

    except Exception as e:

        print(f"❌ ERRO acesso tabela: {e}")
        return False

    if not rows:

        print("⚠️ Tabela vazia")
        return False

    print(f"✅ Registros encontrados: {len(rows)}")

    exemplo = rows[0]

    faltando = []

    for coluna in colunas_criticas:

        if coluna not in exemplo:

            faltando.append(coluna)

    if faltando:

        print(
            f"❌ Colunas ausentes: {faltando}"
        )

        return False

    print("✅ Estrutura OK")

    return True


def main():

    print("\n🧠 v1.0-auditoria-estrutural")
    print("==================================================")

    supabase = get_supabase()

    sucesso = 0
    falhas = 0

    for tabela, colunas in TABELAS_CRITICAS.items():

        ok = auditar_tabela(

            supabase,
            tabela,
            colunas
        )

        if ok:
            sucesso += 1
        else:
            falhas += 1

    print("\n==================================================")
    print("📊 RESUMO FINAL")
    print("==================================================")

    print(f"✅ Tabelas OK: {sucesso}")
    print(f"❌ Tabelas com falha: {falhas}")

    if falhas == 0:

        print("🚀 Estrutura íntegra")

    else:

        print("⚠️ Existem inconsistências estruturais")


if __name__ == "__main__":
    main()
