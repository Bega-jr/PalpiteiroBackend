from datetime import date
from api.core.supabase import supabase

def gerar_estatisticas():
    # 🔴 AQUI entra sua lógica pesada atual
    return {
        "numeros_mais_sorteados": [10, 11, 20, 25],
        "numeros_menos_sorteados": [2, 3, 7],
        "numeros_atrasados": [17, 4],
        "moda_recente": [10, 20],
        "media_soma": 195.2,
        "media_pares": 7.1,
        "sequencias_comuns": [3, 4]
    }

def gerar_palpites():
    palpites = []
    for i in range(1, 8):
        palpites.append({
            "indice_palpite": i,
            "numeros": sorted([1, 2, 3, 5, 7, 9, 10, 11, 13, 14, 15, 18, 20, 24, 25]),
            "soma_total": 195,
            "pares": 7,
            "impares": 8,
            "qtd_sequencias": 3,
            "usa_mais_sorteados": True,
            "usa_menos_sorteados": False,
            "metricas": {"score": 0.87},
            "filtros_aplicados": {
                "soma": "ok",
                "pares_impares": "ok",
                "sequencias": "ok"
            }
        })
    return palpites

def main():
    hoje = date.today()

    # Limpa dados do dia
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).execute()
    supabase.table("estatisticas_diarias").delete().eq("data_referencia", hoje).execute()

    estatisticas = gerar_estatisticas()
    estatisticas["data_referencia"] = hoje
    supabase.table("estatisticas_diarias").insert(estatisticas).execute()

    for palpite in gerar_palpites():
        palpite["data_referencia"] = hoje
        supabase.table("palpites_validos").insert(palpite).execute()

    print("✅ Palpites pré-calculados com sucesso")

if __name__ == "__main__":
    main()
