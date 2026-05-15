import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "v14.4-conferencia-definitiva"

PRIMOS = {2,3,5,7,11,13,17,19,23}


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
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(f"🏁 [{VERSAO}] Conferência + Bootstrap")

    oficiais = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso",
        desc=True
    ).limit(100).execute().data

    mapa = {
        int(r["concurso"]): set(parse_numeros(r["dezenas"]))
        for r in oficiais
    }

    pendentes = supabase.table(
        "palpites_validos"
    ).select("*") \
     .eq("conferido", False) \
     .execute().data

    print(f"📌 {len(pendentes)} palpites pendentes")

    processados = 0

    # ======================================================
    # AGRUPA POR CONCURSO (IMPORTANTE PARA AUDITORIA LIMPA)
    # ======================================================
    por_concurso = {}

    for p in pendentes:

        concurso = int(p["concurso_referencia"])

        if concurso not in por_concurso:
            por_concurso[concurso] = []

        por_concurso[concurso].append(p)

    # ======================================================
    # PROCESSAMENTO
    # ======================================================
    for concurso, lista in por_concurso.items():

        if concurso not in mapa:
            print(f"⏳ Concurso {concurso} ainda sem resultado oficial")
            continue

        resultado = mapa[concurso]

        # ===========================
        # HEADER DA AUDITORIA
        # ===========================
        print("\n" + "="*50)
        print(f"📊 Concurso {concurso} — Auditoria de Performance\n")
        print(f"🎯 Resultado oficial:")
        print(sorted(resultado))
        print("\n📌 Resultado IA:\n")

        ranking = []

        for p in lista:

            numeros = parse_numeros(p["numeros"])
            acertos = len(set(numeros) & resultado)

            ranking.append({
                "id": p["id"],
                "idx": p["indice_palpite"],
                "acertos": acertos,
                "numeros": numeros
            })

            # atualiza banco
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

        # ===========================
        # ORDENA POR PERFORMANCE
        # ===========================
        ranking.sort(key=lambda x: x["acertos"], reverse=True)

        # ===========================
        # OUTPUT FINAL (TELEGRAM/LOG)
        # ===========================
        for r in ranking:

            print(
                f"🔹 Palpite #{r['idx']} → {r['acertos']} acertos"
            )

        print("="*50)

    print(
        f"\n====================\n"
        f"✅ Processo concluído: {processados} palpites processados"
    )


if __name__ == "__main__":
    main()
