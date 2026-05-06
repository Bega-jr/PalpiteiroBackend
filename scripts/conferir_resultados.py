import sys
import json
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

def parse_numeros(valor):
    if not valor: return None
    try:
        if isinstance(valor, list): return [int(x) for x in valor]
        if isinstance(valor, str):
            parsed = json.loads(valor)
            if isinstance(parsed, str): parsed = json.loads(parsed)
            if isinstance(parsed, list): return [int(x) for x in parsed]
    except: return None
    return None

def peso_acerto(acertos):
    pesos = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}
    return pesos.get(acertos, 0)

def buscar_resultados_oficiais(supabase):
    rows = supabase.table("lotofacil_concursos").select("concurso,dezenas").execute().data
    resultados = {}
    for row in rows:
        dezenas = parse_numeros(row.get("dezenas"))
        if dezenas and len(dezenas) == 15:
            resultados[int(row["concurso"])] = set(dezenas)
    return resultados

def main():
    supabase = get_supabase()
    print("🏁 Iniciando Consolidação de Resultados Reais...")

    resultados_oficiais = buscar_resultados_oficiais(supabase)
    
    # Busca palpites não processados
    palpites = supabase.table("palpites_validos").select("*").eq("processado", False).execute().data
    
    if not palpites:
        print("⚠️ Nada para processar.")
        return

    # Dicionário para agrupar: (concurso, tipo, versao)
    consolidado = {}

    for p in palpites:
        concurso = int(p["concurso_referencia"])
        
        # Só processa se o resultado oficial já existir
        if concurso not in resultados_oficiais:
            continue

        numeros = parse_numeros(p["numeros"])
        if not numeros: continue

        tipo = p.get("tipo") or "estatistico"
        versao = p.get("versao_gerador") or "legacy"
        chave = (concurso, tipo, versao)

        # Cálculo de acertos
        oficiais = resultados_oficiais[concurso]
        acertos = len(set(numeros) & oficiais)
        peso = peso_acerto(acertos)

        if chave not in consolidado:
            consolidado[chave] = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": concurso,
                "concurso_fim": concurso,
                "total_concursos": 1,
                "tipo_palpite": tipo,
                "versao_gerador": versao,
                "qtd_palpites": 0,
                "acertos_11": 0, "acertos_12": 0, "acertos_13": 0, "acertos_14": 0, "acertos_15": 0,
                "score_ponderado": 0.0,
                "eficiencia": 0,
                "taxa_15": 0, "taxa_14": 0, "taxa_13": 0, "taxa_12": 0
            }

        # Acumula os dados no balde correspondente
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        ref["score_ponderado"] += float(peso)
        
        if acertos >= 11:
            ref[f"acertos_{acertos}"] += 1
            ref["eficiencia"] += 1
            # Atualiza as taxas (contagem simples de ocorrências)
            if acertos >= 12: ref[f"taxa_{acertos}"] = ref[f"acertos_{acertos}"]

    # INSERÇÃO NO BANCO
    sucesso_count = 0
    for chave, payload in consolidado.items():
        try:
            # Tenta inserir o consolidado
            supabase.table("palpites_resultados_reais").insert(payload).execute()
            sucesso_count += 1
            print(f"✅ Salvo: Concurso {chave[0]} | Tipo: {chave[1]} | Qtd: {payload['qtd_palpites']}")
        except Exception as e:
            if "23505" in str(e):
                print(f"ℹ️ Já existe consolidado para {chave}, ignorando insert.")
            else:
                print(f"❌ Erro ao inserir {chave}: {e}")

    # MARCA COMO PROCESSADO NA ORIGEM
    if sucesso_count > 0:
        ids_finalizados = [p["id"] for p in palpites if int(p["concurso_referencia"]) in resultados_oficiais]
        # Atualiza em lotes para evitar erro de URL muito longa
        for i in range(0, len(ids_finalizados), 100):
            lote = ids_finalizados[i:i+100]
            supabase.table("palpites_validos").update({"processado": True, "conferido": True}).in_("id", lote).execute()

    print(f"\n🚀 Finalizado. {sucesso_count} grupos consolidados criados.")

if __name__ == "__main__":
    main()


