import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.meta_learning_service import atualizar_meta_learning
from scripts.processamento_diario_lotofacil import carregar_historico, extrair_estrutura

def avaliar_desempenho_concurso():
    supabase = get_supabase()
    
    hist = carregar_historico()
    ultimo_concurso = hist[-1]
    
    concurso_real = int(ultimo_concurso["concurso"])
    numeros_sorteados = set(ultimo_concurso["numeros"])
    
    print(f"🎲 [Modo Manual] Reprocessando Concurso {concurso_real} -> {sorted(list(numeros_sorteados))}")
    
    rows = (
        supabase
        .table("palpites_validos")
        .select("indice_palpite, numeros, score, data_referencia")
        .eq("concurso_referencia", concurso_real)
        .execute()
        .data
    )
    
    if not rows:
        print(f"ℹ️ Nenhum palpite encontrado para o concurso {concurso_real}.")
        return

    acertos_totais = []
    palpites_atualizados = []
    scores_estruturais = []

    for row in rows:
        # ======================================================
        # TRATAMENTO ROBUSTO DE TIPAGEM (STRING VS LISTA NATIVA)
        # ======================================================
        numeros_brutos = row["numeros"]
        if isinstance(numeros_brutos, str):
            try:
                nums_palpite = set(json.loads(numeros_brutos))
            except Exception:
                nums_palpite = set()
        elif isinstance(numeros_brutos, list):
            nums_palpite = set(int(x) for x in numeros_brutos)
        else:
            nums_palpite = set()

        qtd_acertos = len(nums_palpite & numeros_sorteados)
        acertos_totais.append(qtd_acertos)
        
        if row.get("score"):
            try:
                scores_estruturais.append(float(row["score"]))
            except:
                pass
        
        data_jogo = row.get("data_referencia") or datetime.now().date().isoformat()

        numeros_originais = row.get("numeros")
        
        palpites_atualizados.append({
            "concurso_referencia": concurso_real,
            "indice_palpite": row["indice_palpite"],
            "data_referencia": data_jogo, # 🟢 Adicionado para satisfazer a restrição NOT NULL
            "numeros": numeros_originais, # 🟢 Adicionado para satisfazer a restrição NOT NULL de números
            "acertos": qtd_acertos,
            "conferido": True,
            "processado": True
        })

    if not acertos_totais:
        print("⚠️ Nenhum palpite pôde ser processado devido a formato inválido.")
        return

    media_acertos_ensemble = sum(acertos_totais) / len(acertos_totais)
    melhor_acerto = max(acertos_totais)
    pior_acerto = min(acertos_totais)
    dispersao = melhor_acerto - pior_acerto
    score_estrutural = sum(scores_estruturais) / len(scores_estruturais) if scores_estruturais else 0.0

    # Busca contexto de regime anterior para não quebrar a assinatura da v18.1
    tipo_regime = "NEUTRO"
    try:
        reg = supabase.table("memoria_regimes").select("tipo_regime").eq("concurso", concurso_real - 1).limit(1).execute().data
        if reg:
            tipo_regime = reg[0]["tipo_regime"]
    except:
        pass

    print(f"📈 Média: {media_acertos_ensemble:.2f} | Spread: {dispersao}")

    # 1. Updates Meta-Learning com a assinatura correta
    atualizar_meta_learning(
        media_acertos=media_acertos_ensemble,
        concurso_ref=concurso_real,
        melhor_acerto=melhor_acerto,
        pior_acerto=pior_acerto,
        dispersao=dispersao,
        qtd_palpites=len(acertos_totais),
        tipo_regime=tipo_regime,
        score_estrutural=score_estrutural
    )

    # ======================================================
    # 2. AUTO-AJUSTE DA MEMÓRIA DE CENÁRIOS E ESTRUTURAS
    # ======================================================
    try:
    
        estrutura_real = extrair_estrutura(
            list(numeros_sorteados)
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
        data_int = int(datetime.now().date().isoformat().replace("-", ""))
    
        vezes_gerado = 1
        score_medio_real = media_acertos_ensemble
    
        estabilidade_media = 1.0
        dispersao_media = dispersao
    
        taxa_sobrevivencia = (
            1 if media_acertos_ensemble >= 10 else 0
        )
    
        score_contextual = media_acertos_ensemble
    
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
                + media_acertos_ensemble
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
                    1 if media_acertos_ensemble >= 10
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
                    data_int,
    
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
    
    except Exception as e_cen:
    
        print(
            f"⚠️ Erro ao atualizar "
            f"memoria_cenarios: {e_cen}"
        )

    # 3. Força a atualização de todos os palpites da rodada de forma segura (Bulk Upsert)
    if palpites_atualizados:
        try:
            supabase.table("palpites_validos").upsert(
                palpites_atualizados,
                on_conflict="concurso_referencia,indice_palpite"
            ).execute()
            print(f"✅ Banco de dados sincronizado em lote ({len(palpites_atualizados)} jogos).")
        except Exception as e:
            print(f"⚠️ Erro ao salvar palpites em lote: {e}")


if __name__ == "__main__":
    avaliar_desempenho_concurso()

