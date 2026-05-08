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
    print("🏁 [v2.9] Sincronização por Substituição (Foco no Concurso)...")

    # 1. Resultados oficiais
    oficiais_db = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    resultados_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. Conferência pendente
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} novos palpites...")
        for p in pendentes:
            conc_ref = int(str(p["concurso_referencia"]).strip())
            if conc_ref not in resultados_map: continue
            nums = parse_numeros(p["numeros"])
            acertos = len(set(nums) & resultados_map[conc_ref])
            supabase.table("palpites_validos").update({"acertos": acertos, "processado": True, "conferido": True}).eq("id", p["id"]).execute()

    # 3. Consolidação (Cada concurso/tipo/versão gera apenas 1 linha)
    print("📊 Agrupando registros por concurso...")
    todos = supabase.table("palpites_validos").select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos").not_.is_("acertos", "null").execute().data

    consolidado = {}
    for p in todos:
        conc = int(p["concurso_referencia"])
        tipo = (p.get("tipo") or "estatistico").strip()
        versao = (p.get("versao_gerador") or "legacy").strip()
        
        chave = (conc, tipo, versao)

        if chave not in consolidado:
            # Pegamos apenas a parte YYYY-MM-DD da data para evitar erros de timestamp
            data_limpa = str(p["data_referencia"]).split(' ')[0]
            consolidado[chave] = {
                "data_referencia": data_limpa,
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

    # 4. Sincronização: Deletar Antigo + Inserir Novo (Evita erro 23505)
    print(f"🚀 Sincronizando {len(consolidado)} grupos...")
    for payload in consolidado.values():
        try:
            # Remove qualquer registro existente para este concurso/tipo/versão
            # Isso mata o problema da constraint 'idx_resultados_unico'
            supabase.table("palpites_resultados_reais") \
                .delete() \
                .eq("concurso_inicio", payload["concurso_inicio"]) \
                .eq("tipo_palpite", payload["tipo_palpite"]) \
                .eq("versao_gerador", payload["versao_gerador"]) \
                .execute()

            # Insere o dado fresquinho e consolidado
            supabase.table("palpites_resultados_reais").insert(payload).execute()
        except Exception as e:
            print(f"⚠️ Erro no concurso {payload['concurso_inicio']}: {e}")

    print("✅ Concluído! Tabela de resultados sincronizada sem duplicatas.")

if __name__ == "__main__":
    main()

