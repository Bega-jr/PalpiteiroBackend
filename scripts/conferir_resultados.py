import sys
import json
import pytz
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
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
    
    # Peso ponderado
    peso = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}.get(acertos, 0)

    res = supabase.table("memoria_cenarios").select("*") \
        .eq("soma_faixa", est["soma_faixa"]) \
        .eq("pares", est["pares"]) \
        .eq("primos", est["primos"]) \
        .execute()

    if res.data:
        mem = res.data[0]
        update_data = {
            "vezes_gerado": mem["vezes_gerado"] + 1,
            "score_medio_real": (float(mem["score_medio_real"]) + peso) / 2
        }
        if acertos >= 11:
            col = f"acertos_{acertos}"
            update_data[col] = mem.get(col, 0) + 1
        
        supabase.table("memoria_cenarios").update(update_data).eq("id", mem["id"]).execute()

def main():
    supabase = get_supabase()
    print("🏁 Conferindo Resultados, Atualizando Memória e Consolidando...")

    # 1. Busca resultados oficiais recentes
    oficiais_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    resultados = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. Busca palpites pendentes
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if not pendentes:
        print("⚠️ Sem palpites pendentes.")
        return

    # Dicionário para consolidar os resultados para a tabela 'palpites_resultados_reais'
    consolidado = {}

    for p in pendentes:
        conc = int(str(p["concurso_referencia"]).strip())
        if conc not in resultados: continue

        nums = parse_numeros(p["numeros"])
        acertos = len(set(nums) & resultados[conc])
        
        # --- Lógica de Consolidação (Para a tabela palpites_resultados_reais) ---
        tipo = p.get("tipo") or "estatistico"
        versao = p.get("versao_gerador") or "legacy"
        chave = (conc, tipo, versao)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": conc, "concurso_fim": conc,
                "tipo_palpite": tipo, "versao_gerador": versao,
                "qtd_palpites": 0, "total_concursos": 1,
                "acertos_11": 0, "acertos_12": 0, "acertos_13": 0, "acertos_14": 0, "acertos_15": 0,
                "score_ponderado": 0.0
            }
        
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        if acertos >= 11:
            ref[f"acertos_{acertos}"] += 1
            ref["score_ponderado"] += float({11:1, 12:2, 13:5, 14:10, 15:15}.get(acertos, 0))

        # 3. Atualiza o palpite individual
        supabase.table("palpites_validos").update({
            "acertos": acertos,
            "processado": True,
            "conferido": True
        }).eq("id", p["id"]).execute()

        # 4. Alimenta a Memória
        atualizar_memoria_com_acerto(supabase, p, acertos)
        print(f"✅ Palpite {p['id']} (Conc {conc}) conferido: {acertos} acertos.")

    # 5. Salva os resultados consolidados na tabela 'palpites_resultados_reais'
    for chave, payload in consolidado.items():
        try:
            supabase.table("palpites_resultados_reais").insert(payload).execute()
            print(f"📊 Consolidado salvo para {chave[1]} - Concurso {chave[0]}")
        except Exception as e:
            print(f"⚠️ Erro ao salvar consolidado {chave}: {e}")

if __name__ == "__main__":
    main()


