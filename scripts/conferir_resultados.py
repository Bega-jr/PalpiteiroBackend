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
        if isinstance(valor, list): return [int(x) for x in valor]
        parsed = json.loads(valor)
        return [int(x) for x in (parsed if isinstance(parsed, list) else json.loads(parsed))]
    except: return None

def extrair_estrutura(nums):
    """Necessário para identificar o cenário na memória."""
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
    """ALIMENTA O CÉREBRO: Atualiza o score real para o processamento diário."""
    nums = parse_numeros(palpite["numeros"])
    if not nums: return
    
    est = extrair_estrutura(nums)
    peso = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}.get(acertos, 0)

    # Busca o cenário existente
    res = supabase.table("memoria_cenarios").select("*") \
        .eq("soma_faixa", est["soma_faixa"]) \
        .eq("pares", est["pares"]) \
        .eq("primos", est["primos"]) \
        .execute()

    if res.data:
        mem = res.data[0]
        # Cálculo de média móvel simples para o score real
        novo_score = (float(mem.get("score_medio_real", 0)) + peso) / 2 if mem.get("score_medio_real") else peso
        
        update_data = {
            "vezes_gerado": mem.get("vezes_gerado", 0) + 1,
            "score_medio_real": novo_score,
            "updated_at": datetime.now().isoformat()
        }
        
        # Incrementa contador de acertos na memória
        if acertos >= 11:
            col = f"acertos_{acertos}"
            update_data[col] = mem.get(col, 0) + 1
            
        supabase.table("memoria_cenarios").update(update_data).eq("id", mem["id"]).execute()

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    print("🏁 [v5.0-FINAL] Conferência, Memória e Eficiência...")

    # 1. Carrega resultados oficiais
    oficiais = supabase.table("lotofacil_concursos").select("concurso,dezenas").order("concurso", desc=True).limit(500).execute().data
    res_map = {int(str(r["concurso"]).strip()): set(parse_numeros(r["dezenas"])) for r in oficiais}

    # 2. Conferência Individual e Atualização de Memória
    pendentes = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if pendentes:
        print(f"🔍 Conferindo {len(pendentes)} novos palpites e alimentando memória...")
        for p in pendentes:
            conc_ref = int(str(p["concurso_referencia"]).strip())
            if conc_ref not in res_map: continue

            nums = parse_numeros(p["numeros"])
            acertos = len(set(nums) & res_map[conc_ref])
            
            # Atualiza palpite individual
            supabase.table("palpites_validos").update({
                "acertos": acertos, "processado": True, "conferido": True
            }).eq("id", p["id"]).execute()

            # ALIMENTA O SCORE REAL DA MEMÓRIA
            atualizar_memoria_com_acerto(supabase, p, acertos)
        print("✅ Memória e conferência individual concluídas.")

    # 3. Consolidação (Agrupamento para Tabela de Resultados)
    print("📊 Consolidando grupos de performance...")
    todos = supabase.table("palpites_validos").select("data_referencia, concurso_referencia, tipo, versao_gerador, acertos").not_.is_("acertos", "null").execute().data

    consolidado = {}
    for p in todos:
        conc = int(p["concurso_referencia"])
        tipo = (p.get("tipo") or "estatistico").strip()
        versao = (p.get("versao_gerador") or "legacy").strip()
        chave = (conc, tipo, versao)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": str(p["data_referencia"]).split(' ')[0],
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

    # 4. Cálculo de Eficiência e Taxas
    for ref in consolidado.values():
        qtd = ref["qtd_palpites"]
        if qtd > 0:
            premiados = sum([ref[f"acertos_{i}"] for i in range(11, 16)])
            ref["eficiencia"] = str(round((premiados / qtd) * 100, 2))
            for i in range(12, 16):
                ref[f"taxa_{i}"] = str(round((ref[f"acertos_{i}"] / qtd) * 100, 2))

    # 5. Upsert Final
    items = list(consolidado.values())
    print(f"🚀 Enviando {len(items)} registros consolidados...")
    for i in range(0, len(items), 50):
        try:
            supabase.table("palpites_resultados_reais").upsert(
                items[i:i+50], 
                on_conflict="concurso_inicio,tipo_palpite,versao_gerador"
            ).execute()
        except Exception as e:
            print(f"⚠️ Erro no lote: {e}")

    print("✅ Tudo sincronizado! Memória alimentada e Métricas calculadas.")

if __name__ == "__main__":
    main()

