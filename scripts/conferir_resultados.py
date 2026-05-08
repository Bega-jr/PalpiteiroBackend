import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# ======================================================
# FUNÇÕES DE APOIO
# ======================================================
def parse_numeros(valor):
    if not valor: return None
    try:
        # Se já for lista (jsonb), retorna direto
        if isinstance(valor, list): return [int(x) for x in valor]
        # Se for string, tenta carregar como JSON
        parsed = json.loads(valor)
        return [int(x) for x in (parsed if isinstance(parsed, list) else json.loads(parsed))]
    except: return None

def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }

def atualizar_memoria_com_acerto(supabase, palpite, acertos):
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
        # Média ponderada simples
        score_antigo = float(mem.get("score_medio_real", 0))
        vezes = mem.get("vezes_gerado", 0) + 1
        novo_score = ((score_antigo * (vezes - 1)) + peso) / vezes
        
        update_data = {
            "vezes_gerado": vezes,
            "score_medio_real": round(novo_score, 4),
            "updated_at": datetime.now().isoformat()
        }
        if acertos >= 11:
            col = f"acertos_{acertos}"
            update_data[col] = mem.get(col, 0) + 1
            
        supabase.table("memoria_cenarios").update(update_data).eq("id", mem["id"]).execute()

def main():
    supabase = get_supabase()
    print("🏁 [v5.6-DEFINITIVO] Sincronização de Performance e Memória...")

    # 1. Mapa de Resultados
    oficiais = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    res_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais}

    # 2. Conferência Individual
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} palpites e atualizando cérebro...")
        for p in pendentes:
            conc_ref = int(str(p["concurso_referencia"]).strip())
            if conc_ref not in res_map: continue

            nums = parse_numeros(p["numeros"])
            acertos = len(set(nums) & res_map[conc_ref])
            
            supabase.table("palpites_validos").update({
                "acertos": acertos, "processado": True, "conferido": True
            }).eq("id", p["id"]).execute()

            atualizar_memoria_com_acerto(supabase, p, acertos)

    # 3. Consolidação (Agrupamento por Concurso + Tipo + Versão)
    print("📊 Agrupando resultados por categoria...")
    todos = supabase.table("palpites_validos").select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos").not_.is_("acertos", "null").execute().data

    consolidado = {}
    for p in todos:
        conc = int(p["concurso_referencia"])
        tipo = (p.get("tipo") or "estatistico").strip()
        versao = (p.get("versao_gerador") or "legacy").strip()
        chave = (conc, tipo, versao)

        if chave not in consolidado:
            # Proteção na data_referencia
            data_str = str(p.get("data_referencia", datetime.now().date())).split(' ')[0]
            consolidado[chave] = {
                "data_referencia": data_str,
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

    # 4. Cálculo de Eficiência
    for ref in consolidado.values():
        qtd = ref["qtd_palpites"]
        if qtd > 0:
            premiados = sum([ref.get(f"acertos_{i}", 0) for i in range(11, 16)])
            ref["eficiencia"] = str(round((premiados / qtd) * 100, 2))
            for i in range(12, 16):
                ref[f"taxa_{i}"] = str(round((ref.get(f"acertos_{i}", 0) / qtd) * 100, 2))

    # 5. Upsert Final
    items = list(consolidado.values())
    print(f"🚀 Enviando {len(items)} grupos para o banco...")
    for i in range(0, len(items), 50):
        try:
            supabase.table("palpites_resultados_reais").upsert(
                items[i:i+50], 
                on_conflict="concurso_inicio,tipo_palpite,versao_gerador"
            ).execute()
        except Exception as e:
            print(f"⚠️ Erro ao sincronizar resumo: {e}")

    print("✅ Tudo sincronizado!")

if __name__ == "__main__":
    main()

