import sys
from pathlib import Path
import numpy as np
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

    presencas = [
        1 if numero in h["numeros"] else 0
        for h in ultimos
    ]

    return float(np.mean(presencas))


def calcular_ciclo_historico_completo(historico):

    todos_25 = set(range(1, 26))

    sorteados = set()

    ciclo = 1

    for conc in historico:

        sorteados.update(
            conc["numeros"]
        )

        if sorteados == todos_25:

            sorteados = set()

            ciclo += 1

    faltam = sorted(
        todos_25 - sorteados
    )

    return (
        faltam if faltam else list(range(1, 26)),
        ciclo
    )


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


# ======================================================
# MEMÓRIA REAL (NOVA + FALLBACK)
# ======================================================

def buscar_memoria_real(
    supabase,
    estrutura
):

    # -----------------------------
    # 1. MATCH EXATO (modelo novo)
    # -----------------------------
    exato = supabase.table(
        "memoria_cenarios"
    ).select(
        "*"
    ).eq(
        "soma_faixa",
        estrutura["soma_faixa"]
    ).eq(
        "pares",
        estrutura["pares"]
    ).eq(
        "primos",
        estrutura["primos"]
    ).eq(
        "hash_estrutura",
        estrutura["hash_estrutura"]
    ).limit(
        1
    ).execute()

    if exato.data:
        return exato.data[0]

    # -----------------------------
    # 2. FALLBACK (modelo híbrido)
    # -----------------------------
    similares = supabase.table(
        "memoria_cenarios"
    ).select(
        "*"
    ).eq(
        "soma_faixa",
        estrutura["soma_faixa"]
    ).eq(
        "pares",
        estrutura["pares"]
    ).eq(
        "primos",
        estrutura["primos"]
    ).execute()

    if not similares.data:
        return None

    melhor = None

    menor_diff = 999

    for item in similares.data:

        linhas_db = item.get(
            "linhas",
            []
        )

        if not linhas_db:
            continue

        diff = sum(
            abs(a - b)
            for a, b in zip(
                linhas_db,
                estrutura["linhas"]
            )
        )

        if diff < menor_diff:

            menor_diff = diff

            melhor = item

    return melhor


# Compatibilidade com scripts antigos
buscar_cenario_similar = buscar_memoria_real


def ajustar_por_memoria(
    df,
    memoria
):

    if not memoria:

        print(
            "🧠 Novo cenário "
            "(sem histórico)"
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

    print(
        f"🧠 Memória Ativa | "
        f"Score Real: {score_real:.2f} | "
        f"Testado: {vezes}x"
    )

    if score_real >= 5:

        print(
            "🔥 Alta performance "
            "(+15%)"
        )

        df["score"] *= 1.15

    elif score_real >= 1:

        print(
            "📈 Cenário consistente "
            "(+5%)"
        )

        df["score"] *= 1.05

    elif vezes >= 5 and score_real == 0:

        print(
            "❄️ Cenário improdutivo "
            "(-15%)"
        )

        df["score"] *= 0.85

    return df


# ======================================================
# MAIN
# ======================================================

def main():

    supabase = get_supabase()

    print(
        "🚀 [v4.3-STABLE] "
        "Processamento Inteligente"
    )

    try:

        historico = carregar_historico()

        ultimo = historico[-1]

        concurso = ultimo["concurso"]
        data = ultimo["data"]
        dezenas = ultimo["numeros"]

        print(
            f"📌 Concurso {concurso} "
            f"| Data {data}"
        )

        df = obter_estatisticas_com_score()

        df.loc[
            df["numero"].isin(dezenas),
            "atraso"
        ] = 0

        df["tendencia"] = df[
            "numero"
        ].apply(
            lambda n:
            calcular_tendencia(
                historico,
                n
            )
        )

        # Normalização
        df["freq_norm"] = normalizar(
            df["frequencia"]
        )

        df["atraso_norm"] = (
            1 -
            normalizar(
                df["atraso"]
            )
        )

        df["tendencia_norm"] = normalizar(
            df["tendencia"]
        )

        df["score_norm"] = normalizar(
            df["score"]
        )

        # Score base
        df["score"] = (

            df["freq_norm"] * 0.35 +

            df["tendencia_norm"] * 0.30 +

            df["atraso_norm"] * 0.20 +

            df["score_norm"] * 0.15
        )

        # Memória
        est = extrair_estrutura(
            dezenas
        )

        memoria = buscar_memoria_real(
            supabase,
            est
        )

        df = ajustar_por_memoria(
            df,
            memoria
        )

        # Upsert memória
        payload_memoria = {
            "soma_faixa": est["soma_faixa"],
            "pares": est["pares"],
            "primos": est["primos"],

            "linhas": est["linhas"],
            "hash_estrutura": est["hash_estrutura"],

            "ultima_aparicao": data,
            "updated_at": datetime.now().isoformat()
        }

        supabase.table(
            "memoria_cenarios"
        ).upsert(
            payload_memoria,
            on_conflict="soma_faixa,pares,primos,hash_estrutura"
        ).execute()

        print(
            "✅ Memória atualizada"
        )

        # Regimes
        faltantes, ciclo = calcular_ciclo_historico_completo(
            historico
        )

        media_score = df[
            df["numero"].isin(
                dezenas
            )
        ]["score"].mean()

        regime = "NEUTRO"

        if media_score > 0.55:
            regime = "EXPANSAO_QUENTES"

        elif media_score < 0.45:
            regime = "CONTRACAO_FRIAS"

        check = supabase.table(
            "memoria_regimes"
        ).select(
            "id"
        ).eq(
            "concurso",
            int(concurso)
        ).execute()

        if not check.data:

            payload_regime = {
                "data_referencia": data,
                "concurso": int(concurso),

                "numero_ciclo": int(ciclo),

                "tipo_regime": regime,

                "score_global": float(
                    media_score
                ),

                "media_soma": float(
                    sum(dezenas)
                ),

                "media_pares": int(
                    est["pares"]
                )
            }

            supabase.table(
                "memoria_regimes"
            ).insert(
                payload_regime
            ).execute()

            print(
                f"📡 Regime salvo: "
                f"{regime}"
            )

        else:

            print(
                f"ℹ️ Concurso "
                f"{concurso} já existe"
            )

        print(
            "✅ Estatísticas prontas"
        )

        print(
            f"🎯 Ciclo {ciclo}"
        )

    except Exception as e:

        print(
            f"❌ Erro crítico: {e}"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()

