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

    # 2. Atualiza a Memória de Cenários estruturais
    try:
        estrutura_real = extrair_estrutura(list(numeros_sorteados))
        hash_est = estrutura_real["hash_estrutura"]
        cenario_banco = supabase.table("memoria_cenarios").select("*").eq("hash_estrutura", hash_est).execute().data
        
        vezes_gerado = 1
        score_acumulado = media_acertos_ensemble
        if cenario_banco:
            v_antigo = int(cenario_banco[0].get("vezes_gerado", 0))
            s_antigo = float(cenario_banco[0].get("score_medio_real", 0.0))
            vezes_gerado = v_antigo + 1
            score_acumulado = ((s_antigo * v_antigo) + media_acertos_ensemble) / vezes_gerado

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
    except Exception as e_cen:
        print(f"⚠️ Erro ao recalibrar cenário: {e_cen}")

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

