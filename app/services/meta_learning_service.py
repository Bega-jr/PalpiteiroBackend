from typing import Dict
from app.services.supabase_service import get_supabase

# ==================================================
# DEFAULTS
# ==================================================
PESOS_DEFAULT = {
    "peso_base": 0.40,
    "peso_memoria": 0.20,
    "peso_regime": 0.15,
    "peso_feedback": 0.15,
    "peso_recencia": 0.10
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
            .select("*")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
            .data
        )

        if not rows:
            return PESOS_DEFAULT.copy() # .copy() evita mutação acidental

        row = rows[0]
        return {
            "peso_base": float(row.get("peso_base", 0.40)),
            "peso_memoria": float(row.get("peso_memoria", 0.20)),
            "peso_regime": float(row.get("peso_regime", 0.15)),
            "peso_feedback": float(row.get("peso_feedback", 0.15)),
            "peso_recencia": float(row.get("peso_recencia", 0.10))
        }
    except Exception as e:
        print(f"⚠️ Erro ao ler pesos (usando padrão): {e}") # Log adicionado
        return PESOS_DEFAULT.copy()

# ==================================================
# REGISTRO DAS EXECUÇÕES
# ==================================================
def registrar_execucao_ensemble(
    concurso_ref: int,
    media_score: float,
    qtd_palpites: int,
    versao: str
):
    supabase = get_supabase()
    try:
        payload = {
            "concurso_referencia": concurso_ref,
            "media_score": round(media_score, 6),
            "qtd_palpites": qtd_palpites,
            "versao_modelo": versao
        }
        supabase.table("meta_learning_execucoes").upsert(
            payload, on_conflict="concurso_referencia"
        ).execute()
        print(f"🧠 Ensemble registrado | Concurso {concurso_ref}")
    except Exception as e:
        print(f"⚠️ Erro registrar ensemble: {e}")

# ==================================================
# AJUSTE DOS PESOS
# ==================================================
def atualizar_meta_learning(media_acertos: float):
    supabase = get_supabase()
    pesos = obter_pesos_ensemble()

    try:
        # Aplica a lógica de recompensa/penalidade
        if media_acertos < 9:
            pesos["peso_memoria"] += 0.02
            pesos["peso_feedback"] += 0.02
            pesos["peso_base"] -= 0.02
            pesos["peso_regime"] -= 0.01
        elif media_acertos >= 11:
            pesos["peso_base"] += 0.02
            pesos["peso_regime"] += 0.01
            pesos["peso_memoria"] -= 0.01
            pesos["peso_feedback"] -= 0.01

        # Restringe limites (bounds)
        for k in pesos:
            pesos[k] = max(0.05, min(0.60, pesos[k]))

        # Normalização matemática rigorosa
        soma = sum(pesos.values())
        chaves = list(pesos.keys())
        
        for k in chaves:
            pesos[k] = round(pesos[k] / soma, 4)
            
        # Força a soma exata corrigindo resíduos de arredondamento no último item
        diferenca = round(1.0 - sum(pesos.values()), 4)
        if diferenca != 0.0:
            pesos[chaves[-1]] = round(pesos[chaves[-1]] + diferenca, 4)

        # Salva no banco de dados
        supabase.table("memoria_meta_learning").insert(pesos).execute()
        print(f"🧠 Meta-learning atualizado | Média={media_acertos:.2f} | Soma={sum(pesos.values())}")

    except Exception as e:
        print(f"⚠️ Erro meta-learning: {e}")
