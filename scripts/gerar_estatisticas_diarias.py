from datetime import date
from app.core.supabase import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    analisar_ciclo
)

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()

    print(f"📊 Gerando estatísticas diárias para {hoje}")

    analise = calcular_medias_recentes()
    faltantes = analisar_ciclo()

    payload = {
        "data_referencia": hoje,
        "media_soma": round(analise["soma_media"], 2),
        "media_pares": round(analise["pares_media"], 2),
        "media_impares": round(analise["impares_media"], 2),
        "media_primos": round(analise["primos_media"], 2),
        "numeros_atrasados": sorted(faltantes)
    }

    supabase.table("estatisticas_diarias_v2") \
        .delete() \
        .eq("data_referencia", hoje) \
        .execute()

    supabase.table("estatisticas_diarias_v2") \
        .insert(payload) \
        .execute()

    print("✅ Estatísticas diárias salvas")

if __name__ == "__main__":
    main()
