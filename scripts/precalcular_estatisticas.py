from datetime import date
from app.services.estatisticas_service import obter_estatisticas_com_score
from app.core.supabase import supabase

def main():
    hoje = date.today()

    # Limpa estatísticas do dia
    supabase.table("estatisticas_numeros") \
        .delete() \
        .eq("data_referencia", hoje) \
        .execute()

    df = obter_estatisticas_com_score()

    registros = []
    for _, row in df.iterrows():
        registros.append({
            "data_referencia": hoje,
            "numero": int(row["numero"]),
            "frequencia": int(row["frequencia"]),
            "atraso": int(row["atraso"]),
            "score": float(row["score"])
        })

    supabase.table("estatisticas_numeros").insert(registros).execute()

    print("✅ Estatísticas pré-calculadas com sucesso")

if __name__ == "__main__":
    main()
