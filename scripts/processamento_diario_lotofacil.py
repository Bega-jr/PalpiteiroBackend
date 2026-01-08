from collections import Counter
from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# 1. ÚLTIMO CONCURSO (DATA DE REFERÊNCIA)
# =========================================================
def obter_ultimo_concurso():
    resp = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,data,dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        raise Exception("Nenhum concurso encontrado")

    return resp.data[0]


# =========================================================
# 2. HISTÓRICO COMPLETO
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
# 3. CALCULAR FREQUÊNCIA, ATRASO E SCORE
# =========================================================
def calcular_estatisticas_numeros(historico):
    total_concursos = len(historico)
    contagem = Counter()
    ultimo_aparecimento = {}

    for idx, item in enumerate(historico):
        dezenas = list(map(int, item["dezenas"]))
        contagem.update(dezenas)
        for d in dezenas:
            ultimo_aparecimento[d] = idx

    estatisticas = {}

    for numero in range(1, 26):
        freq_abs = contagem.get(numero, 0)
        freq_rel = freq_abs / total_concursos

        atraso = (
            total_concursos - 1 - ultimo_aparecimento[numero]
            if numero in ultimo_aparecimento
            else total_concursos
        )

        # score ponderado (frequência + atraso)
        score = round((freq_rel * 0.7) + ((1 / (atraso + 1)) * 0.3), 6)

        estatisticas[numero] = {
            "frequencia": freq_abs,
            "atraso": atraso,
            "score": score
        }

    return estatisticas


# =========================================================
# 4. SALVAR estatisticas_numeros
# =========================================================
def salvar_estatisticas_numeros(data_ref, estatisticas):
    supabase.table("estatisticas_numeros").delete().eq(
        "data_referencia", data_ref
    ).execute()

    payload = [
        {
            "data_referencia": data_ref,
            "numero": numero,
            "frequencia": dados["frequencia"],
            "atraso": dados["atraso"],
            "score": dados["score"]
        }
        for numero, dados in estatisticas.items()
    ]

    supabase.table("estatisticas_numeros").insert(payload).execute()


# =========================================================
# 5. EXECUÇÃO PRINCIPAL
# =========================================================
def main():
    ultimo = obter_ultimo_concurso()
    data_ref = ultimo["data"]

    historico = obter_historico()
    estatisticas = calcular_estatisticas_numeros(historico)

    salvar_estatisticas_numeros(data_ref, estatisticas)

    print(f"✔ estatisticas_numeros atualizada com base no concurso {ultimo['concurso']} ({data_ref})")


if __name__ == "__main__":
    main()

    main()

