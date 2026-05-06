import sys
import json
from pathlib import Path

# Configuração de diretório
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

def parse_numeros(valor):
    if not valor:
        return None
    try:
        if isinstance(valor, list):
            return [int(x) for x in valor]
        if isinstance(valor, str):
            parsed = json.loads(valor)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                return [int(x) for x in parsed]
    except Exception:
        return None
    return None

def peso_acerto(acertos):
    pesos = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}
    return pesos.get(acertos, 0)

def buscar_resultados_oficiais(supabase):
    print("📊 Carregando resultados oficiais...")
    rows = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .execute()
        .data
    )
    resultados = {}
    for row in rows:
        try:
            concurso = int(row["concurso"])
            dezenas = parse_numeros(row.get("dezenas"))
            if dezenas and len(dezenas) == 15:
                resultados[concurso] = set(dezenas)
        except:
            continue
    print(f"✅ {len(resultados)} concursos oficiais carregados.")
    return resultados

def main():
    supabase = get_supabase()
    print("🏁 Iniciando Processamento de Resultados Consolidados...")

    resultados_oficiais = buscar_resultados_oficiais(supabase)

    # Busca todos os palpites marcados como não processados
    print("🔍 Buscando palpites pendentes...")
    palpites = (
        supabase
        .table("palpites_validos")
        .select("id, concurso_referencia, numeros, data_referencia, tipo, versao_gerador")
        .eq("processado", False)
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nada para processar. Todos os palpites já estão marcados como processados.")
        return

    print(f"📌 {len(palpites)} palpites encontrados para processar.")

    # DICIONÁRIO DE AGRUPAMENTO: {(concurso, tipo, versao): payload}
    consolidado = {}
    ids_para_marcar_como_concluidos = []

    for p in palpites:
        concurso = int(p["concurso_referencia"])
        
        # Só processa se o resultado já saiu
        if concurso not in resultados_oficiais:
            continue

        numeros = parse_numeros(p["numeros"])
        if not numeros:
            continue

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

        # Acumula os dados
        ref = consolidado[chave]
        ref["qtd_palpites"] += 1
        ref["score_ponderado"] += float(peso)
        
        if acertos >= 11:
            ref[f"acertos_{acertos}"] += 1
            ref["eficiencia"] += 1
            if acertos >= 12:
                ref[f"taxa_{acertos}"] = ref[f"acertos_{acertos}"]

        # Guardamos o ID para marcar como processado depois
        ids_para_marcar_como_concluidos.append(p["id"])

    # --- INSERÇÃO DOS DADOS CONSOLIDADOS ---
    print(f"📤 Enviando {len(consolidado)} grupos para 'palpites_resultados_reais'...")
    grupos_salvos = 0
    for chave, payload in consolidado.items():
        try:
            supabase.table("palpites_resultados_reais").insert(payload).execute()
            grupos_salvos += 1
        except Exception as e:
            if "23505" in str(e):
                print(f"ℹ️ Grupo {chave} já existia no banco. Ignorado.")
            else:
                print(f"❌ Erro ao salvar grupo {chave}: {e}")

    # --- ATUALIZAÇÃO DOS PALPITES ORIGINAIS EM LOTES ---
    if ids_para_marcar_como_concluidos:
        total = len(ids_para_marcar_como_concluidos)
        print(f"🧹 Marcando {total} palpites como processados em lotes...")
        
        lote_size = 200
        for i in range(0, total, lote_size):
            lote = ids_para_marcar_como_concluidos[i : i + lote_size]
            try:
                supabase.table("palpites_validos") \
                    .update({"processado": True, "conferido": True}) \
                    .in_("id", lote) \
                    .execute()
                print(f"   ✅ Lote {i//lote_size + 1} finalizado ({min(i + lote_size, total)}/{total})")
            except Exception as e:
                print(f"   ❌ Erro no lote {i//lote_size + 1}: {e}")

    print(f"\n🚀 Fim do Processo. {grupos_salvos} novos grupos criados.")

if __name__ == "__main__":
    main()


