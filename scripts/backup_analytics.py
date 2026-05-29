import sys
import json
import pandas as pd

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import (
    get_supabase
)


TABELAS_BACKUP = [

    "palpites_validos",

    "telemetria_geracao",

    "snapshot_telemetria",

    "feature_store_jogos",

    "memoria_clusters",

    "meta_learning_execucoes",

    "memoria_feedback_loop",

    "memoria_cenarios"
]


def garantir_pasta():

    pasta = BASE_DIR / "backups"

    pasta.mkdir(
        exist_ok=True
    )

    return pasta


def exportar_tabela(
    supabase,
    tabela,
    pasta
):

    print("\n==================================================")
    print(f"💾 BACKUP: {tabela}")
    print("==================================================")

    try:

        rows = (

            supabase
            .table(tabela)
            .select("*")
            .limit(5000)
            .execute()
            .data
        )

    except Exception as e:

        print(f"❌ Erro leitura: {e}")
        return False

    if not rows:

        print("⚠️ Sem registros")
        return False

    df = pd.DataFrame(rows)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    arquivo_csv = (
        pasta /
        f"{tabela}_{timestamp}.csv"
    )

    arquivo_json = (
        pasta /
        f"{tabela}_{timestamp}.json"
    )

    try:

        df.to_csv(
            arquivo_csv,
            index=False
        )

        with open(
            arquivo_json,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                rows,
                f,

                ensure_ascii=False,

                indent=2,

                default=str
            )

        print(
            f"✅ Backup salvo:"
        )

        print(arquivo_csv.name)
        print(arquivo_json.name)

        return True

    except Exception as e:

        print(
            f"❌ Erro exportação: {e}"
        )

        return False


def limpar_backups_antigos(
    pasta,
    manter=15
):

    arquivos = sorted(

        pasta.glob("*"),

        key=lambda x: x.stat().st_mtime,

        reverse=True
    )

    if len(arquivos) <= manter:
        return

    remover = arquivos[manter:]

    for arq in remover:

        try:

            arq.unlink()

        except:
            pass


def main():

    print("\n🧠 v1.0-backup-analytics")
    print("==================================================")

    supabase = get_supabase()

    pasta = garantir_pasta()

    sucesso = 0
    falhas = 0

    for tabela in TABELAS_BACKUP:

        ok = exportar_tabela(

            supabase,
            tabela,
            pasta
        )

        if ok:
            sucesso += 1
        else:
            falhas += 1

    limpar_backups_antigos(
        pasta
    )

    print("\n==================================================")
    print("📊 RESUMO FINAL")
    print("==================================================")

    print(f"✅ Backups OK: {sucesso}")
    print(f"❌ Falhas: {falhas}")

    print(
        f"📂 Pasta: {pasta}"
    )


if __name__ == "__main__":
    main()
