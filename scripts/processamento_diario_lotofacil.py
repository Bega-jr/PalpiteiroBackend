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

NUMEROS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}


# ======================================================
# UTILITÁRIOS
# ======================================================

def normalizar(col):
    return (col - col.min()) / (col.max() - col.min() + 1e-9)


def calcular_tendencia(historico, numero, janela=25):
    ultimos = historico[-janela:]
    presencas = [1 if numero in h["numeros"] else 0 for h in ultimos]
    return float(np.mean(presencas))


def calcular_ciclo_historico_completo(historico):

    todos_25 = set(range(1, 26))
    sorteados = set()
    ciclo = 1

    for concurso in historico:
        sorteados.update(concurso["numeros"])

        if sorteados == todos_25:
            sorteados = set()
            ciclo += 1

    faltantes = sorted(todos_25 - sorteados)
    return (faltantes if faltantes else list(range(1, 26)), ciclo)


def extrair_estrutura(nums):

    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]

    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in NUMEROS_PRIMOS),
        "linhas": linhas,
        "hash_estrutura": "-".join(map(str, linhas))
    }


# ======================================================
# MEMÓRIA
# ======================================================

def buscar_memoria_real(supabase, estrutura):

    resp = supabase.table("memoria_cenarios") \
        .select("*") \
        .eq("hash_estrutura", estrutura["hash_estrutura"]) \
        .limit(1) \
        .execute()

    return resp.data[0] if resp.data else None


buscar_cenario_similar = buscar_memoria_real


def calcular_saturacao(memoria):
    if not memoria:
        return 0.0

    vezes = int(memoria.get("vezes_gerado", 0))
    if vezes <= 2:
        return 0.0

    return min(vezes / 20, 1.0)


def calcular_tendencia_memoria(memoria):
    if not memoria:
        return 0.0

    return float(memoria.get("score_medio_real", 0))


def ajustar_por_memoria(df, memoria):

    if not memoria:
        print("🧠 Novo cenário (sem histórico)")
        return df

    score_real = float(memoria.get("score_medio_real", 0))
    vezes = int(memoria.get("vezes_gerado", 0))

    print(f"🧠 Memória Ativa | Score Real: {score_real:.2f} | Testado: {vezes}x")

    if score_real >= 5:
        df["score"] *= 1.15
        print("🔥 Alta performance (+15%)")

    elif score_real >= 1:
        df["score"] *= 1.05
        print("📈 Cenário consistente (+5%)")

    elif vezes >= 5 and score_real == 0:
        df["score"] *= 0.85
        print("❄️ Cenário saturado (-15%)")

    return df


# ======================================================
# MAIN
# ======================================================

def main():

    supabase = get_supabase()

    print("🚀 [v4.7-FEEDBACK-LOOP] Processamento Inteligente Ativo")

    try:

        historico = carregar_historico()

        if not historico:
            print("⚠️ Histórico vazio")
            return

        ultimo = historico[-1]

        concurso = ultimo["concurso"]
        data = ultimo["data"]
        dezenas = ultimo["numeros"]

        print(f"📌 Concurso {concurso} | Data {data}")

        df = obter_estatisticas_com_score()

        df.loc[df["numero"].isin(dezenas), "atraso"] = 0

        df["tendencia"] = df["numero"].apply(
            lambda n: calcular_tendencia(historico, n)
        )

        df["freq_norm"] = normalizar(df["frequencia"])
        df["atraso_norm"] = 1 - normalizar(df["atraso"])
        df["tendencia_norm"] = normalizar(df["tendencia"])
        df["score_norm"] = normalizar(df["score"])

        df["score"] = (
            df["freq_norm"] * 0.35 +
            df["tendencia_norm"] * 0.30 +
            df["atraso_norm"] * 0.20 +
            df["score_norm"] * 0.15
        )

        # ==================================================
        # MEMÓRIA (UPSERT SAFE - SEM DUPLICAÇÃO)
        # ==================================================

        estrutura = extrair_estrutura(dezenas)
        memoria = buscar_memoria_real(supabase, estrutura)

        df = ajustar_por_memoria(df, memoria)

        tendencia_memoria = calcular_tendencia_memoria(memoria)
        saturacao = calcular_saturacao(memoria)

        payload = {
            "hash_estrutura": estrutura["hash_estrutura"],
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "tendencia": round(tendencia_memoria, 4),
            "saturacao": round(saturacao, 4),
            "ultima_aparicao": data,
            "updated_at": datetime.now().isoformat()
        }

        # 🔥 UPSERT DEFINITIVO (REMOVE 23505)
        supabase.table("memoria_cenarios") \
            .upsert(
                payload,
                on_conflict="soma_faixa,pares,primos,hash_estrutura"
            ).execute()

        print("🔄 Memória atualizada via UPSERT seguro")

        # =====================================================
        # 🧠 RETROALIMENTAÇÃO: DISPARO DO FEEDBACK LOOP
        # =====================================================
        try:
            # Busca os palpites gerados anteriormente para o concurso que acabou de ocorrer
            palpites_passados = supabase.table("palpites_validos") \
                .select("numeros") \
                .eq("concurso_referencia", int(concurso)).execute().data
            
            if palpites_passados:
                acertos_do_dia = []
                for p in palpites_passados:
                    # Faz o parse da lista stringificada JSON salva no banco
                    jogo_limpo = [int(x) for x in json.loads(p["numeros"])]
                    acertos = len(set(jogo_limpo) & set(dezenas))
                    acertos_do_dia.append(acertos)
                
                media_acertos = float(np.mean(acertos_do_dia))
                
                # Regra de Reforço Estocástico Baseada em Performance Real
                if media_acertos < 9.0:
                    fator_correcao = 0.92  # Erro alto: Força deflação de viés
                elif media_acertos >= 11.0:
                    fator_correcao = 1.05  # Sucesso alto: Força impulsionamento de convergência
                else:
                    fator_correcao = 1.00  # Desempenho esperado: Mantém estabilidade neutra
                
                payload_feedback = {
                    "concurso_referencia": int(concurso),
                    "media_acertos_ia": round(media_acertos, 2),
                    "fator_correcao": fator_correcao
                }
                
                # Persiste de forma indestrutível via upsert indexado por concurso único
                supabase.table("memoria_feedback_loop").upsert(
                    payload_feedback, on_conflict="concurso_referencia"
                ).execute()
                print(f"📡 Feedback Loop: Concurso {concurso} auditado automaticamente. Média acertos: {media_acertos:.2f} | Fator: {fator_correcao}")
            else:
                print(f"ℹ️ Feedback Loop: Nenhum palpite prévio armazenado para auditar o concurso {concurso}.")
        except Exception as e_fb:
            print(f"⚠️ Erro operacional ao processar Feedback Loop: {e_fb}")

        # ==================================================
        # REGIME
        # ==================================================

        _, ciclo = calcular_ciclo_historico_completo(historico)

        media_score = df[df["numero"].isin(dezenas)]["score"].mean()

        regime = "NEUTRO"

        if media_score > 0.55:
            regime = "EXPANSAO_QUENTES"

        elif media_score < 0.45:
            regime = "CONTRACAO_FRIAS"

        check_reg = supabase.table("memoria_regimes") \
            .select("id") \
            .eq("concurso", int(concurso)) \
            .execute()

        if not check_reg.data:

            supabase.table("memoria_regimes") \
                .insert({
                    "data_referencia": data,
                    "concurso": int(concurso),
                    "numero_ciclo": int(ciclo),
                    "tipo_regime": regime,
                    "score_global": float(media_score),
                    "media_soma": float(sum(dezenas)),
                    "media_pares": int(estrutura["pares"])
                }).execute()

            print(f"📡 Regime salvo: {regime}")

        else:
            print(f"ℹ️ Concurso {concurso} já existe em memoria_regimes")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

