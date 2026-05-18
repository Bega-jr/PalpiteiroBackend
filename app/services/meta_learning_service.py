from typing import Dict
from app.services.supabase_service import get_supabase

# ==================================================
# DEFAULTS (Alinhados com as suas colunas de memória)
# ==================================================
PESOS_DEFAULT = {
    "peso_base": 0.30,
    "peso_global": 0.15,
    "peso_feedback": 0.15,
    "peso_regime": 0.10,
    "peso_moldura": 0.10,
    "peso_estrutura": 0.10, # Mapeia o que chamávamos de peso_memoria
    "peso_fadiga": 0.05,
    "peso_recencia": 0.05
}

# ==================================================
# LEITURA DOS PESOS
# ==================================================
def obter_pesos_ensemble() -> Dict[str, float]:
    supabase = get_supabase()
    try:
        rows = (
            supabase
            .table("memoria_meta_learning")
            .select("peso_base, peso_global, peso_feedback, peso_regime, peso_moldura, peso_estrutura, peso_fadiga, peso_recencia")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
            .data
        )

        if not rows:
            return PESOS_DEFAULT.copy()

        row = rows[0]
        return {k: float(row.get(k, v)) for k, v in PESOS_DEFAULT.items()}
        
    except Exception as e:
        print(f"⚠️ Erro ao ler pesos da memória (usando padrão): {e}")
        return PESOS_DEFAULT.copy()

# ==================================================
# FEEDBACK E ATUALIZAÇÃO DOS PESOS (PÓS-SORTEIO)
# ==================================================
def atualizar_meta_learning(media_acertos: float, concurso_ref: int):
    supabase = get_supabase()
    pesos = obter_pesos_ensemble()

    try:
        # Aplica lógica adaptativa nas variáveis principais
        if media_acertos < 9:
            pesos["peso_estrutura"] += 0.02  # Valoriza padrões estruturais históricos
            pesos["peso_feedback"] += 0.02   # Aumenta peso do feedback
            pesos["peso_base"] -= 0.03
            pesos["peso_regime"] -= 0.01
        elif media_acertos >= 11:
            pesos["peso_base"] += 0.02
            pesos["peso_regime"] += 0.01
            pesos["peso_estrutura"] -= 0.01
            pesos["peso_feedback"] -= 0.01

        # Restringe limites de segurança para os 8 pesos
        for k in pesos:
            pesos[k] = max(0.02, min(0.60, pesos[k]))

        # Normalização rigorosa (Soma = 1.0)
        soma = sum(pesos.values())
        chaves = list(pesos.keys())
        for k in chaves:
            pesos[k] = round(pesos[k] / soma, 4)
            
        diferenca = round(1.0 - sum(pesos.values()), 4)
        if diferenca != 0.0:
            pesos[chaves[-1]] = round(pesos[chaves[-1]] + diferenca, 4)

        # 1. Salva o novo estado dos pesos na tabela 'memoria_meta_learning'
        payload_memoria = {**pesos, "score_ultimo": round(media_acertos, 4)}
        supabase.table("memoria_meta_learning").insert(payload_memoria).execute()

        # 2. Grava o log de auditoria na tabela 'meta_learning_execucoes'
        payload_execucao = {
            "concurso_referencia": concurso_ref,
            "peso_base": pesos["peso_base"],
            "peso_memoria": pesos["peso_estrutura"], # Guarda estrutura na coluna memoria do log
            "peso_regime": pesos["peso_regime"],
            "peso_feedback": pesos["peso_feedback"],
            "peso_recencia": pesos["peso_recencia"],
            "qtd_candidatos": 7, # QTD_FINAL padrão
            "score_medio": round(media_acertos, 6)
        }
        supabase.table("meta_learning_execucoes").upsert(payload_execucao, on_conflict="concurso_referencia").execute()

        print(f"🧠 Meta-Learning Atualizado | Concurso {concurso_ref} | Média Acertos={media_acertos:.2f}")

    except Exception as e:
        print(f"⚠️ Erro ao atualizar meta-learning: {e}")

