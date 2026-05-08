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
    print("🏁 [v3.1] Consolidação por Tipo (Fixo vs Estatístico)...")

    # 1. Carrega resultados oficiais
    oficiais = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    res_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais}

    # 2. Conferência Individual
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} novos palpites...")
        for p in pendentes:
            conc = int(str(p["concurso_referencia"]).strip())
            if conc in res_map:
                acertos = len(set(parse_numeros(p["numeros"])) & res_map[conc])
                supabase.table("palpites_validos").update({"acertos": acertos, "processado": True, "conferido": True}).eq("id", p["id"]).execute()

    # 3. Consolidação em 2 grupos por dia/concurso
    print("📊 Agrupando por Tipo...")
    todos = supabase.table("palpites_validos").select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos").not_.is_("acertos", "null").execute().data

    consolidado = {}
    for p in todos:
        # Normaliza a data para YYYY-MM-DD
        data_ref = str(p["data_referencia"]).split(' ')[0]
        conc = int(p["concurso_referencia"])
        tipo = (p.get("tipo") or "estatistico").strip()
        versao = (p.get("versao_gerador") or "legacy").strip()
        
        # Chave que separa Fixo de Estatístico no mesmo dia/concurso
        chave = (data_ref, conc, tipo, versao)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": data_ref,
                "concurso_inicio": conc,
                "concurso_fim": conc,
                "tipo_palpite": tipo,
                "versao_gerador": versao,
                "qtd_palpites": 0,
                "acertos_11": 0, "acertos_12": 0, "acertos_13": 0, "acertos_14": 0, "acertos_15": 0,
                "score_ponderado": 0.0,
                "total_concursos": 1
            }
        
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        ac = p["acertos"]
        if ac >= 11:
            ref[f"acertos_{ac}"] += 1
            ref["score_ponderado"] += float({11:1, 12:2, 13:5, 14:10, 15:15}.get(ac, 0))

    # 4. Upsert (Sincronização)
    print(f"🚀 Enviando {len(consolidado)} registros consolidados...")
    items = list(consolidado.values())
    for i in range(0, len(items), 50):
        try:
            supabase.table("palpites_resultados_reais").upsert(
                items[i:i+50], 
                on_conflict="data_referencia,concurso_inicio,versao_gerador,tipo_palpite"
            ).execute()
        except Exception as e:
            print(f"⚠️ Erro ao sincronizar lote: {e}")

    print("✅ Sucesso! Agora você tem uma linha para 'fixo' e uma para 'estatistico' por concurso.")

if __name__ == "__main__":
    main()

