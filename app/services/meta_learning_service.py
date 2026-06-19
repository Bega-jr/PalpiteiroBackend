from typing import Dict
import numpy as np

from app.services.supabase_service import get_supabase

# ==================================================
# DEFAULTS
# ==================================================
PESOS_DEFAULT = {

    "peso_base": 0.28,

    "peso_global": 0.12,

    "peso_feedback": 0.10,

    "peso_regime": 0.07,

    "peso_moldura": 0.08,

    "peso_estrutura": 0.10,

    "peso_fadiga": 0.06,

    "peso_recencia": 0.06,

    "peso_montecarlo": 0.15,

    "peso_recompensa": 0.08
}

# ==================================================
# UTILS
# ==================================================
def limitar(valor, vmin=0.02, vmax=0.60):

    return max(
        vmin,
        min(vmax, valor)
    )


def normalizar_pesos(pesos):

    soma = sum(pesos.values())

    chaves = list(pesos.keys())

    for k in chaves:

        pesos[k] = round(
            pesos[k] / soma,
            4
        )

    diferenca = round(
        1.0 - sum(pesos.values()),
        4
    )

    if diferenca != 0:

        pesos[chaves[-1]] = round(
            pesos[chaves[-1]] + diferenca,
            4
        )

    return pesos


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

            return PESOS_DEFAULT.copy()

        row = rows[0]

        pesos = {
            k: float(row.get(k, v))
            for k, v in PESOS_DEFAULT.items()
        }

        return normalizar_pesos(pesos)

    except Exception as e:

        print(
            f"⚠️ Erro ao ler pesos da memória: {e}"
        )

        return PESOS_DEFAULT.copy()


# ==================================================
# CÁLCULO DE ENTROPIA
# ==================================================
def calcular_entropia(
    media_acertos,
    melhor_acerto,
    dispersao
):

    score = (
        (melhor_acerto * 0.50)
        +
        (media_acertos * 0.30)
        +
        (dispersao * 0.20)
    )

    return round(score / 15, 6)
# ==================================================
# INTELIGÊNCIA HISTÓRICA (30 concursos)
# ==================================================
def analisar_feedback_recente():

    supabase = get_supabase()

    try:

        rows = (
            supabase
            .table("memoria_feedback_loop")
            .select("*")
            .order(
                "concurso_referencia",
                desc=True
            )
            .limit(30)
            .execute()
            .data
        )

        if not rows:

            return {

                "media_acertos": 9.0,

                "dispersao": 3.0,

                "estabilidade": 0.70,

                "entropia": 0.50

            }

        medias = [
            float(
                x.get(
                    "media_acertos_ia",
                    0
                )
            )
            for x in rows
        ]

        dispersoes = [
            float(
                x.get(
                    "dispersao_media",
                    0
                )
            )
            for x in rows
        ]

        estabilidades = [
            float(
                x.get(
                    "estabilidade_media",
                    0
                )
            )
            for x in rows
        ]

        entropias = [
            float(
                x.get(
                    "entropia_media",
                    0
                )
            )
            for x in rows
        ]

        return {

            "media_acertos":
                np.mean(medias),

            "dispersao":
                np.mean(dispersoes),

            "estabilidade":
                np.mean(estabilidades),

            "entropia":
                np.mean(entropias)

        }

    except Exception as e:

        print(
            f"⚠️ Erro feedback histórico: {e}"
        )

        return {

            "media_acertos": 9,

            "dispersao": 3,

            "estabilidade": 0.7,

            "entropia": 0.5

        }

# ==================================================
# ANTI OVERFITTING
# ==================================================
def aplicar_anti_overfitting(
    pesos,
    media_acertos,
    dispersao,
    melhor_acerto
):

    # ==========================================
    # Cenário:
    # Muito concentrado
    # ==========================================
    if dispersao <= 2 and media_acertos <= 9:

        pesos["peso_base"] -= 0.015
        pesos["peso_feedback"] -= 0.010

        pesos["peso_estrutura"] += 0.015
        pesos["peso_recencia"] += 0.010

        print(
            "🧠 Anti-Overfitting: "
            "aumentando exploração estrutural"
        )

    # ==========================================
    # Cenário:
    # Pico isolado muito alto
    # ==========================================
    if melhor_acerto >= 14 and media_acertos < 11:

        pesos["peso_base"] -= 0.010
        pesos["peso_global"] -= 0.010

        pesos["peso_estrutura"] += 0.015
        pesos["peso_fadiga"] += 0.005

        print(
            "🎯 Pico isolado detectado: "
            "reduzindo convergência"
        )

    return pesos


# ==================================================
# CONTROLE DE ENTROPIA
# ==================================================
def aplicar_entropia_dinamica(
    pesos,
    score_entropia
):

        # ==========================================
        # Baixa entropia: jogos muito parecidos
        # ==========================================
        if score_entropia < 0.55:
            pesos["peso_estrutura"] += 0.02
            pesos["peso_recencia"] += 0.01
            pesos["peso_base"] -= 0.02
            print("🌪️ Entropia baixa: forçando diversidade")
        # ==========================================
        # Entropia muito alta: sistema instável
        # ==========================================
        elif score_entropia > 0.80:
            pesos["peso_base"] += 0.01
            pesos["peso_feedback"] += 0.01
            pesos["peso_estrutura"] -= 0.01
            print("📊 Entropia alta: reduzindo ruído estrutural")
        return pesos

# ==================================================
# FEEDBACK + EVOLUÇÃO DOS PESOS (ASSINATURA INTACTA)
# ==================================================
def atualizar_meta_learning(
    media_acertos: float,
    concurso_ref: int,
    tipo_regime: str = "NEUTRO",
    fator_feedback: float = 1.0,
    fator_global: float = 1.0,
    melhor_acerto: int = 0,
    pior_acerto: int = 0,
    dispersao: int = 0,
    qtd_palpites: int = 7,
    score_estrutural: float = 0.0
):
    supabase = get_supabase()
    pesos = obter_pesos_ensemble()
    feedback_30 = analisar_feedback_recente()
    media_30 = feedback_30["media_acertos"]
    dispersao_30 = feedback_30["dispersao"]
    estabilidade_30 = feedback_30["estabilidade"]
    entropia_30 = feedback_30["entropia"]
    try:


        # ==========================================
        # AUTO-ADAPTAÇÃO PELOS ÚLTIMOS 30 CONCURSOS
        # ==========================================
        if media_30 < 9:

            pesos["peso_estrutura"] += 0.015

            pesos["peso_feedback"] += 0.015

            pesos["peso_base"] -= 0.020

            print(
                "📉 Histórico fraco: "
                "favorecendo estrutura"
            )

        elif media_30 > 10:

            pesos["peso_base"] += 0.015

            pesos["peso_global"] += 0.010

            pesos["peso_estrutura"] -= 0.010

            print(
                "📈 Histórico consistente"
            )

        if estabilidade_30 < 0.60:

            pesos["peso_fadiga"] += 0.010

            pesos["peso_recencia"] += 0.010

            print(
                "🌪️ Sistema instável"
            )

        if dispersao_30 > 4:

            pesos["peso_estrutura"] += 0.010

            pesos["peso_montecarlo"] += 0.010

            print(
                "🎲 Alta dispersão histórica"
            )

        if entropia_30 < 0.40:

            pesos["peso_recencia"] += 0.010

            pesos["peso_estrutura"] += 0.010

            print(
                "🧠 Baixa diversidade histórica"
            )
        # ==========================================
        # AJUSTE POR MÉDIA
        # ==========================================
        if media_acertos < 9:
            pesos["peso_estrutura"] += 0.02
            pesos["peso_feedback"] += 0.02
            pesos["peso_base"] -= 0.03
            pesos["peso_regime"] -= 0.01
        elif media_acertos >= 11:
            pesos["peso_base"] += 0.02
            pesos["peso_regime"] += 0.01
            pesos["peso_estrutura"] -= 0.01
            pesos["peso_feedback"] -= 0.01

        # ==========================================
        # AJUSTE POR DISPERSÃO
        # ==========================================
        if dispersao >= 4:
            pesos["peso_estrutura"] += 0.01
            pesos["peso_fadiga"] += 0.01
            pesos["peso_base"] -= 0.01
            print("📉 Alta dispersão detectada")

        # ==========================================
        # AJUSTE POR REGIME
        # ==========================================
        if tipo_regime == "EXPANSAO_QUENTES":
            pesos["peso_regime"] += 0.01
        elif tipo_regime == "CONTRACAO_FRIAS":
            pesos["peso_recencia"] += 0.01

        # ==========================================
        # FILTROS E DINÂMICAS MODULARES
        # ==========================================
        score_entropia = calcular_entropia(media_acertos, melhor_acerto, dispersao)
        pesos = aplicar_entropia_dinamica(pesos, score_entropia)
        pesos = aplicar_anti_overfitting(pesos, media_acertos, dispersao, melhor_acerto)

        for k in pesos:
            pesos[k] = limitar(pesos[k])
        pesos = normalizar_pesos(pesos)

        # ==========================================
        # MEMÓRIA VIVA
        # ==========================================
        payload_memoria = {
            **pesos,
            "score_ultimo": round(media_acertos, 4),
            "entropia_atual": score_entropia
        }
        supabase.table("memoria_meta_learning").insert(payload_memoria).execute()

        # ==========================================
        # AUDITORIA HISTÓRICA
        # ==========================================
        payload_execucao = {

            "concurso_referencia": concurso_ref,

            "peso_base": pesos["peso_base"],

            "peso_global": pesos["peso_global"],

            "peso_feedback": pesos["peso_feedback"],

            "peso_regime": pesos["peso_regime"],

            "peso_moldura": pesos["peso_moldura"],

            "peso_estrutura": pesos["peso_estrutura"],

            "peso_fadiga": pesos["peso_fadiga"],

            "peso_recencia": pesos["peso_recencia"],

            "peso_montecarlo": pesos["peso_montecarlo"],

            "peso_recompensa": pesos["peso_recompensa"],

            "tipo_regime": tipo_regime,

            "fator_feedback": round(
                fator_feedback,
                6
            ),

            "fator_global": round(
                fator_global,
                6
            ),

            "melhor_acerto": melhor_acerto,

            "pior_acerto": pior_acerto,

            "dispersao": dispersao,

            "entropia": score_entropia,

            "qtd_candidatos": qtd_palpites,

            "score_estrutural": round(
                score_estrutural,
                6
            ),

            "score_medio": round(
                media_acertos,
                6
            )

        }
        supabase.table("meta_learning_execucoes").upsert(payload_execucao, on_conflict="concurso_referencia").execute()
        print(f"🧠 Meta-Learning v19 | Concurso {concurso_ref} | Média={media_acertos:.2f} | Best={melhor_acerto} | Spread={dispersao} | Entropia={score_entropia:.4f}")
    except Exception as e:
        print(f"⚠️ Erro meta-learning: {e}")

# ==================================================
# BRIDGE EXCLUSIVA COMPATÍVEL COM O HUB ANALYTICS v20
# ==================================================
def atualizar_pesos_dinamicos():
    """
    Invocada de forma direta e transparente pelo Hub Analytics v20.
    Consome o último log histórico e executa a evolução retroalimentada.
    """
    supabase = get_supabase()
    print("🧠 [Meta-Learning] Iniciando recalibragem macro e evolução de pesos via Hub...")
    try:
        auditoria = (
            supabase.table("meta_learning_execucoes")
            .select("*")
            .order("concurso_referencia", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not auditoria:
            print("⚠️ [Meta-Learning] Sem históricos na tabela meta_learning_execucoes para evoluir.")
            return

        last = auditoria[0]
        # Executa a chamada reaproveitando a assinatura principal estável
        atualizar_meta_learning(
            media_acertos=float(last.get("score_medio", 9.0)),
            concurso_ref=int(last.get("concurso_referencia", 0)),
            tipo_regime=last.get("tipo_regime", "NEUTRO"),
            fator_feedback=float(last.get("fator_feedback", 1.0)),
            fator_global=float(last.get("fator_global", 1.0)),
            melhor_acerto=int(last.get("melhor_acerto", 0)),
            pior_acerto=int(last.get("pior_acerto", 0)),
            dispersao=int(last.get("dispersao", 0)),
            qtd_palpites=int(last.get("qtd_candidatos", 7)),
            score_estrutural=float(last.get("score_estrutural", 0.0))
        )
    except Exception as e:
        print(f"❌ [Meta-Learning] Erro crítico na evolução de pesos do Hub: {e}")
        raise e
