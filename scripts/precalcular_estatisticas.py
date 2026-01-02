from datetime import date
from app.services.estatisticas_service import obter_estatisticas_com_score
from app.core.supabase import supabase
from postgrest.exceptions import APIError


def main():
    hoje = date.today()
    print(f"📅 Pré-cálculo estatístico para {hoje}")

    try:
        # 1️⃣ Limpa estatísticas do dia (idempotente)
        supabase.table("estatisticas_numeros") \
            .delete() \
            .eq("data_referencia", hoje) \
            .execute()

        # 2️⃣ Calcula estatísticas pesadas
        df = obter_estatisticas_com_score()

        if df is None or df.empty:
            print("⚠️ Nenhum dado estatístico gerado. Abortando insert.")
            return

        # 3️⃣ Monta payload
        registros = [
            {
                "data_referencia": hoje,
                "numero": int(row["numero"]),
                "frequencia": int(row["frequencia"]),
                "atraso": int(row["atraso"]),
                "score": float(row["score"]),
            }
            for _, row in df.iterrows()
        ]

        # 4️⃣ Insere no Supabase
        supabase.table("estatisticas_numeros") \
            .insert(registros) \
            .execute()

        print(f"✅ {len(registros)} registros inseridos com sucesso")

    except APIError as e:
        print("❌ Erro Supabase:", e)
    except Exception as e:
        print("❌ Erro inesperado:", e)


if __name__ == "__main__":
    main()
