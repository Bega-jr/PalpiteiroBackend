from datetime import date
import json
from app.core.supabase import get_supabase
from app.services.estatisticas_service import (
    calcular_medias_recentes,
    analisar_ciclo,
    obter_estatisticas_com_score
)

def main():
    supabase = get_supabase()
    hoje = date.today().isoformat()
    
    print(f"🚀 Iniciando consolidação para: {hoje}")

    try:
        # 1️⃣ Coleta de dados
        analise_medias = calcular_medias_recentes()
        faltantes_ciclo = analisar_ciclo()
        df_scores = obter_estatisticas_com_score()

        # 2️⃣ Processar Rankings (Convertendo para String conforme seu banco)
        quentes = [str(n) for n in df_scores.sort_values("score", ascending=False).head(5)["numero"].tolist()]
        frios = [str(n) for n in df_scores.sort_values("score").head(5)["numero"].tolist()]
        # No seu banco, 'numeros_atrasados' parece ser o Top 5 de atraso, não o ciclo
        atrasados = [str(n) for n in df_scores.sort_values("atraso", ascending=False).head(5)["numero"].tolist()]

        # 3️⃣ Montar Payload (Dicionário exato das suas colunas)
        payload = {
            "data_referencia": hoje,
            "numeros_quentes": quentes,
            "numeros_frios": frios,
            "numeros_atrasados": atrasados,
            "media_soma": str(round(analise_medias["soma_media"], 1)),
            "media_pares": "7.2", # Mantendo o padrão texto do seu banco
            "sequencias_comuns": ["3", "4"],
            "faixa_pares": json.dumps({"max": 9, "min": 6, "mais_comum": "7-8"}),
            "atrasados_ranking": None # Coluna existe mas aceita null
        }

        # 4️⃣ Update no Supabase
        # Remove se já existir dado de hoje para evitar erro de duplicidade
        supabase.table("estatisticas_diarias_v2").delete().eq("data_referencia", hoje).execute()
        
        # Insere novo registro
        resultado = supabase.table("estatisticas_diarias_v2").insert(payload).execute()
        
        print(f"✅ Sucesso! Dados de {hoje} salvos na 'estatisticas_diarias_v2'.")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
