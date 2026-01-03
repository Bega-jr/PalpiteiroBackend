from datetime import date
from app.core.supabase import get_supabase

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()

    print(f"📊 Consolidando estatísticas diárias para {hoje}")

    # 1️⃣ Busca estatísticas por número já calculadas
    res = supabase.table("estatisticas_numeros") \
        .select("numero, score, atraso") \
        .eq("data_referencia", hoje) \
        .execute()

    if not res.data:
        raise Exception("Nenhuma estatística por número encontrada para hoje")

    stats = res.data

    # 2️⃣ Consolida dados
    ordenado_score = sorted(stats, key=lambda x: x["score"], reverse=True)
    ordenado_atraso = sorted(stats, key=lambda x: x["atraso"], reverse=True)

    numeros_quentes = [x["numero"] for x in ordenado_score[:5]]
    numeros_frios = [x["numero"] for x in ordenado_score[-5:]]
    numeros_atrasados = [x["numero"] for x in ordenado_atraso[:5]]

    payload = {
        "data_referencia": hoje,
        "numeros_quentes": numeros_quentes,
        "numeros_frios": numeros_frios,
        "numeros_atrasados": numeros_atrasados,
        "media_soma": None,
        "media_pares": None,
        "sequencias_comuns": None,
        "faixa_pares": None,
    }

    # 3️⃣ Idempotência
    supabase.table("estatisticas_diarias_v2") \
        .delete() \
        .eq("data_referencia", hoje) \
        .execute()

    supabase.table("estatisticas_diarias_v2") \
        .insert(payload) \
        .execute()

    print("✅ Estatísticas diárias consolidadas com sucesso")

if __name__ == "__main__":
    main()
