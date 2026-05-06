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
    est = extrair_estrutura(nums)
    peso = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}.get(acertos, 0)

    # Busca registro atual para média móvel
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
    print("🏁 Conferindo Resultados e Atualizando Memória...")

    # 1. Busca resultados oficiais recentes
    oficiais_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    resultados = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. Busca palpites pendentes
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if not pendentes:
        print("⚠️ Sem palpites pendentes.")
        return

    for p in pendentes:
        conc = int(str(p["concurso_referencia"]).strip())
        if conc not in resultados: continue

        nums = parse_numeros(p["numeros"])
        acertos = len(set(nums) & resultados[conc])
        
        # Grava acertos no palpite
        supabase.table("palpites_validos").update({
            "acertos": acertos,
            "processado": True,
            "conferido": True
        }).eq("id", p["id"]).execute()

        # ALIMENTA A MEMÓRIA ESTRUTURAL
        atualizar_memoria_com_acerto(supabase, p, acertos)
        print(f"✅ Palpite {p['id']} conferido: {acertos} acertos. Memória atualizada.")

if __name__ == "__main__":
    main()


