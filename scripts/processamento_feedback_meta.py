import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.meta_learning_service import atualizar_meta_learning
from scripts.processamento_diario_lotofacil import carregar_historico

def avaliar_desempenho_concurso():
    supabase = get_supabase()
    
    # 1. Carrega o histórico atualizado para pegar o resultado real mais recente
    hist = carregar_historico()
    ultimo_concurso = hist[-1]
    
    concurso_real = int(ultimo_concurso["concurso"])
    numeros_sorteados = set(ultimo_concurso["numeros"]) # Set para busca O(1)
    
    print(f"🎲 Sorteio Real: Concurso {concurso_real} -> {sorted(list(numeros_sorteados))}")
    
    # 2. Busca os palpites que você gerou para este concurso específico
    rows = (
        supabase
        .table("palpites_validos")
        .select("indice_palpite, numeros, conferido")
        .eq("concurso_referencia", concurso_real)
        .execute()
        .data
    )
    
    if not rows:
        print(f"ℹ️ Nenhum palpite encontrado no banco para o concurso {concurso_real}. Ignorando feedback.")
        return

    # Evita reprocessar e aplicar viés duplo nos pesos se já foi conferido
    if all(row.get("conferido") for row in rows):
        print(f"⚠️ O concurso {concurso_real} já teve o meta-learning atualizado anteriormente.")
        return

    acertos_totais = []
    palpites_atualizados = []

    # 3. Calcula os acertos de cada palpite
    for row in rows:
        # Decodifica os números (salvos como JSON String no seu gerador)
        nums_palpite = set(json.loads(row["numeros"]))
        
        # Interseção matemática para ver quantos números bateram
        qtd_acertos = len(nums_palpite & numeros_sorteados)
        acertos_totais.append(qtd_acertos)
        
        # Prepara o payload para atualizar o status do palpite individual no banco
        palpites_atualizados.append({
            "concurso_referencia": concurso_real,
            "indice_palpite": row["indice_palpite"],
            "acertos": qtd_acertos,
            "conferido": True
        })
        
        print(f"📊 Palpite {row['indice_palpite']}º teve {qtd_acertos} acertos.")

    # 4. Calcula a média matemática de acertos do grupo (Ensemble)
    media_acertos_ensemble = sum(acertos_totais) / len(acertos_totais)
    print(f"📈 Média de acertos do Ensemble: {media_acertos_ensemble:.2f}")

    # 5. ATUALIZA O META-LEARNING (Ajusta os pesos com base nas suas faixas < 9 ou >= 11)
    atualizar_meta_learning(media_acertos_ensemble)

    # 6. Salva o resultado da conferência de cada palpite para auditoria e gráficos futuros
    # (Adicione a coluna 'acertos' do tipo integer na sua tabela 'palpites_validos' se ainda não tiver)
    try:
        supabase.table("palpites_validos").upsert(
            palpites_atualizados,
            on_conflict="concurso_referencia,indice_palpite"
        ).execute()
        print(f"✅ Status dos palpites do concurso {concurso_real} atualizados com sucesso.")
    except Exception as e:
        print(f"⚠️ Erro ao atualizar status dos palpites no banco: {e}")

if __name__ == "__main__":
    avaliar_desempenho_concurso()
