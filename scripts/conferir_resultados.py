import sys
import json
import pytz
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# Importa sua função de extrair estrutura do script diário
from scripts.processamento_diario_lotofacil import extrair_estrutura

def parse_numeros(valor):
    if not valor: return None
    try:
        if isinstance(valor, list): return [int(x) for x in valor]
        parsed = json.loads(valor)
        if isinstance(parsed, str): parsed = json.loads(parsed)
        return [int(x) for x in parsed]
    except: return None

def atualizar_memoria_com_acerto(supabase, palpite, acertos):
    """Atualiza a performance do cenário na tabela de memória."""
    nums = parse_numeros(palpite["numeros"])
    if not nums: return
    est = extrair_estrutura(nums)
    
    # Peso ponderado para o score_medio_real
    peso = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}.get(acertos, 0)

    # Busca registro atual na memória
    res = supabase.table("memoria_cenarios").select("*") \
        .eq("soma_faixa", est["soma_faixa"]) \
        .eq("pares", est["pares"]) \
        .eq("primos", est["primos"]) \
        .execute()

    if res.data:
        # Pega o primeiro item da lista de retorno
        mem = res.data[0]
        
        # Cálculo de média móvel simples para o score real
        vezes = mem.get("vezes_gerado", 0) + 1
        update_data = {
            "vezes_gerado": vezes,
            "score_medio_real": (float(mem.get("score_medio_real", 0)) + peso) / 2
        }
        
        # Incrementa contador de premiações específicas se houver
        if acertos >= 11:
            col = f"acertos_{acertos}"
            update_data[col] = mem.get(col, 0) + 1
        
        supabase.table("memoria_cenarios").update(update_data).eq("id", mem["id"]).execute()

def main():
    supabase = get_supabase()
    print("🏁 Conferindo Resultados, Atualizando Memória e Consolidando...")

    # 1. Busca resultados oficiais recentes (últimos 500)
    oficiais_db = supabase.table("lotofacil_concursos") \
        .select("concurso,dezenas") \
        .order("concurso", desc=True) \
        .limit(500).execute().data
        
    resultados = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. Busca palpites pendentes (processado = false)
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if not pendentes:
        print("⚠️ Sem palpites pendentes para conferir.")
        return

    print(f"🔍 Processando {len(pendentes)} palpites...")

    # Dicionário para consolidar os resultados para a tabela 'palpites_resultados_reais'
    consolidado = {}

    for p in pendentes:
        conc_ref = int(str(p["concurso_referencia"]).strip())
        
        # Pula se o resultado oficial ainda não estiver no banco
        if conc_ref not in resultados: 
            continue

        nums = parse_numeros(p["numeros"])
        acertos = len(set(nums) & resultados[conc_ref])
        
        # --- Lógica de Consolidação para 'palpites_resultados_reais' ---
        tipo = p.get("tipo") or "estatistico"
        versao = p.get("versao_gerador") or "legacy"
        chave = (conc_ref, tipo, versao)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": conc_ref, 
                "concurso_fim": conc_ref,
                "tipo_palpite": tipo, 
                "versao_gerador": versao,
                "qtd_palpites": 0, 
                "total_concursos": 1,
                "acertos_11": 0, "acertos_12": 0, "acertos_13": 0, "acertos_14": 0, "acertos_15": 0,
                "score_ponderado": 0.0
            }
        
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        
        if acertos >= 11:
            ref[f"acertos_{acertos}"] += 1
            peso_acerto = {11:1, 12:2, 13:5, 14:10, 15:15}.get(acertos, 0)
            ref["score_ponderado"] += float(peso_acerto)

        # 3. Atualiza o status do palpite individual
        supabase.table("palpites_validos").update({
            "acertos": acertos,
            "processado": True,
            "conferido": True
        }).eq("id", p["id"]).execute()

        # 4. Alimenta a Memória Estrutural com a experiência deste palpite
        atualizar_memoria_com_acerto(supabase, p, acertos)
        
    print(f"✅ Conferência individual concluída.")

    # 5. Sincroniza os resultados consolidados (UPSERT para evitar duplicatas)
    print(f"📤 Sincronizando consolidados na tabela 'palpites_resultados_reais'...")
    for chave, payload in consolidado.items():
        try:
            # O upsert resolve o erro 23505 de chave duplicada
            supabase.table("palpites_resultados_reais") \
                .upsert(payload, on_conflict="concurso_inicio,concurso_fim,tipo_palpite,versao_gerador") \
                .execute()
            print(f"   📊 Consolidado OK: Conc {chave[0]} | Tipo {chave[1]} | {chave[2]}")
        except Exception as e:
            print(f"   ⚠️ Erro ao sincronizar consolidado {chave}: {e}")

    print("🚀 Fim do processo de conferência.")

if __name__ == "__main__":
    main()



