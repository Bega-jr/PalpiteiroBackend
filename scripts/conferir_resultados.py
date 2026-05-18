import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
# IMPORTAÇÃO DO SEU NOVO SERVICE
from app.services.meta_learning_service import atualizar_meta_learning

VERSAO = "v17.2-conferencia-meta-learning-ready"

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

def montar_bloco_auditoria(concurso, resultado, ranking, concurso_atual=None):
    linhas = []
    linhas.append("=" * 50)
    linhas.append(f"📊 Concurso {concurso} — Auditoria de Performance")
    linhas.append("")
    linhas.append(f"🎯 Resultado oficial: {sorted(resultado)}")
    linhas.append("")
    linhas.append("📌 Resultado IA:")
    linhas.append("")
    for r in ranking:
        linhas.append(f"🔹 Palpite #{r['idx']} → {r['acertos']} acertos")
    if concurso_atual:
        linhas.append("")
        linhas.append(f"⏳ Concurso {concurso_atual} ainda sem resultado oficial")
    linhas.append("=" * 50)
    return "\n".join(linhas)

# ======================================================
# AUDITORIA HISTÓRICA
# ======================================================
def exibir_ultima_auditoria(supabase, mapa, concurso_atual):
    ultimo = supabase.table("palpites_validos").select(
        "concurso_referencia,indice_palpite,acertos"
    ).eq("conferido", True).order("concurso_referencia", desc=True).limit(50).execute().data

    if not ultimo:
        print(f"⏳ Concurso {concurso_atual} ainda sem resultado oficial")
        return

    ultimo_concurso = int(ultimo[0]["concurso_referencia"])
    registros = [x for x in ultimo if int(x["concurso_referencia"]) == ultimo_concurso]

    if ultimo_concurso not in mapa:
        print(f"⏳ Concurso {concurso_atual} still sem resultado oficial")
        return

    resultado = mapa[ultimo_concurso]
    ranking = []

    for r in registros:
        ranking.append({
            "idx": r["indice_palpite"],
            "acertos": r["acertos"]
        })

    ranking.sort(key=lambda x: x["acertos"], reverse=True)
    print(montar_bloco_auditoria(ultimo_concurso, resultado, ranking, concurso_atual))

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    print(f"🏁 [{VERSAO}] Conferência + Bootstrap")

    oficiais = supabase.table("lotofacil_concursos").select(
        "concurso,dezenas"
    ).order("concurso", desc=True).limit(100).execute().data

    mapa = {int(r["concurso"]): set(parse_numeros(r["dezenas"])) for r in oficiais}

    pendentes = supabase.table("palpites_validos").select("*").eq("conferido", False).execute().data
    print(f"📌 {len(pendentes)} palpites pendentes")

    processados = 0
    por_concurso = {}

    for p in pendentes:
        concurso = int(p["concurso_referencia"])
        if concurso not in por_concurso:
            por_concurso[concurso] = []
        por_concurso[concurso].append(p)

    for concurso, lista in por_concurso.items():
        if concurso not in mapa:
            exibir_ultima_auditoria(supabase, mapa, concurso)
            continue

        resultado = mapa[concurso]
        ranking = []
        lista_acertos = [] # Lista para acumular os acertos deste concurso específico

        for p in lista:
            numeros = parse_numeros(p["numeros"])
            acertos = len(set(numeros) & resultado)
            lista_acertos.append(acertos)

            ranking.append({
                "id": p["id"],
                "idx": p["indice_palpite"],
                "acertos": acertos
            })

            supabase.table("palpites_validos").update({
                "acertos": acertos,
                "processado": True,
                "conferido": True
            }).eq("id", p["id"]).execute()

            processados += 1

        # ======================================================
        # INTEGRACAO META LEARNING
        # ======================================================
        if lista_acertos:
            media_concurso = sum(lista_acertos) / len(lista_acertos)
            print(f"\n🧠 [Meta-Learning] Disparando retroalimentação para Concurso {concurso} | Média: {media_concurso:.2f}")
            try:
                # Aplica as regras (< 9 ou >= 11) e salva a nova linha na memória_meta_learning
                atualizar_meta_learning(media_concurso)
            except Exception as e:
                print(f"⚠️ Erro ao atualizar pesos adaptativos: {e}")

        ranking.sort(key=lambda x: x["acertos"], reverse=True)
        print(montar_bloco_auditoria(concurso, resultado, ranking))

    print(
        f"\n"
        f"====================\n"
        f"✅ Processo concluído\n"
        f"📊 {processados} palpites processados"
    )

if __name__ == "__main__":
    main()

