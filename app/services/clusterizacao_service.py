import sys
import numpy as np
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# =========================================================
# HELPERS
# =========================================================
def calcular_linhas(nums):
    return [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25)
    ]

def calcular_colunas(nums):
    colunas = []
    for c in range(1, 6):
        colunas.append(sum(1 for n in nums if (n - c) % 5 == 0))
    return colunas

# =========================================================
# CLUSTERIZAÇÃO
# =========================================================
def identificar_cluster_jogo(dados, **kwargs):
    # =====================================================
    # CASO RECEBA FEATURES
    # =====================================================
    if isinstance(dados, dict):
        pares = dados.get("pares", 0)
        primos = dados.get("primos", 0)
        soma = dados.get("soma", 0)
        seq = dados.get("seq_max", 0)
        entropia = dados.get("entropia", 0)
        dispersao = dados.get("dispersao", 0)
        linhas = dados.get("linhas", [0, 0, 0, 0, 0])
    # =====================================================
    # CASO RECEBA JOGO
    # =====================================================
    else:
        nums = sorted([int(n) for n in dados])
        pares = sum(1 for n in nums if n % 2 == 0)
        primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})
        soma = sum(nums)
        seq = max(np.diff(nums)) if len(nums) > 1 else 0
        entropia = float(np.std(nums))
        dispersao = float(max(nums) - min(nums))
        linhas = calcular_linhas(nums)

    # =====================================================
    # SCORE VETORIAL
    # =====================================================
    vetor = [pares, primos, soma / 15, seq, entropia, dispersao, max(linhas)]
    assinatura = int(sum(vetor) * 1000) % 12
    return assinatura

# =========================================================
# RECALIBRAGEM EM LOTE (CONECTA COM O HUB ANALYTICS v20)
# =========================================================
def recalibrar_clusters():
    from app.services.supabase_service import get_supabase
    supabase = get_supabase()
    print("🧬 [Clusters] Iniciando recalibragem e agregação estatística vetorial...")
    try:
        rows = (
            supabase
            .table("feature_store_jogos")
            # 🟢 CORREÇÃO: Remove 'score_mc' da busca para evitar o erro 42703
            .select("cluster_id, score_final, score, concurso_referencia")
            .order("created_at", desc=True)
            .limit(5000)
            .execute()
            .data
        )
        if not rows:
            print("⚠️ [Clusters] Feature Store sem dados recentes para recalibragem.")
            return
        mapa_clusters = {}
        for r in rows:
            c_id = int(r.get("cluster_id", 0))
            s_final = float(r.get("score_final", 0.0))
            # 🟢 CORREÇÃO: Usa a coluna física 'score' como fallback seguro para a média móvel
            s_mc = float(r.get("score", 0.0))
            conc_ref = int(r.get("concurso_referencia", 0))
            if c_id not in mapa_clusters:
                mapa_clusters[c_id] = {"scores": [], "scores_mc": [], "qtd": 0, "concursos": set()}
            mapa_clusters[c_id]["scores"].append(s_final)
            mapa_clusters[c_id]["scores_mc"].append(s_mc)
            mapa_clusters[c_id]["qtd"] += 1
            if conc_ref > 0:
                mapa_clusters[c_id]["concursos"].add(conc_ref)
        payload_upsert = []
        for c_id, dados in mapa_clusters.items():
            arr_scores = dados["scores"]
            arr_mc = dados["scores_mc"]
            score_medio = float(np.mean(arr_scores)) if arr_scores else 0.0
            score_mc_medio = float(np.mean(arr_mc)) if arr_mc else 0.0
            dispersao = float(np.std(arr_scores)) if len(arr_scores) > 1 else 0.0
            ultimo_concurso = max(dados["concursos"]) if dados["concursos"] else 0
            payload_upsert.append({
                "concurso_referencia": ultimo_concurso,
                "cluster_id": c_id,
                "qtd_jogos": dados["qtd"],
                "score_medio": round(score_medio, 6),
                "score_mc_medio": round(score_mc_medio, 6),
                "dispersao": round(dispersao, 6),
                "score": round(score_medio, 6),
                "updated_at": datetime.now().isoformat()
            })
        if payload_upsert:
            supabase.table("memoria_clusters").upsert(
                payload_upsert,
                on_conflict="concurso_referencia,cluster_id"
            ).execute()
            print(f"✅ [Clusters] Recalibragem concluída com sucesso para {len(payload_upsert)} clusters.")
    except Exception as e:
        print(f"❌ [Clusters] Erro crítico ao recalibrar clusters no Hub: {e}")
        raise e
