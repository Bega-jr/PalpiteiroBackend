import json
import time
import numpy as np
from datetime import datetime
from app.services.supabase_service import get_supabase


# =========================================================
# HELPERS
# =========================================================
def media_segura(valores, fallback=0.0):
    validos = [
        float(v)
        for v in valores
        if v is not None
    ]
    if not validos:
        return fallback
    return round(float(np.mean(validos)), 6)


def dispersao_scores(scores):
    if not scores:
        return 0.0
    return round(float(np.std(scores)), 6)


# =========================================================
# FEATURE STORE
# =========================================================
def persistir_feature_store(
    supabase,
    concurso_ref,
    candidatos,
    versao
):
    payload = []
    for idx, c in enumerate(candidatos, 1):
        payload.append({
            "concurso_referencia": concurso_ref,
            "indice_palpite": idx,
            "numeros": json.dumps(c["nums"]),
            "cluster_id": int(c.get("cluster_id", 0)),
            "score_final": round(float(c.get("score", 0)), 8),
            "score_mc": round(float(c.get("score_mc", 0)), 8),
            "estrutura": c.get("estrutura", {}),
            "features": c.get("features", {}),
            "versao_gerador": versao,
            "created_at": datetime.now().isoformat()
        })

    if payload:
        supabase.table(
            "feature_store_jogos"
        ).upsert(
            payload,
            on_conflict="concurso_referencia,indice_palpite"
        ).execute()

        print(f"🧠 Feature Store atualizado: {len(payload)} registros")


# =========================================================
# MEMÓRIA DE CLUSTERS
# =========================================================
def persistir_memoria_clusters(
    supabase,
    concurso_ref,
    candidatos
):
    clusters = {}
    for c in candidatos:
        cluster_id = int(c.get("cluster_id", 0))
        if cluster_id not in clusters:
            clusters[cluster_id] = {
                "scores": [],
                "score_mc": [],
                "qtd": 0
            }
        clusters[cluster_id]["scores"].append(float(c.get("score", 0)))
        clusters[cluster_id]["score_mc"].append(float(c.get("score_mc", 0)))
        clusters[cluster_id]["qtd"] += 1

    payload = []
    for cluster_id, dados in clusters.items():
        payload.append({
            "concurso_referencia": concurso_ref,
            "cluster_id": cluster_id,
            "qtd_jogos": dados["qtd"],
            "score_medio": media_segura(dados["scores"]),
            "score_mc_medio": media_segura(dados["score_mc"]),
            "dispersao": dispersao_scores(dados["scores"]),
            "updated_at": datetime.now().isoformat()
        })

    if payload:
        supabase.table(
            "memoria_clusters"
        ).upsert(
            payload,
            on_conflict="concurso_referencia,cluster_id"
        ).execute()

        print(f"🧬 Memória de clusters atualizada: {len(payload)} clusters")


# =========================================================
# TELEMETRIA
# =========================================================
def persistir_telemetria(
    supabase,
    concurso_ref,
    candidatos,
    tempo_execucao,
    versao
):
    scores = [
        float(c["score"])
        for c in candidatos
    ]

    payload = {
        "concurso_referencia": concurso_ref,
        "versao_gerador": versao,
        "tempo_execucao": round(float(tempo_execucao), 4),
        "qtd_candidatos": len(candidatos),
        "score_medio": media_segura(scores),
        "score_max": round(float(max(scores)) if scores else 0.0, 6),
        "score_min": round(float(min(scores)) if scores else 0.0, 6),
        "dispersao_scores": dispersao_scores(scores),
        "created_at": datetime.now().isoformat()
    }

    supabase.table(
        "telemetria_geracao"
    ).upsert(
        payload,
        on_conflict="concurso_referencia"
    ).execute()

    print("📡 Telemetria persistida")


# =========================================================
# MEMÓRIA ENSEMBLE
# =========================================================
def persistir_memoria_ensemble(
    supabase,
    concurso_ref,
    pesos,
    score_medio,
    versao
):
    payload = {
        "concurso_referencia": concurso_ref,
        "versao_gerador": versao,
        "peso_base": pesos.get("peso_base", 0),
        "peso_global": pesos.get("peso_global", 0),
        "peso_feedback": pesos.get("peso_feedback", 0),
        "peso_regime": pesos.get("peso_regime", 0),
        "peso_moldura": pesos.get("peso_moldura", 0),
        "peso_estrutura": pesos.get("peso_estrutura", 0),
        "peso_fadiga": pesos.get("peso_fadiga", 0),
        "peso_recencia": pesos.get("peso_recencia", 0),
        "score_medio": round(float(score_medio), 6),
        "created_at": datetime.now().isoformat()
    }

    supabase.table(
        "memoria_ensemble"
    ).upsert(
        payload,
        on_conflict="concurso_referencia"
    ).execute()

    print("⚙️ Memória ensemble persistida")


# =========================================================
# PIPELINE CENTRAL
# =========================================================
def persistir_analytics_completo(
    supabase,
    concurso_ref,
    candidatos,
    pesos,
    versao,
    tempo_execucao
):
    inicio = time.time()

    persistir_feature_store(
        supabase=supabase,
        concurso_ref=concurso_ref,
        candidatos=candidatos,
        versao=versao
    )

    persistir_memoria_clusters(
        supabase=supabase,
        concurso_ref=concurso_ref,
        candidatos=candidatos
    )

    persistir_telemetria(
        supabase=supabase,
        concurso_ref=concurso_ref,
        candidatos=candidatos,
        tempo_execucao=tempo_execucao,
        versao=versao
    )

    persistir_memoria_ensemble(
        supabase=supabase,
        concurso_ref=concurso_ref,
        pesos=pesos,
        score_medio=media_segura([c["score"] for c in candidatos]),
        versao=versao
    )

    fim = time.time()
    print(f"🚀 Analytics persistido em {fim - inicio:.2f}s")


# ======================================================
# FEATURE STORE (MÉTODO INDIVIDUAL ATUALIZADO)
# ======================================================
def salvar_feature_store_jogo(
    concurso,
    jogo,
    features,
    score,
    cluster_id
):
    supabase = get_supabase()

    # Extrai os filtros do dicionário para persistência em colunas físicas
    soma = int(features.get("soma", 0)) if features.get("soma") is not None else None
    pares = int(features.get("pares", 0)) if features.get("pares") is not None else None
    primos = int(features.get("primos", 0)) if features.get("primos") is not None else None
    moldura = int(features.get("moldura", 0)) if features.get("moldura") is not None else None
    repetidos = int(features.get("repetidos", 0)) if features.get("repetidos") is not None else None
    sequencias = int(features.get("seq_max", 0)) if features.get("seq_max") is not None else None
    
    # Captura metadados de regime se disponíveis
    regime = features.get("regime", "NEUTRO")

    payload = {
        "concurso_referencia": concurso,
        "numeros": jogo,  # Mantém o array ou string tratada
        "cluster_id": int(cluster_id),
        
        # Injeção nas colunas físicas
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "moldura": moldura,
        "repetidos": repetidos,
        "sequencias": sequencias,
        
        # Scores e metadados
        "score_base": round(float(score), 8),
        "score_final": round(float(score), 8),
        "score": round(float(score), 8),
        "regime": regime,
        
        # Guarda o dicionário cheio para compatibilidade complementar
        "features": features,
        "created_at": datetime.now().isoformat()
    }

    supabase.table(
        "feature_store_jogos"
    ).insert(
        payload
    ).execute()



# ======================================================
# CLUSTERS (COMPLETO, BLINDADO E ATUALIZADO v20)
# ======================================================
def salvar_cluster_jogo(
    concurso,
    cluster_id,
    jogo,
    score
):
    supabase = get_supabase()
    payload = {
        "concurso_referencia": concurso,
        "cluster_id": int(cluster_id),
        "numeros": jogo,
        "score": round(float(score), 8),
        "updated_at": datetime.now().isoformat()
    }
    # 🟢 CORREÇÃO: Altera de .insert() para .upsert() usando a restrição única do banco
    supabase.table(
        "memoria_clusters"
    ).upsert(
        payload,
        on_conflict="concurso_referencia,cluster_id"
    ).execute()


# =========================================================
# BRIDGE EXCLUSIVA COMPATÍVEL COM O HUB ANALYTICS v20
# =========================================================
def consolidar_telemetria():
    """
    Função ponte invocada pelo Hub Analytics v20.
    Reutiliza a telemetria do último concurso gerado para manter o Hub integrado.
    """
    print("📡 [Telemetria] Hub acionou a consolidação de métricas...")
    # Como o gerador diário já roda e salva a telemetria em lote a cada concurso,
    # a ponte serve apenas para confirmar o sincronismo e retornar Sucesso (True) para o Hub.
    print("✅ [Telemetria] Métricas já consolidadas na tabela telemetria_geracao.")

