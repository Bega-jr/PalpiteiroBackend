import sys
import json
from pathlib import Path

# Configuração de diretório
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

def parse_numeros(valor):
    """Converte strings, listas ou JSONs de números em uma lista de inteiros."""
    if not valor:
        return None
    try:
        if isinstance(valor, list):
            return [int(x) for x in valor]
        if isinstance(valor, str):
            # Limpa aspas extras se houver e carrega JSON
            parsed = json.loads(valor)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                return [int(x) for x in parsed]
    except Exception:
        return None
    return None

def peso_acerto(acertos):
    """Define a pontuação ponderada por acerto."""
    pesos = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}
    return pesos.get(acertos, 0)

def buscar_resultados_oficiais(supabase):
    """Busca resultados pegando os mais recentes primeiro para garantir o match."""
    print("📊 Carregando resultados oficiais (últimos 3000)...")
    rows = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True) # Traz do 3677 para baixo
        .limit(3000)                  # Garante que concursos como 3580 estejam na lista
        .execute()
        .data
    )
    resultados = {}
    for row in rows:
        try:
            # Blindagem de tipo e espaços
            concurso_limpo = int(str(row["concurso"]).strip())
            dezenas = parse_numeros(row.get("dezenas"))
            
            if dezenas and len(dezenas) == 15:
                resultados[concurso_limpo] = set(dezenas)
        except Exception:
            continue
            
    print(f"✅ {len(resultados)} concursos oficiais carregados no dicionário.")
    return resultados

def main():
    supabase = get_supabase()
    print("🏁 Iniciando Processamento de Resultados Consolidados...")

    resultados_oficiais = buscar_resultados_oficiais(supabase)

    # Busca todos os palpites marcados como não processados
    print("🔍 Buscando palpites pendentes na tabela 'palpites_validos'...")
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
        try:
            # Força o concurso para inteiro
            concurso = int(str(p["concurso_referencia"]).strip())
            
            # Agora com o limit(3000) e order desc, os concursos devem ser encontrados
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

            # Armazena ID para marcação final
            ids_para_marcar_como_concluidos.append(p["id"])
            
        except Exception as e:
            continue

    # --- INSERÇÃO DOS DADOS CONSOLIDADOS ---
    if not consolidado:
        print("⏳ Nenhum palpite processado. Verifique se os concursos dos palpites estão entre os últimos 3000 resultados oficiais.")
    else:
        print(f"📤 Enviando {len(consolidado)} grupos para 'palpites_resultados_reais'...")
        grupos_salvos = 0
        for chave, payload in consolidado.items():
            try:
                supabase.table("palpites_resultados_reais").insert(payload).execute()
                grupos_salvos += 1
            except Exception as e:
                if "23505" in str(e):
                    grupos_salvos += 1 # Conta como processado se já existia
                else:
                    print(f"❌ Erro ao salvar grupo {chave}: {e}")

        # --- ATUALIZAÇÃO DOS PALPITES ORIGINAIS EM LOTES ---
        if ids_para_marcar_como_concluidos:
            total = len(ids_para_marcar_como_concluidos)
            print(f"🧹 Marcando {total} palpites como processados em lotes de 200...")
            
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
                    print(f"   ❌ Erro no lote: {e}")

    print(f"\n🚀 Fim do Processo. {len(ids_para_marcar_como_concluidos)} palpites reconciliados com o histórico.")

if __name__ == "__main__":
    main()


