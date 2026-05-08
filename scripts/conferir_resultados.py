import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

def parse_numeros(valor):
    if not valor: return None
    try:
        if isinstance(valor, list): return [int(x) for x in valor]
        parsed = json.loads(valor)
        return [int(x) for x in (parsed if isinstance(parsed, list) else json.loads(parsed))]
    except: return None

def main():
    supabase = get_supabase()
    print("🏁 [v2.8] Agrupamento por Concurso (Fixo vs Estatístico)...")

    # 1. Resultados oficiais
    oficiais_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    resultados_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. Conferência individual pendente
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} novos palpites...")
        for p in pendentes:
            conc_ref = int(str(p["concurso_referencia"]).strip())
            if conc_ref not in resultados_map: continue
            nums = parse_numeros(p["numeros"])
            acertos = len(set(nums) & resultados_map[conc_ref])
            supabase.table("palpites_validos").update({"acertos": acertos, "processado": True, "conferido": True}).eq("id", p["id"]).execute()

    # 3. Consolidação BASEADA NO CONCURSO
    print("📊 Agrupando registros por concurso e tipo...")
    todos = supabase.table("palpites_validos").select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos").not_.is_("acertos", "null").execute().data

    consolidado = {}
    for p in todos:
        conc = int(p["concurso_referencia"])
        tipo = (p.get("tipo") or "estatistico").strip()
        versao = (p.get("versao_gerador") or "legacy").strip()
        
        # CHAVE: Agora focada no Concurso, Tipo e Versão
        # Isso garante que seus 6 estatísticos virem 1 linha e o fixo vire outra.
        chave = (conc, tipo, versao)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": p["data_referencia"], # Mantém a data do primeiro encontrado
                "concurso_inicio": conc, 
                "concurso_fim": conc,
                "tipo_palpite": tipo, 
                "versao_gerador": versao,
                "qtd_palpites": 0, 
                "total_concursos": 1,
                "acertos_11": 0, "acertos_12": 0, "acertos_13": 0, "acertos_14": 0, "acertos_15": 0,
                "score_ponderado": 0.0
            }
        
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        ac = p["acertos"]
        if ac >= 11:
            ref[f"acertos_{ac}"] += 1
            ref["score_ponderado"] += float({11:1, 12:2, 13:5, 14:10, 15:15}.get(ac, 0))

    # 4. Upsert (Sincronização com o banco)
    print(f"🚀 Sincronizando {len(consolidado)} grupos...")
    items = list(consolidado.values())
    for i in range(0, len(items), 60):
        batch = items[i:i+60]
        try:
            # Sincroniza usando a chave lógica de concurso e versão
            supabase.table("palpites_resultados_reais") \
                .upsert(batch, on_conflict="concurso_inicio,concurso_fim,tipo_palpite,versao_gerador") \
                .execute()
        except Exception as e:
            print(f"⚠️ Erro ao sincronizar: {e}")

    print("✅ Concluído! Os 6 estatísticos e o fixo foram consolidados separadamente.")

if __name__ == "__main__":
    main()

