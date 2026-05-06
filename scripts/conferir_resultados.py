import sys
import json
from pathlib import Path

# Configuração de diretório para importar o Supabase
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
            # Remove possíveis aspas extras de escape e converte string para lista
            parsed = json.loads(valor)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, list):
                return [int(x) for x in parsed]
    except Exception as e:
        print(f"⚠️ Parse erro: {e}")
    return None

def peso_acerto(acertos):
    pesos = {11: 1, 12: 2, 13: 5, 14: 10, 15: 15}
    return pesos.get(acertos, 0)

def buscar_resultados_oficiais(supabase):
    rows = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .execute()
        .data
    )
    resultados = {}
    print(f"📊 Concursos oficiais encontrados no banco: {len(rows)}")

    for row in rows:
        try:
            concurso = int(row["concurso"])
            dezenas = parse_numeros(row.get("dezenas"))
            if not dezenas or len(dezenas) != 15:
                continue
            resultados[concurso] = set(dezenas)
        except Exception as e:
            print(f"⚠️ Erro ao processar concurso {row.get('concurso')}: {e}")

    print(f"✅ Concursos válidos carregados: {len(resultados)}")
    return resultados

def main():
    supabase = get_supabase()
    print("🏁 Iniciando conferência e população de palpites_resultados_reais...")

    resultados = buscar_resultados_oficiais(supabase)

    # BUSCA: Palpites que ainda não foram processados para a tabela de resultados
    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("processado", False) 
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nada novo para conferir (todos marcados como processados)")
        return

    print(f"📌 {len(palpites)} palpites pendentes encontrados")

    processados_sucesso = 0
    ignorados_sem_resultado = {}

    for p in palpites:
        try:
            concurso = int(p["concurso_referencia"])

            # Se o resultado oficial ainda não saiu, pula
            if concurso not in resultados:
                ignorados_sem_resultado[concurso] = ignorados_sem_resultado.get(concurso, 0) + 1
                continue

            numeros = parse_numeros(p["numeros"])
            if not numeros:
                print(f"⚠️ Palpite {p['id']} ignorado: Números inválidos")
                continue

            oficiais = resultados[concurso]
            acertos = len(set(numeros) & oficiais)
            peso = peso_acerto(acertos)

            # Monta o payload para a tabela palpites_resultados_reais
            payload = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": concurso,
                "concurso_fim": concurso,
                "total_concursos": 1,
                "tipo_palpite": p.get("tipo") or "estatistico",
                "versao_gerador": p.get("versao_gerador") or "legacy",
                "qtd_palpites": 1,

                "acertos_11": 1 if acertos == 11 else 0,
                "acertos_12": 1 if acertos == 12 else 0,
                "acertos_13": 1 if acertos == 13 else 0,
                "acertos_14": 1 if acertos == 14 else 0,
                "acertos_15": 1 if acertos == 15 else 0,

                "score_ponderado": float(peso),
                "eficiencia": 1 if acertos >= 11 else 0,

                "taxa_15": 1 if acertos == 15 else 0,
                "taxa_14": 1 if acertos == 14 else 0,
                "taxa_13": 1 if acertos == 13 else 0,
                "taxa_12": 1 if acertos == 12 else 0
            }

            # 1. Salva na tabela de resultados reais
            supabase.table("palpites_resultados_reais").insert(payload).execute()

            # 2. Atualiza a palpite_validos: marca como processado e salva os acertos
            supabase.table("palpites_validos") \
                .update({
                    "acertos": acertos,
                    "processado": True,
                    "conferido": True
                }) \
                .eq("id", p["id"]) \
                .execute()

            print(f"✅ Palpite {p['id']} (Concurso {concurso}) processado: {acertos} acertos")
            processados_sucesso += 1

        except Exception as e:
            print(f"❌ Erro ao processar ID {p.get('id')}: {e}")

    # Resumo final
    if ignorados_sem_resultado:
        print("\n⏳ Aguardando resultados oficiais saírem:")
        for conc, qtd in sorted(ignorados_sem_resultado.items()):
            print(f"   - Concurso {conc}: {qtd} palpites na fila")

    print(f"\n🚀 Fim do processo. {processados_sucesso} novos registros na tabela de resultados.")

if __name__ == "__main__":
    main()

