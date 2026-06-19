import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.meta_learning_service import atualizar_meta_learning
from app.services.feature_store_service import gerar_features_jogo
# Importação da função necessária para extrair a estrutura real sorteada
from scripts.processamento_diario_lotofacil import extrair_estrutura

VERSAO = "v18.2-conferencia-roi-evolutivo"


# ======================================================
# AUXILIARES
# ======================================================
def parse_numeros(valor):

    if not valor:
        return []

    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):
        try:
            return [int(x) for x in json.loads(valor)]
        except Exception:
            return []

    return []


def montar_bloco_auditoria(
    concurso,
    resultado,
    ranking,
    concurso_atual=None
):

    linhas = [
        "=" * 50,
        f"📊 Concurso {concurso} — Auditoria de Performance",
        "",
        f"🎯 Resultado oficial: {sorted(resultado)}",
        "",
        "📌 Resultado IA:",
        ""
    ]

    for r in ranking:

        linhas.append(
            f"🔹 Palpite #{r['idx']} → {r['acertos']} acertos"
        )

    if concurso_atual:

        linhas.extend([
            "",
            f"⏳ Concurso {concurso_atual} ainda sem resultado oficial"
        ])

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
        .eq(
            "conferido",
            True
        )
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

    if ultimo_concurso not in mapa:

        print(
            f"⏳ Concurso {concurso_atual} ainda sem resultado oficial"
        )

        return

    registros = [
        r
        for r in ultimo
        if int(r["concurso_referencia"]) == ultimo_concurso
    ]

    ranking = sorted(
        [
            {
                "idx": r["indice_palpite"],
                "acertos": r["acertos"]
            }
            for r in registros
        ],
        key=lambda x: x["acertos"],
        reverse=True
    )

    print(
        montar_bloco_auditoria(
            ultimo_concurso,
            mapa[ultimo_concurso],
            ranking,
            concurso_atual
        )
    )


# ======================================================
# BULK UPDATE PALPITES
# ======================================================
def atualizar_palpites_lote(
    supabase,
    payload
):

    if not payload:
        return

    (
        supabase
        .table("palpites_validos")
        .upsert(
            payload,
            on_conflict="id"
        )
        .execute()
    )


# ======================================================
# BULK ROI ESTRUTURAS
# ======================================================
def atualizar_memoria_roi(
    supabase,
    concurso,
    historico_estruturas
):

    try:

        payload = []

        for item in historico_estruturas:

            hash_est = item.get(
                "hash_estrutura"
            )

            if not hash_est:
                continue

            acertos = item["acertos"]

            roi_real = max(
                0,
                (acertos - 8) / 7
            )

            payload.append({

                "hash_estrutura":
                    hash_est,

                "ultimo_concurso":
                    concurso,

                "acertos_reais":
                    acertos,

                "roi_real":
                    round(
                        roi_real,
                        6
                    ),

                "score_contextual_real":
                    round(
                        float(
                            item.get(
                                "score_contextual_real",
                                0
                            )
                        ),
                        6
                    ),

                "updated_at":
                    datetime.now().isoformat()

            })

        if payload:

            (
                supabase
                .table(
                    "memoria_roi_estruturas"
                )
                .upsert(
                    payload,
                    on_conflict="hash_estrutura"
                )
                .execute()
            )

            print(
                f"🧠 ROI estrutural atualizado ({len(payload)})"
            )

    except Exception as e:

        print(
            f"⚠️ Erro memória ROI: {e}"
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
        historico_estruturas = []

        payload_palpites = []
        payload_feature_store = []

        ultimo = (
            list(mapa[concurso - 1])
            if concurso - 1 in mapa
            else []
        )

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

            historico_estruturas.append({

                "hash_estrutura":
                    p.get(
                        "hash_estrutura"
                    ),

                "acertos":
                    acertos,

                "score_contextual_real":
                    float(
                        p.get(
                            "score_estrutural",
                            0
                        )
                    )

            })

            if p.get("score"):

                try:

                    scores_estruturais.append(
                        float(
                            p["score"]
                        )
                    )

                except Exception:
                    pass

            # ======================================
            # FEATURE STORE
            # ======================================
            try:

                features = gerar_features_jogo(
                    jogo=numeros,
                    ultimo=ultimo
                )

            except Exception as e_feat:

                print(
                    f"⚠️ Erro feature store: {e_feat}"
                )

                features = {}

            ranking.append({

                "id":
                    p["id"],

                "idx":
                    p["indice_palpite"],

                "acertos":
                    acertos

            })

            # ======================================
            # PAYLOAD PALPITES_VALIDOS
            # ======================================
            payload_palpites.append({

                "id":
                    p["id"],

                "acertos":
                    acertos,

                "processado":
                    True,

                "conferido":
                    True

            })

            # ======================================
            # PAYLOAD FEATURE_STORE
            # ======================================
            hash_jogo = "-".join(
                map(
                    str,
                    sorted(numeros)
                )
            )

            payload_feature_store.append({

                "concurso_referencia":
                    concurso,

                "hash_jogo":
                    hash_jogo,

                "numeros":
                    numeros,

                "soma":
                    features.get(
                        "soma",
                        0
                    ),

                "pares":
                    features.get(
                        "pares",
                        0
                    ),

                "primos":
                    features.get(
                        "primos",
                        0
                    ),

                "moldura":
                    features.get(
                        "moldura",
                        0
                    ),

                "repetidos":
                    features.get(
                        "repetidos",
                        0
                    ),

                "sequencias":
                    features.get(
                        "seq_max",
                        0
                    ),

                "features":
                    features

            })

            processados += 1

        # ======================================================
        # BULK PALPITES
        # ======================================================
        try:

            atualizar_palpites_lote(
                supabase,
                payload_palpites
            )

        except Exception as e_bulk:

            print(
                f"⚠️ Erro bulk palpites: {e_bulk}"
            )

        # ======================================================
        # BULK FEATURE STORE
        # ======================================================
        try:

            if payload_feature_store:

                (
                    supabase
                    .table(
                        "feature_store_jogos"
                    )
                    .upsert(
                        payload_feature_store,
                        on_conflict="hash_jogo"
                    )
                    .execute()
                )

        except Exception as e_fs:

            print(
                f"⚠️ Erro feature_store_jogos: {e_fs}"
            )

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
            estabilidade = max(
                0,
                1 - (dispersao / 15)
            )

            entropia_media = 0

            try:

                if scores_estruturais:

                    probs = np.array(scores_estruturais)

                    probs = probs / probs.sum()

                    entropia_media = float(
                        -np.sum(
                            probs * np.log2(
                                probs + 1e-12
                            )
                        )
                    )

            except:

                entropia_media = 0
            score_estrutural = 0

            if scores_estruturais:
                score_estrutural = sum(scores_estruturais) / len(scores_estruturais)

            print("\n🧠 [Meta-Learning Contextual] Retroalimentando...")

            # ======================================================
            # MEMÓRIA DE FEEDBACK LOOP
            # ======================================================
            try:

                fator_correcao = round(
                    media_concurso / 10,
                    4
                )

                (
                    supabase
                    .table(
                        "memoria_feedback_loop"
                    )
                    .insert({

                        "concurso_referencia":
                            concurso,

                        "media_acertos_ia":
                            round(
                                media_concurso,
                                4
                            ),

                        "fator_correcao":
                            fator_correcao,

                        "dispersao_media":
                            round(
                                dispersao,
                                6
                            ),

                        "estabilidade_media":
                            round(
                                estabilidade,
                                6
                            ),

                        "entropia_media":
                            round(
                                entropia_media,
                                6
                            )

                    })
                    .execute()
                )

                print(
                    "🧠 Feedback loop atualizado"
                )

            except Exception as e_feedback:

                print(
                    f"⚠️ Erro memoria_feedback_loop: {e_feedback}"
                )

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

            # ======================================================
            # 2. AUTO-AJUSTE DA MEMÓRIA DE CENÁRIOS E ESTRUTURAS
            # ======================================================
            try:
            
                estrutura_real = extrair_estrutura(
                    list(resultado)
                )
            
                hash_est = estrutura_real["hash_estrutura"]
            
                cenario_banco = (
                    supabase
                    .table("memoria_cenarios")
                    .select("*")
                    .eq("hash_estrutura", hash_est)
                    .limit(1)
                    .execute()
                    .data
                )
            
                agora = datetime.now().isoformat()
            
                vezes_gerado = 1
                score_medio_real = media_concurso
            
                estabilidade_media = 1.0
                dispersao_media = dispersao
            
                taxa_sobrevivencia = (
                    1 if media_concurso >= 10 else 0
                )
            
                score_contextual = media_concurso
            
                score_previsibilidade = (
                    max(
                        0,
                        1 - (dispersao / 15)
                    )
                )
            
                if cenario_banco:
            
                    row = cenario_banco[0]
            
                    v_antigo = int(
                        row.get(
                            "vezes_gerado",
                            0
                        )
                    )
            
                    score_antigo = float(
                        row.get(
                            "score_medio_real",
                            0
                        )
                    )
            
                    estabilidade_antiga = float(
                        row.get(
                            "estabilidade_media",
                            0
                        )
                    )
            
                    dispersao_antiga = float(
                        row.get(
                            "dispersao_media",
                            0
                        )
                    )
            
                    sobrevivencia_antiga = float(
                        row.get(
                            "taxa_sobrevivencia",
                            0
                        )
                    )
            
                    previsibilidade_antiga = float(
                        row.get(
                            "score_previsibilidade",
                            0
                        )
                    )
            
                    vezes_gerado = v_antigo + 1
            
                    score_medio_real = (
                        (
                            score_antigo * v_antigo
                        )
                        + media_concurso
                    ) / vezes_gerado
            
                    estabilidade_atual = max(
                        0,
                        1 - (dispersao / 15)
                    )
            
                    estabilidade_media = (
                        (
                            estabilidade_antiga * v_antigo
                        )
                        + estabilidade_atual
                    ) / vezes_gerado
            
                    dispersao_media = (
                        (
                            dispersao_antiga * v_antigo
                        )
                        + dispersao
                    ) / vezes_gerado
            
                    taxa_sobrevivencia = (
                        (
                            sobrevivencia_antiga * v_antigo
                        )
                        + (
                            1 if media_concurso >= 10
                            else 0
                        )
                    ) / vezes_gerado
            
                    score_previsibilidade = (
                        (
                            previsibilidade_antiga * v_antigo
                        )
                        + max(
                            0,
                            1 - (dispersao / 15)
                        )
                    ) / vezes_gerado
            
                    score_contextual = (
                        score_medio_real * 0.60
                        +
                        estabilidade_media * 0.20
                        +
                        taxa_sobrevivencia * 10 * 0.20
                    )
            
                (
                    supabase
                    .table("memoria_cenarios")
                    .upsert({
            
                        "hash_estrutura":
                            hash_est,
            
                        "soma_faixa":
                            estrutura_real["soma_faixa"],
            
                        "pares":
                            estrutura_real["pares"],
            
                        "primos":
                            estrutura_real["primos"],
            
                        "linhas":
                            estrutura_real["linhas"],
            
                        "vezes_gerado":
                            vezes_gerado,
            
                        "score_medio_real":
                            round(
                                score_medio_real,
                                4
                            ),
            
                        "estabilidade_media":
                            round(
                                estabilidade_media,
                                6
                            ),
            
                        "dispersao_media":
                            round(
                                dispersao_media,
                                6
                            ),
            
                        "taxa_sobrevivencia":
                            round(
                                taxa_sobrevivencia,
                                6
                            ),
            
                        "score_contextual":
                            round(
                                score_contextual,
                                6
                            ),
            
                        "score_previsibilidade":
                            round(
                                score_previsibilidade,
                                6
                            ),
            
                        "ultima_aparicao":
                            concurso,
            
                        "ultima_atualizacao_contextual":
                            agora,
            
                        "updated_at":
                            agora
            
                    },
                    on_conflict="hash_estrutura"
                    )
                    .execute()
                )
            
                print(
                    f"📈 Estrutura {hash_est} | "
                    f"Score={score_medio_real:.2f} | "
                    f"Estab={estabilidade_media:.2f} | "
                    f"Disp={dispersao_media:.2f}"
                )

                # ======================================================
                # ROI DAS ESTRUTURAS
                # ======================================================
                # Chamada da função isolada para evitar que erros nela 
                # quebrem o fluxo principal dos cenários
                try:
                    atualizar_memoria_roi(
                        supabase,
                        concurso,
                        historico_estruturas
                    )
                except Exception as e_roi:
                    print(f"⚠️ Erro memória ROI: {e_roi}")

            except Exception as e_cen:
                print(f"⚠️ Erro ao atualizar memoria_cenarios: {e_cen}")


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
