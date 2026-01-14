import sys
import json
from pathlib import Path
from datetime import datetime
import random

# -----------------------------------
# Setup base
# -----------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# -----------------------------------
# Parâmetros
# -----------------------------------
QTD_ESTATISTICOS = 26
VERSAO_GERADOR = "v1.1"
MAX_TENTATIVAS = 200

# -----------------------------------
# Funções auxiliares
# -----------------------------------
def gerar_palpite_base(numeros_base, qtd=15):
    return sorted(random.sample(numeros_base, qtd))


def calcular_metricas(numeros):
    pares = sum(1 for n in numeros if n % 2 == 0)
    impares = 15 - pares
    soma = sum(numeros)
    return pares, impares, soma


def palpite_valido(numeros):
    pares, impares, soma = calcular_metricas(numeros)

    # Soma
    if not (170 <= soma <= 210):
        return False

    # Pares / Ímpares
    if not (6 <= pares <= 9):
        return False

    # Sequências consecutivas
    seq = 1
    max_seq = 1
    for i in range(1, len(numeros)):
        if numeros[i] == numeros[i - 1] + 1:
            seq += 1
            max_seq = max(max_seq, seq)
        else:
            seq = 1

    if max_seq > 4:
        return False

    # Presença em todas as faixas
    faixas = [
        any(1 <= n <= 5 for n in numeros),
        any(6 <= n <= 10 for n in numeros),
        any(11 <= n <= 15 for n in numeros),
        any(16 <= n <= 20 for n in numeros),
        any(21 <= n <= 25 for n in numeros),
    ]

    if not all(faixas):
        return False

    return True


def gerar_palpite_validado(base):
    for _ in range(MAX_TENTATIVAS):
        numeros = gerar_palpite_base(base)
        if palpite_valido(numeros):
            return numeros
    return None


# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerando palpites para {hoje}")

    # 1️⃣ Estatísticas diárias
    estat = (
        supabase
        .table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not estat.data:
        print("❌ Estatísticas diárias não encontradas.")
        return

    estat = estat.data[0]

    # 2️⃣ Estatísticas por número
    numeros_stats = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, score")
        .eq("data_referencia", estat["data_referencia"])
        .order("score", desc=True)
        .execute()
    )

    if not numeros_stats.data:
        print("❌ Estatísticas por número não encontradas.")
        return

    numeros_ordenados = [n["numero"] for n in numeros_stats.data]

    # 3️⃣ Limpa palpites do dia
    supabase.table("palpites_validos") \
        .delete() \
        .eq("data_referencia", estat["data_referencia"]) \
        .execute()

    # ==========================
    # PALPITE FIXO
    # ==========================
    fixo_base = numeros_ordenados[:20]
    fixo_numeros = gerar_palpite_validado(fixo_base)

    if not fixo_numeros:
        print("❌ Falha ao gerar palpite fixo válido.")
        return

    pares, impares, soma = calcular_metricas(fixo_numeros)

    palpite_fixo = {
        "data_referencia": estat["data_referencia"],
        "tipo": "fixo",
        "indice_palpite": 0,
        "numeros": json.dumps(fixo_numeros),
        "pares": pares,
        "impares": impares,
        "metricas": json.dumps({
            "origem": "top_20_score",
            "soma": soma,
            "versao": VERSAO_GERADOR
        })
    }

    supabase.table("palpites_validos").insert(palpite_fixo).execute()
    print("✅ Palpite fixo validado e salvo")

    # ==========================
    # PALPITES ESTATÍSTICOS
    # ==========================
    palpites_est = []

    for i in range(QTD_ESTATISTICOS):
        base = numeros_ordenados[:15 + (i % 10)]
        numeros = gerar_palpite_validado(base)

        if not numeros:
            print(f"⚠️ Palpite estatístico {i+1} descartado (raro)")
            continue

        pares, impares, soma = calcular_metricas(numeros)

        palpites_est.append({
            "data_referencia": estat["data_referencia"],
            "tipo": "estatistico",
            "indice_palpite": i + 1,
            "numeros": json.dumps(numeros),
            "pares": pares,
            "impares": impares,
            "metricas": json.dumps({
                "base": f"top_{len(base)}",
                "soma": soma,
                "versao": VERSAO_GERADOR
            })
        })

    if palpites_est:
        supabase.table("palpites_validos").insert(palpites_est).execute()

    print(f"✅ {len(palpites_est)} palpites estatísticos válidos salvos")
    print("🎯 Processo finalizado com segurança")

if __name__ == "__main__":
    main()

