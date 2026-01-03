from datetime import date
from app.core.supabase import supabase
from app.services.estatisticas_service import obter_estatisticas_com_score

def main():
    hoje = date.today().isoformat()
    df = obter_estatisticas_com_score()

    supabase.table("estatisticas_numeros") \
        .delete() \
        .eq("data_referencia", hoje) \
        .execute()

    registros = [
        {
            "data_referencia": hoje,
            "numero": int(r.numero),
            "frequencia": int(r.frequencia),
            "atraso": int(r.atraso),
            "score": float(r.score),
        }
        for r in df.itertuples()
    ]

    supabase.table("estatisticas_numeros").insert(registros).execute()
    print("✅ Score diário salvo")

if __name__ == "__main__":
    main()
