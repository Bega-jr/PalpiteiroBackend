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
    
    peso = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}.get(acertos, 0)

    res = supabase.table("memoria_cenarios").select("*") \
        .eq("soma_faixa", est["soma_faixa"]) \
        .eq("pares", est["pares"]) \
        .eq("primos", est["primos"]) \
        .execute()

    if res.data:
        mem = res.data[0]
        vezes = mem.get("vezes_gerado", 0) + 1
        update_data = {
            "vezes_gerado": vezes,
            "score_medio_real": (float(mem.get("score_medio_real", 0)) + peso) / 2
        }
        if acertos >= 11:
            col = f"acertos_{acertos}"
            update_data[col] = mem.get(col, 0) + 1
        
        supabase.table("memoria_cenarios").update(update_data).eq("id", mem["id"]).execute()

def main():
    supabase = get_supabase()
    print("🏁 [v2.0] Conferência Total e Sincronização de Resultados...")

    # 1. Carrega resultados oficiais (últimos 500)
    oficiais_db = supabase.table("lotofacil_concursos") \
        .select("concurso,dezenas") \
        .order("concurso", desc=True) \
        .limit(500).execute().data
    resultados_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais_db}

    # 2. CONFERÊNCIA: Processa apenas o que ainda não foi conferido
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} novos palpites...")
        for p in pendentes:
            conc_ref = int(str(p["concurso_referencia"]).strip())
            if conc_ref not in resultados_map: continue

            nums = parse_numeros(p["numeros"])
            acertos = len(set(nums) & resultados_map[conc_ref])
            
            # Atualiza palpite individual
            supabase.table("palpites_validos").update({
                "acertos": acertos, "processado": True, "conferido": True
            }).eq("id", p["id"]).execute()

            # Alimenta Memória
            atualizar_memoria_com_acerto(supabase, p, acertos)
        print("✅ Conferência individual concluída.")
    else:
        print("ℹ️ Sem novos palpites para conferir individualmente.")

    # 3. SINCRONIZAÇÃO FORÇADA: Reconstroi a tabela de resultados consolidados
    # Isso garante que a tabela 'palpites_resultados_reais' esteja sempre correta
    print("📊 Sincronizando tabela de resultados consolidados...")
    
    # Busca TODOS os palpites que já foram conferidos (independente de quando)
    todos_conferidos = supabase.table("palpites_validos") \
        .select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos") \
        .not_.is_("acertos", "null") \
        .execute().data

    consolidado = {}
    for p in todos_conferidos:
        conc = p["concurso_referencia"]
        tipo = p.get("tipo") or "estatistico"
        versao = p.get("versao_gerador") or "legacy"
        acertos = p["acertos"]
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
            peso = {11:1, 12:2, 13:5, 14:10, 15:15}.get(acertos, 0)
            ref["score_ponderado"] += float(peso)

    # 4. Upsert em massa dos consolidados
    for chave, payload in consolidado.items():
        try:
            supabase.table("palpites_resultados_reais") \
                .upsert(payload, on_conflict="concurso_inicio,concurso_fim,tipo_palpite,versao_gerador") \
                .execute()
        except Exception as e:
            print(f"⚠️ Erro ao sincronizar resumo do concurso {chave[0]}: {e}")

    print(f"🚀 Sucesso! {len(consolidado)} grupos de resultados sincronizados.")

if __name__ == "__main__":
    main()



