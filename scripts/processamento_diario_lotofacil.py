import sys
from pathlib import Path
import numpy as np
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    obter_estatisticas_com_score,
    carregar_historico
)

NUMEROS_PRIMOS = {
    2, 3, 5, 7, 11,
    13, 17, 19, 23
}


VERSAO = "v19.0-contextual-processing"


# ======================================================
# UTILITÁRIOS
# ======================================================

def normalizar(col):
    return (
        (col - col.min())
        /
        (col.max() - col.min() + 1e-9)
    )


def calcular_tendencia(
    historico,
    numero,
    janela=25
):
    ultimos = historico[-janela:]
    presencas = [
        1 if numero in h["numeros"] else 0
        for h in ultimos
    ]
    return float(
        np.mean(presencas)
    )


def calcular_ciclo_historico_completo(historico):
    todos_25 = set(
        range(1, 26)
    )
    sorteados = set()
    ciclo = 1

    for concurso in historico:
        sorteados.update(
            concurso["numeros"]
        )
        if sorteados == todos_25:
            sorteados = set()
            ciclo += 1

    faltantes = sorted(
        todos_25 - sorteados
    )

    return (
        (
            faltantes
            if faltantes
            else list(range(1, 26))
        ),
        ciclo
    )


def extrair_estrutura(nums):
    linhas = [
        sum(
            1 for n in nums
            if 1 <= n <= 5
        ),
        sum(
            1 for n in nums
            if 6 <= n <= 10
        ),
        sum(
            1 for n in nums
            if 11 <= n <= 15
        ),
        sum(
            1 for n in nums
            if 16 <= n <= 20
        ),
        sum(
            1 for n in nums
            if 21 <= n <= 25
        ),
    ]

    return {
        "soma_faixa": int(
            round(sum(nums) / 10) * 10
        ),
        "pares": sum(
            1 for n in nums
            if n % 2 == 0
        ),
        "primos": sum(
            1 for n in nums
            if n in NUMEROS_PRIMOS
        ),
        "linhas": linhas,
        "hash_estrutura": "-".join(
            map(str, linhas)
        )
    }


def calcular_estabilidade(acertos):
    if not acertos:
        return 0.0
    dp = float(
        np.std(acertos)
    )
    return round(
        max(0.0, 1 - (dp / 5)),
        4
    )


def calcular_dispersao(acertos):
    if not acertos:
        return 0
    return int(
        max(acertos) - min(acertos)
    )


# ======================================================
# MEMÓRIA
# ======================================================

def buscar_memoria_real(
    supabase,
    estrutura
):
    resp = (
        supabase
        .table("memoria_cenarios")
        .select("*")
        .eq("hash_estrutura", estrutura["hash_estrutura"])
        .eq("soma_faixa", estrutura["soma_faixa"])
        .eq("pares", estrutura["pares"])
        .eq("primos", estrutura["primos"])
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    return (
        resp.data[0]
        if resp.data
        else None
    )


buscar_cenario_similar = buscar_memoria_real


def calcular_saturacao(memoria):
    if not memoria:
        return 0.0

    vezes = int(
        memoria.get(
            "vezes_gerado",
            0
        )
    )
    if vezes <= 2:
        return 0.0

    return min(
        vezes / 20,
        1.0
    )


def calcular_tendencia_memoria(memoria):
    if not memoria:
        return 0.0
    return float(
        memoria.get(
            "score_medio_real",
            0
        )
    )


def ajustar_por_memoria(df, memoria):
    if not memoria:
        print(
            "🧠 Novo cenário (sem histórico)"
        )
        return df

    score_real = float(
        memoria.get(
            "score_medio_real",
            0
        )
    )
    vezes = int(
        memoria.get(
            "vezes_gerado",
            0
        )
    )
    estabilidade = float(
        memoria.get(
            "estabilidade_media",
            0
        )
    )
    dispersao_media = float(
        memoria.get(
            "dispersao_media",
            0
        )
    )

    print(
        f"🧠 Memória Ativa | "
        f"Score Real: {score_real:.2f} | "
        f"Testado: {vezes}x"
    )

    # ==========================================
    # PERFORMANCE POSITIVA
    # ==========================================
    if score_real >= 9:
        df["score"] *= 1.15
        print(
            "🔥 Alta performance (+15%)"
        )
    elif score_real >= 7:
        df["score"] *= 1.05
        print(
            "📈 Cenário consistente (+5%)"
        )

    # ==========================================
    # SATURAÇÃO
    # ==========================================
    elif vezes >= 5 and score_real <= 5:
        df["score"] *= 0.85
        print(
            "❄️ Cenário saturado (-15%)"
        )

    # ==========================================
    # INSTABILIDADE
    # ==========================================
    if dispersao_media >= 5:
        df["score"] *= 0.92
        print(
            "⚠️ Instabilidade contextual (-8%)"
        )

    # ==========================================
    # BAIXA ESTABILIDADE
    # ==========================================
    if estabilidade <= 0.35:
        df["score"] *= 0.94
        print(
            "🧠 Baixa estabilidade detectada (-6%)"
        )

    return df


# ======================================================
# MAIN
# ======================================================

def main():
    supabase = get_supabase()

    print(
        f"🚀 [{VERSAO}] "
        f"Processamento Inteligente Ativo"
    )

    try:
        historico = carregar_historico()
        if not historico:
            print(
                "⚠️ Histórico vazio"
            )
            return

        ultimo = historico[-1]
        concurso = ultimo["concurso"]
        data = ultimo["data"]
        dezenas = ultimo["numeros"]

        print(
            f"📌 Concurso {concurso} | "
            f"Data {data}"
        )

        df = obter_estatisticas_com_score()

        df.loc[
            df["numero"].isin(dezenas),
            "atraso"
        ] = 0

        df["tendencia"] = df["numero"].apply(
            lambda n:
            calcular_tendencia(
                historico,
                n
            )
        )

        df["freq_norm"] = normalizar(
            df["frequencia"]
        )
        df["atraso_norm"] = 1 - normalizar(
            df["atraso"]
        )
        df["tendencia_norm"] = normalizar(
            df["tendencia"]
        )
        df["score_norm"] = normalizar(
            df["score"]
        )

        df["score"] = (
            df["freq_norm"] * 0.35
            +
            df["tendencia_norm"] * 0.30
            +
            df["atraso_norm"] * 0.20
            +
            df["score_norm"] * 0.15
        )

        # ==================================================
        # MEMÓRIA
        # ==================================================
        estrutura = extrair_estrutura(
            dezenas
        )
        memoria = buscar_memoria_real(
            supabase,
            estrutura
        )
        df = ajustar_por_memoria(
            df,
            memoria
        )

        tendencia_memoria = (
            calcular_tendencia_memoria(
                memoria
            )
        )
        saturacao = (
            calcular_saturacao(
                memoria
            )
        )

        # ======================================================
        # FEEDBACK LOOP
        # ======================================================
        media_acertos = 0.0
        fator_correcao = 1.0
        dispersao = 0
        estabilidade = 0.0

        try:
            palpites_passados = (
                supabase
                .table("palpites_validos")
                .select("numeros")
                .eq("concurso_referencia", int(concurso))
                .execute()
                .data
            )

            if palpites_passados:
                acertos_do_dia = []
                for p in palpites_passados:
                    jogo_limpo = [
                        int(x)
                        for x in json.loads(p["numeros"])
                    ]
                    acertos = len(
                        set(jogo_limpo)
                        &
                        set(dezenas)
                    )
                    acertos_do_dia.append(acertos)

                media_acertos = float(
                    np.mean(acertos_do_dia)
                )
                dispersao = calcular_dispersao(acertos_do_dia)
                estabilidade = calcular_estabilidade(acertos_do_dia)

                fator_correcao = (
                    0.92
                    if media_acertos < 9.0
                    else (
                        1.05
                        if media_acertos >= 11.0
                        else 1.00
                    )
                )

                payload_feedback = {
                    "concurso_referencia": int(concurso),
                    "media_acertos_ia": round(media_acertos, 2),
                    "fator_correcao": fator_correcao,
                    "dispersao_media": dispersao,
                    
                    # CORREÇÃO 1: Substituído o caractere residual pela variável local correta
                    "estabilidade_media": estabilidade
                }

                supabase.table(
                    "memoria_feedback_loop"
                ).upsert(
                    payload_feedback,
                    on_conflict="concurso_referencia"
                ).execute()

                print(
                    f"📡 Feedback Loop: "
                    f"Concurso {concurso} auditado. "
                    f"Média={media_acertos:.2f} | "
                    f"Spread={dispersao} | "
                    f"Estabilidade={estabilidade:.4f}"
                )
            else:
                print(
                    f"ℹ️ Nenhum palpite "
                    f"encontrado para auditoria."
                )
        except Exception as e_fb:
            print(f"⚠️ Erro Feedback Loop: {e_fb}")

        # ==================================================
        # MEMÓRIA CONTEXTUAL
        # ==================================================
        payload_memoria = {
            "hash_estrutura": estrutura["hash_estrutura"],
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "tendencia": round(tendencia_memoria, 4),
            "saturacao": round(saturacao, 4),
            "score_medio_real": round(media_acertos, 4),
            "dispersao_media": dispersao,
            "estabilidade_media": estabilidade,
            "ultima_aparicao": data,
            "updated_at": datetime.now().isoformat()
        }

        supabase.table(
            "memoria_cenarios"
        ).upsert(
            payload_memoria,
            on_conflict="hash_estrutura"
        ).execute()

        print("🔄 Memória estrutural updated via UPSERT seguro")

        # ==================================================
        # REGIME CONTEXTUAL
        # ==================================================
        _, ciclo = calcular_ciclo_historico_completo(historico)
        media_score = float(df[df["numero"].isin(dezenas)]["score"].mean())

        regime = "NEUTRO"
        if media_score > 0.55:
            regime = "EXPANSAO_QUENTES"
        elif media_score < 0.45:
            regime = "CONTRACAO_FRIAS"

        # Proteção contextual baseada no Spread
        if dispersao >= 5:
            regime = "CONTRACAO_FRIAS"
            print("⚠️ Instabilidade contextual detectada. Forçando CONTRACAO_FRIAS.")

        # Converter data ISO para inteiro YYYYMMDD
        data_int = int(data.replace("-", ""))

        payload_regime = {
            "data_referencia": data_int,
            "concurso": int(concurso),
            "numero_ciclo": int(ciclo),
            "tipo_regime": regime,
            "score_global": float(media_score),
            "media_soma": float(sum(dezenas)),
            "media_pares": int(estrutura["pares"]),
            "contexto_repetidos": float(
                np.mean([
                    len(set(historico[i]["numeros"]) & set(historico[i - 1]["numeros"]))
                    for i in range(1, min(15, len(historico)))
                ])
            ),
            
            # CORREÇÃO 2: Extrai a média das linhas obtendo um número decimal puro aceito pela coluna numeric
            "contexto_seq": float(np.mean(estrutura["linhas"]))
        }

        supabase.table(
            "memoria_regimes"
        ).upsert(
            payload_regime,
            on_conflict="concurso"
        ).execute()

        print(
            f"📡 Regime adaptativo consolidado: {regime} | Score Global: {media_score:.4f}"
        )

        # ======================================================
        # 🔗 🆕 CONCILIAÇÃO AUTOMÁTICA DAS MÉTRICAS DO FRONT-END
        # ======================================================
        print("⚡ [Auto-Sincronia] Atualizando tabelas públicas de estatísticas do site...")
        faltantes_ciclo, ciclo_atual = calcular_ciclo_historico_completo(historico)
        df_sorted_score = df.sort_values("score", ascending=False)
        df_sorted_atraso = df.sort_values("atraso", ascending=False)

        # 1. Alimenta a 'estatisticas_diarias_v2' com base no concurso processado hoje
        payload_diario_publico = {
            "data_referencia": data_int,
            "concurso": int(concurso),
            "numero_ciclo": int(ciclo_atual),
            "media_soma": int(sum(dezenas)),
            "media_pares": int(estrutura["pares"]),
            "media_impares": int(15 - estrutura["pares"]),
            "media_primos": int(estrutura["primos"]),
            "numeros_atrasados": [int(n) for n in faltantes_ciclo],
            "numeros_quentes": [int(n) for n in df_sorted_score.head(5)["numero"].tolist()],
            "numeros_frios": [int(n) for n in df_sorted_score.tail(5)["numero"].tolist()],
            "atrasados_ranking": [int(n) for n in df_sorted_atraso.head(5)["numero"].tolist()]
        }
        supabase.table("estatisticas_diarias_v2").upsert(
            payload_diario_publico, on_conflict="data_referencia"
        ).execute()

        # 2. Alimenta a 'estatisticas_numeros' que renderiza a tabela de dezenas individuais do site
        payload_numeros_publico = []
        for _, row in df.iterrows():
            payload_numeros_publico.append({
                "data_referencia": data_int,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": round(float(row["score"]), 6)
            })
        supabase.table("estatisticas_numeros").upsert(
            payload_numeros_publico, on_conflict="data_referencia,numero"
        ).execute()

        print(f"✅ [Sincronia Concluída] Estatísticas estáticas atualizadas para o Concurso {concurso}.")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
