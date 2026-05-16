import sys
import json

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "v14.5-conferencia-smart-audit"


# ======================================================
# AUX
# ======================================================
def parse_numeros(valor):

    if not valor:
        return []

    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):

        try:
            return [int(x) for x in json.loads(valor)]
        except:
            return []

    return []


# ======================================================
# AUDITORIA HISTÓRICA
# ======================================================
def exibir_ultima_auditoria(supabase, mapa, concurso_atual):

    ultimo = supabase.table(
        "palpites_validos"
    ).select(
        "concurso_referencia,indice_palpite,acertos"
    ).eq(
        "conferido",
        True
    ).order(
        "concurso_referencia",
        desc=True
    ).limit(50).execute().data

    if not ultimo:
        print(f"⏳ Concurso {concurso_atual} ainda sem resultado oficial")
        return

    ultimo_concurso = int(
        ultimo[0]["concurso_referencia"]
    )

    registros = [
        x for x in ultimo
        if int(x["concurso_referencia"]) == ultimo_concurso
    ]

    if ultimo_concurso not in mapa:
        print(f"⏳ Concurso {concurso_atual} ainda sem resultado oficial")
        return

    resultado = mapa[ultimo_concurso]

    print("\n" + "=" * 50)
    print(
        f"📊 Concurso {ultimo_concurso} — Auditoria de Performance\n"
    )

    print("🎯 Resultado oficial:")
    print(sorted(resultado))

    print("\n📌 Resultado IA:\n")

    ranking = []

    for r in registros:

        ranking.append({
            "idx": r["indice_palpite"],
            "acertos": r["acertos"]
        })

    ranking.sort(
        key=lambda x: x["acertos"],
        reverse=True
    )

    for r in ranking:

        print(
            f"🔹 Palpite #{r['idx']} → {r['acertos']} acertos"
        )

    print(
        f"\n⏳ Concurso {concurso_atual} ainda sem resultado oficial"
    )

    print("=" * 50)


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        f"🏁 [{VERSAO}] Conferência + Bootstrap"
    )

    oficiais = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso",
        desc=True
    ).limit(100).execute().data

    mapa = {
        int(r["concurso"]): set(
            parse_numeros(
                r["dezenas"]
            )
        )
        for r in oficiais
    }

    pendentes = supabase.table(
        "palpites_validos"
    ).select("*") \
     .eq(
         "conferido",
         False
     ) \
     .execute().data

    print(
        f"📌 {len(pendentes)} palpites pendentes"
    )

    processados = 0

    # ======================================================
    # AGRUPA POR CONCURSO
    # ======================================================
    por_concurso = {}

    for p in pendentes:

        concurso = int(
            p["concurso_referencia"]
        )

        if concurso not in por_concurso:
            por_concurso[concurso] = []

        por_concurso[concurso].append(
            p
        )

    # ======================================================
    # PROCESSAMENTO
    # ======================================================
    for concurso, lista in por_concurso.items():

        # Ainda não saiu resultado
        if concurso not in mapa:

            exibir_ultima_auditoria(
                supabase,
                mapa,
                concurso
            )

            continue

        resultado = mapa[concurso]

        print("\n" + "=" * 50)
        print(
            f"📊 Concurso {concurso} — Auditoria de Performance\n"
        )

        print("🎯 Resultado oficial:")
        print(sorted(resultado))

        print("\n📌 Resultado IA:\n")

        ranking = []

        for p in lista:

            numeros = parse_numeros(
                p["numeros"]
            )

            acertos = len(
                set(numeros) &
                resultado
            )

            ranking.append({
                "id": p["id"],
                "idx": p["indice_palpite"],
                "acertos": acertos
            })

            # Atualiza banco
            supabase.table(
                "palpites_validos"
            ).update({

                "acertos": acertos,
                "processado": True,
                "conferido": True

            }).eq(
                "id",
                p["id"]
            ).execute()

            processados += 1

        ranking.sort(
            key=lambda x: x["acertos"],
            reverse=True
        )

        for r in ranking:

            print(
                f"🔹 Palpite #{r['idx']} → {r['acertos']} acertos"
            )

        print("=" * 50)

    print(
        f"\n====================\n"
        f"✅ Processo concluído: {processados} palpites processados"
    )


if __name__ == "__main__":
    main()
