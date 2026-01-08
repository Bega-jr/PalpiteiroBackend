from datetime import date
from collections import Counter, defaultdict
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# 1. BUSCAR ÚLTIMO CONCURSO (FONTE DA VERDADE)
# =========================================================
def obter_ultimo_concurso():
    resp = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,data")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        raise Exception("Nenhum concurso encontrado")

    return resp.data[0]


# =========================================================
# 2. BUSCAR HISTÓRICO COMPLETO
# =========================================================
def obter_historico():
    resp = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso")
        .execute()
    )

    if not resp.data:
        raise Exception("Histórico vazio")

    return resp.data


# =========================================================
# 3. CALCULAR ESTATÍSTICAS GERAIS
# =========================================================
def calcular_estatisticas(historico):
    total_concursos = len(historico)

    contagem = Counter()
    soma_total = 0
    pares_total = 0
    impares_total = 0
    sequencias = Counter()

    ultimo_concurso = historico[-1]["dezenas"]

    for item in historico:
        dezenas = sorted(map(int, item["dezenas"]))
        contagem.update(dezenas)

        soma_total += sum(dezenas)
        pares_total += len([d for d in dezenas if d % 2 == 0])
        impares_total += len([d for d in dezenas if d % 2 != 0])

        # sequências
        seq = 1
        for i in range(1, len(dezenas)):
            if dezenas[i] == dezenas[i - 1] + 1:
                seq += 1
                if seq >= 3:
                    sequencias[seq] += 1
            else:
                seq = 1

    frequencias = {
        n: contagem[n] / total_concursos
        for n in range(1, 26)
    }

    quentes = sorted(frequencias, key=frequencias.get, reverse=True)[:5]
    frios = sorted(frequencias, key=frequencias.get)[:5]

    atrasados = [
        n for n in range(1, 26)
        if n not in map(int, ultimo_concurso)
    ]

    return {
        "frequencias": frequencias,
        "numeros_quentes": quentes,
        "numeros_frios": frios,
        "numeros_atrasados": atrasados[:5],
        "media_soma": soma_total / total_concursos,
        "media_pares": pares_total / total_concursos,
        "media_impares": impares_total / total_concursos,
        "sequencias_comuns": [str(k) for k in sequencias if k >= 3]
    }


# =========================================================
# 4. SALVAR estatisticas_diarias_v2
# =========================================================
def salvar_estatisticas_diarias(data_ref, stats):
    supabase.table("estatisticas_diarias_v2").delete().eq(
        "data_referencia", data_ref
    ).execute()

    supabase.table("estatisticas_diarias_v2").insert({
        "data_referencia": data_ref,
        "numeros_quentes": [str(n) for n in stats["numeros_quentes"]],
        "numeros_frios": [str(n) for n in stats["numeros_frios"]],
        "numeros_atrasados": [str(n) for n in stats["numeros_atrasados"]],
        "media_soma": round(stats["media_soma"], 2),
        "media_pares": round(stats["media_pares"], 2),
        "media_impares": round(stats["media_impares"], 2),
        "sequencias_comuns": stats["sequencias_comuns"],
    }).execute()


# =========================================================
# 5. SALVAR estatisticas_numeros (SCORE)
# =========================================================
def salvar_estatisticas_numeros(data_ref, frequencias):
    supabase.table("estatisticas_numeros").delete().eq(
        "data_referencia", data_ref
    ).execute()

    payload = [
        {
            "data_referencia": data_ref,
            "numero": str(numero),
            "score": round(score, 6),
        }
        for numero, score in frequencias.items()
    ]

    supabase.table("estatisticas_numeros").insert(payload).execute()


# =========================================================
# 6. EXECUÇÃO PRINCIPAL
# =========================================================
def main():
    ultimo = obter_ultimo_concurso()
    data_ref = ultimo["data"]

    historico = obter_historico()
    stats = calcular_estatisticas(historico)

    salvar_estatisticas_diarias(data_ref, stats)
    salvar_estatisticas_numeros(data_ref, stats["frequencias"])

    print(f"✔ Estatísticas atualizadas com base no concurso {ultimo['concurso']} ({data_ref})")


if __name__ == "__main__":
    main()

