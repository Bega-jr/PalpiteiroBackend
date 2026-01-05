import sys
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

# Config ambiente
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
sys.path.append(str(BASE_DIR))

from api.core.supabase import supabase

def gerar_estatisticas():
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
    base = [1, 2, 3, 5, 7, 9, 10, 11, 13, 14, 15, 18, 20, 24, 25]
    palpites = []

    for i in range(1, 8):
        palpites.append({
            "indice_palpite": i,
            "numeros": base,
            "soma_total": 195,
            "pares": 7,
            "impares": 8,
            "qtd_sequencias": 3,
            "metricas": {"score": 0.87},
            "tipo": "estatistico",
            "origem": "sistema"
        })

    return palpites

def main():
    hoje = date.today().isoformat()
    print(f"🚀 Pré-cálculo diário: {hoje}")

    # Limpeza
    supabase.table("palpites_validos").delete().eq("data_referencia", hoje).execute()
    supabase.table("estatisticas_diarias").delete().eq("data_referencia", hoje).execute()

    # Estatísticas
    estatisticas = gerar_estatisticas()
    estatisticas["data_referencia"] = hoje
    supabase.table("estatisticas_diarias").insert(estatisticas).execute()

    # Palpites
    for p in gerar_palpites():
        p["data_referencia"] = hoje
        supabase.table("palpites_validos").insert(p).execute()

    print("✅ Palpites e estatísticas gerados com sucesso")

if __name__ == "__main__":
    main()
