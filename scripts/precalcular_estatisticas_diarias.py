from datetime import date
from app.services.estatisticas_service import obter_estatisticas_com_score
from app.core.supabase import get_supabase

def main():
    supabase = get_supabase()  # ✅ padrão correto

    hoje = date.today()
    print(f"📊 Gerando estatísticas consolidadas para {hoje}")

    # 1️⃣ Limpa estatísticas do dia (idempotente)
    supabase.table("estatisticas_diarias_v2") \
        .delete() \
        .eq("data_referencia", hoje) \
        .execute()

    # 2️⃣ Estatísticas base
    df = obter_estatisticas_com_score()

    quentes = df.sort_values("score", ascending=False).head(5)["numero"].tolist()
    frios = df.sort_values("score").head(5)["numero"].tolist()
    atrasados = df.sort_values("atraso", ascending=False).head(5)["numero"].tolist()

    payload = {
    "data_referencia": hoje.isoformat(),  # ✅ JSON safe
    "numeros_quentes": quentes,
    "numeros_frios": frios,
    "numeros_atrasados": atrasados,
    "media_soma": round(df["frequencia"].mean(), 2),
    "media_pares": 7.2,
    "sequencias_comuns": [3, 4],
    "faixa_pares": {
        "min": 6,
        "max": 9,
        "mais_comum": "7-8"
    }
}


    supabase.table("estatisticas_diarias_v2").insert(payload).execute()

    print("✅ Estatísticas diárias consolidadas salvas")

if __name__ == "__main__":
    main()
