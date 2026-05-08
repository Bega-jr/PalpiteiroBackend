import sys
import json
from pathlib import Path

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

def main():
    supabase = get_supabase()
    print("🏁 [v2.5] Reprocessamento Total Pós-Limpeza...")

    # 1. Carrega resultados oficiais
    oficiais_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    resultados_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. CONFERÊNCIA Individual (Garante que tudo na 'palpites_validos' tenha acertos)
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} novos palpites...")
        for p in pendentes:
            conc_ref = int(str(p["concurso_referencia"]).strip())
            if conc_ref not in resultados_map: continue
            nums = parse_numeros(p["numeros"])
            acertos = len(set(nums) & resultados_map[conc_ref])
            supabase.table("palpites_validos").update({"acertos": acertos, "processado": True, "conferido": True}).eq("id", p["id"]).execute()

    # 3. CONSOLIDAÇÃO (Lê tudo e agrupa)
    print("📊 Gerando novos consolidados...")
    todos_conferidos = supabase.table("palpites_validos").select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos").not_.is_("acertos", "null").execute().data

    consolidado = {}
    for p in todos_conferidos:
        conc = int(p["concurso_referencia"])
        tipo = (p.get("tipo") or "estatistico").strip()
        versao = (p.get("versao_gerador") or "legacy").strip()
        # Usamos apenas a parte da data YYYY-MM-DD
        data_ref = str(p["data_referencia"]).split(' ')[0]
        
        chave = (data_ref, conc, tipo, versao)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": data_ref,
                "concurso_inicio": conc, "concurso_fim": conc,
                "tipo_palpite": tipo, "versao_gerador": versao,
                "qtd_palpites": 0, "total_concursos": 1,
                "acertos_11": 0, "acertos_12": 0, "acertos_13": 0, "acertos_14": 0, "acertos_15": 0,
                "score_ponderado": 0.0
            }
        
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        ac = p["acertos"]
        if ac >= 11:
            ref[f"acertos_{ac}"] += 1
            ref["score_ponderado"] += float({11:1, 12:2, 13:5, 14:10, 15:15}.get(ac, 0))

    # 4. INSERÇÃO (Como limpamos a tabela, usamos upsert apenas por segurança)
    print(f"🚀 Inserindo {len(consolidado)} grupos...")
    items = list(consolidado.values())
    
    # Inserção em lotes de 50 para ser mais rápido
    for i in range(0, len(items), 50):
        batch = items[i:i+50]
        try:
            supabase.table("palpites_resultados_reais").upsert(batch).execute()
        except Exception as e:
            print(f"⚠️ Erro no lote: {e}")

    print("✅ Tabela reprocessada com sucesso!")

if __name__ == "__main__":
    main()

