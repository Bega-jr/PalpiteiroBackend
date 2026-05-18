import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.meta_learning_service import atualizar_meta_learning
# Importação da função necessária para extrair a estrutura real sorteada
from scripts.processamento_diario_lotofacil import extrair_estrutura

VERSAO = "v18.1-conferencia-contextual-learning"


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
def exibir_ultima_auditoria(
    supabase,
    mapa,
    concurso_atual
):
    ultimo = (
        supabase
        .table("palpites_validos")
        .select("concurso_referencia,indice_palpite,acertos")
        .eq("conferido", True)
        .order("concurso_referencia", desc=True)
        .limit(50)
        .execute()
        .data
    )

    if not ultimo:
        print(f"⏳ Concurso {concurso_atual} ainda sem resultado oficial")
        return

    ultimo_concurso = int(ultimo[0]["concurso_referencia"])

    registros = [
        x for x in ultimo
        if int(x["concurso_referencia"]) == ultimo_concurso
    ]

    if ultimo_concurso not in mapa:
        print(f"⏳ Concurso {concurso_atual} ainda sem resultado oficial")
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

    print(f"🏁 [{VERSAO}] Conferência + Meta Learning Contextual")

    # ======================================================
    # RESULTADOS OFICIAIS
    # ======================================================
    oficiais = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(100)
        .execute()
        .data
    )

    mapa = {
        int(r["concurso"]): set(parse_numeros(r["dezenas"]))
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

    print(f"📌 {len(pendentes)} palpites pendentes")

    processados = 0
    por_concurso = {}

    for p in pendentes:
        concurso = int(p["concurso_referencia"])
        if concurso not in por_concurso:
            por_concurso[concurso] = []
        por_concurso[concurso].append(p)

    # ======================================================
    # LOOP PRINCIPAL POR CONCURSO
    # ======================================================
    for concurso, lista in por_concurso.items():
        if concurso not in mapa:
            exibir_ultima_auditoria(supabase, mapa, concurso)
            continue

        resultado = mapa[concurso]
        ranking = []
        lista_acertos = []
        scores_estruturais = []

        # ======================================================
        # PROCESSA CADA PALPITE INDIVIDUAL
        # ======================================================
        for p in lista:
            numeros = parse_numeros(p["numeros"])
            acertos = len(set(numeros) & resultado)
            lista_acertos.append(acertos)

            if p.get("score"):
                try:
                    scores_estruturais.append(float(p["score"]))
                except:
                    pass

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
        # CONTEXTO DE REGIME
        # ======================================================
        tipo_regime = "NEUTRO"
        try:
            reg = (
                supabase
                .table("memoria_regimes")
                .select("tipo_regime")
                .eq("concurso", concurso - 1)
                .limit(1)
                .execute()
                .data
            )
            if reg:
                tipo_regime = reg[0]["tipo_regime"]
        except:
            pass

        # ======================================================
        # MÉTRICAS CONTEXTUAIS E RETROALIMENTAÇÃO DA IA
        # ======================================================
        if lista_acertos:
            media_concurso = sum(lista_acertos) / len(lista_acertos)
            melhor_acerto = max(lista_acertos)
            pior_acerto = min(lista_acertos)
            dispersao = melhor_acerto - pior_acerto
            qtd_palpites = len(lista_acertos)
            score_estrutural = 0

            if scores_estruturais:
                score_estrutural = sum(scores_estruturais) / len(scores_estruturais)

            print("\n🧠 [Meta-Learning Contextual] Retroalimentando...")

            # 1. Atualização Adaptativa Global dos Pesos do Meta-Learning
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
                print(f"⚠️ Erro ao atualizar meta-learning: {e}")

            # 2. AUTO-AJUSTE DA MEMÓRIA DE CENÁRIOS E ESTRUTURAS
            try:
                # Extrai a estrutura real que acabou de ser sorteada
                estrutura_real = extrair_estrutura(list(resultado))
                hash_est = estrutura_real["hash_estrutura"]

                # Puxa o estado atual deste cenário específico no banco de dados
                cenario_banco = supabase.table("memoria_cenarios").select("*").eq("hash_estrutura", hash_est).execute().data

                vezes_gerado = 1
                score_acumulado = media_concurso

                if cenario_banco:
                    row_cenario = cenario_banco[0]
                    v_antigo = int(row_cenario.get("vezes_gerado", 0))
                    s_antigo = float(row_cenario.get("score_medio_real", 0.0))

                    vezes_gerado = v_antigo + 1
                    # Executa a média móvel cumulativa real ponderada
                    score_acumulado = ((s_antigo * v_antigo) + media_concurso) / vezes_gerado

                # Insere ou atualiza dinamicamente as métricas lidas pelo processamento diário
                supabase.table("memoria_cenarios").upsert({
                    "hash_estrutura": hash_est,
                    "soma_faixa": estrutura_real["soma_faixa"],
                    "pares": estrutura_real["pares"],
                    "primos": estrutura_real["primos"],
                    "linhas": estrutura_real["linhas"],
                    "vezes_gerado": vezes_gerado,
                    "score_medio_real": round(score_acumulado, 4),
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="soma_faixa,pares,primos,hash_estrutura").execute()

                print(f"📈 [Auto-Ajuste] Estrutura {hash_est} calibrada | Testes: {vezes_gerado}x | Score Real: {score_acumulado:.2f}")
            except Exception as e_cen:
                print(f"⚠️ Erro ao atualizar auto-aprendizado de cenários: {e_cen}")

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
        f"\n====================\n"
        f"✅ Processo concluído\n"
        f"📊 {processados} palpites processados"
    )


if __name__ == "__main__":
    main()

