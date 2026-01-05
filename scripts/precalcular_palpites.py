import os
import sys
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

# 1. Configura o caminho para encontrar o arquivo .env na raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# 2. Garante que a raiz do projeto esteja no PYTHONPATH para importar a 'api'
sys.path.append(str(BASE_DIR))

# 3. Importação do Supabase (agora com as variáveis de ambiente carregadas)
try:
    from api.core.supabase import supabase
except ImportError as e:
    print(f"❌ Erro ao importar o módulo 'api'. Certifique-se de estar na raiz do projeto: {e}")
    sys.exit(1)
except RuntimeError as e:
    print(f"❌ Erro de configuração: {e}")
    print("Verifique se SUPABASE_URL e SUPABASE_SERVICE_KEY estão no seu arquivo .env")
    sys.exit(1)

def gerar_estatisticas():
    # Lógica de processamento de estatísticas
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
    hoje = date.today().isoformat()
    print(f"🚀 Iniciando pré-cálculo para a data: {hoje}...")

    try:
        # Limpa dados existentes do dia para evitar duplicatas
        supabase.table("palpites_validos").delete().eq("data_referencia", hoje).execute()
        supabase.table("estatisticas_diarias").delete().eq("data_referencia", hoje).execute()

        # Processa e insere estatísticas
        estatisticas = gerar_estatisticas()
        estatisticas["data_referencia"] = hoje
        supabase.table("estatisticas_diarias").insert(estatisticas).execute()
        print("📊 Estatísticas diárias salvas.")

        # Processa e insere palpites
        lista_palpites = gerar_palpites()
        for palpite in lista_palpites:
            palpite["data_referencia"] = hoje
            supabase.table("palpites_validos").insert(palpite).execute()
        
        print(f"✅ {len(lista_palpites)} Palpites pré-calculados com sucesso no Supabase!")

    except Exception as e:
        print(f"❌ Ocorreu um erro durante a execução: {e}")

if __name__ == "__main__":
    main()
