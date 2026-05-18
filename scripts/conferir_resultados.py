import sys
import json

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.meta_learning_service import atualizar_meta_learning


VERSAO = "v18.0-conferencia-contextual-learning"


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


def montar_bloco_auditoria(
    concurso,
    resultado,
    ranking,
    concurso_atual=None
):

    linhas = []

    linhas.append("=" * 50)

    linhas.append(
        f"📊 Concurso {concurso} — Auditoria de Performance"
    )

    linhas.append("")

    linhas.append(
        f"🎯 Resultado oficial: {sorted(resultado)}"
    )

    linhas.append("")

    linhas.append("📌 Resultado IA:")

    linhas.append("")

    for r in ranking:

        linhas.append(
            f"🔹 Palpite #{r['idx']} → {r['acertos']} acertos"
        )

    if concurso_atual:

        linhas.append("")

        linhas.append(
            f"⏳ Concurso {concurso_atual} ainda sem resultado oficial"
        )

    linhas.append("=" * 50)

    return "\n".join(linhas)


# ======================================================
# AUDITORIA HISTÓRICA
# ======================================================
def exibir_ultima_auditoria(
    supabase,
    mapa,
    concurso_atual
):

    ultimo = (

        supabase
        .table("palpites_validos")
        .select(
            "concurso_referencia,indice_palpite,acertos"
        )
        .eq("conferido", True)
        .order(
            "concurso_referencia",
            desc=True
        )
        .limit(50)
        .execute()
        .data
    )

    if not ultimo:

        print(
            f"⏳ Concurso {concurso_atual} ainda sem resultado oficial"
        )

        return

    ultimo_concurso = int(
        ultimo[0]["concurso_referencia"]
    )

    registros = [

        x for x in ultimo

        if int(x["concurso_referencia"]) == ultimo_concurso
    ]

    if ultimo_concurso not in mapa:

        print(
            f"⏳ Concurso {concurso_atual} ainda sem resultado oficial"
        )

        return

    resultado = mapa[ultimo_concurso]

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

    print(

        montar_bloco_auditoria(
            ultimo_concurso,
            resultado,
            ranking,
            concurso_atual
        )
    )


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        f"🏁 [{VERSAO}] Conferência + Meta Learning Contextual"
    )


    # ======================================================
    # RESULTADOS OFICIAIS
    # ======================================================
    oficiais = (

        supabase
        .table("lotofacil_concursos")
        .select(
            "concurso,dezenas"
        )
        .order(
            "concurso",
            desc=True
        )
        .limit(100)
        .execute()
        .data
    )


    mapa = {

        int(r["concurso"]): set(
            parse_numeros(r["dezenas"])
        )

        for r in oficiais
    }


    # ======================================================
    # PALPITES PENDENTES
    # ======================================================
    pendentes = (

        supabase
        .table("palpites_validos")
        .select("*")
        .eq("conferido", False)
        .execute()
        .data
    )

    print(
        f"📌 {len(pendentes)} palpites pendentes"
    )


    processados = 0

    por_concurso = {}


    for p in pendentes:

        concurso = int(
            p["concurso_referencia"]
        )

        if concurso not in por_concurso:

            por_concurso[concurso] = []

        por_concurso[concurso].append(p)


    # ======================================================
    # LOOP
    # ======================================================
    for concurso, lista in por_concurso.items():

        if concurso not in mapa:

            exibir_ultima_auditoria(
                supabase,
                mapa,
                concurso
            )

            continue


        resultado = mapa[concurso]

        ranking = []

        lista_acertos = []

        scores_estruturais = []


        # ======================================================
        # PROCESSA CADA PALPITE
        # ======================================================
        for p in lista:

            numeros = parse_numeros(
                p["numeros"]
            )

            acertos = len(
                set(numeros) & resultado
            )

            lista_acertos.append(
                acertos
            )


            if p.get("score"):

                try:

                    scores_estruturais.append(
                        float(p["score"])
                    )

                except:
                    pass


            ranking.append({

                "id": p["id"],

                "idx": p["indice_palpite"],

                "acertos": acertos
            })


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


        # ======================================================
        # CONTEXTO DE REGIME
        # ======================================================
        tipo_regime = "NEUTRO"

        try:

            reg = (

                supabase
                .table("memoria_regimes")
                .select("tipo_regime")
                .eq(
                    "concurso",
                    concurso - 1
                )
                .limit(1)
                .execute()
                .data
            )

            if reg:

                tipo_regime = reg[0]["tipo_regime"]

        except:
            pass


        # ======================================================
        # MÉTRICAS CONTEXTUAIS
        # ======================================================
        if lista_acertos:

            media_concurso = (
                sum(lista_acertos) / len(lista_acertos)
            )

            melhor_acerto = max(
                lista_acertos
            )

            pior_acerto = min(
                lista_acertos
            )

            dispersao = (
                melhor_acerto - pior_acerto
            )

            qtd_palpites = len(
                lista_acertos
            )

            score_estrutural = 0

            if scores_estruturais:

                score_estrutural = (

                    sum(scores_estruturais)
                    /
                    len(scores_estruturais)
                )


            print(
                "\n🧠 [Meta-Learning Contextual] Retroalimentando..."
            )


            try:

                atualizar_meta_learning(

                    media_acertos=media_concurso,

                    concurso_ref=concurso,

                    melhor_acerto=melhor_acerto,

                    pior_acerto=pior_acerto,

                    dispersao=dispersao,

                    qtd_palpites=qtd_palpites,

                    tipo_regime=tipo_regime,

                    score_estrutural=score_estrutural
                )

            except Exception as e:

                print(
                    f"⚠️ Erro ao atualizar meta-learning: {e}"
                )


        # ======================================================
        # AUDITORIA
        # ======================================================
        ranking.sort(
            key=lambda x: x["acertos"],
            reverse=True
        )

        print(

            montar_bloco_auditoria(
                concurso,
                resultado,
                ranking
            )
        )


    print(

        f"\n"
        f"====================\n"
        f"✅ Processo concluído\n"
        f"📊 {processados} palpites processados"
    )


if __name__ == "__main__":
    main()
