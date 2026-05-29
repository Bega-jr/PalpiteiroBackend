import sys
import json
import math
import statistics
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

VERSAO = "v2.0-meta-validacao-autoregenerativa"
QTD_PALPITES = 7
LIMITE_OVERLAP_MEDIO = 11.2
LIMITE_EXPOSICAO_DEZENA = 6
LIMITE_ENTROPIA = 2.70
LIMITE_DIVERSIDADE = 16
MAX_REGENERACOES = 3


# ======================================================
# HELPERS
# ======================================================
def calcular_overlap(j1, j2):
    return len(set(j1) & set(j2))


def calcular_entropia(contagem):
    total = sum(contagem.values())
    if total == 0:
        return 0

    entropia = 0
    for v in contagem.values():
        p = v / total
        if p > 0:
            entropia -= p * math.log2(p)
    return entropia


def calcular_score_diversidade(jogos):
    dezenas = set()
    for j in jogos:
        dezenas.update(j)
    return len(dezenas)


def calcular_risco_colapso(overlap_medio, entropia, diversidade):
    risco = 0
    if overlap_medio >= 11:
        risco += 1
    if entropia <= 2.75:
        risco += 1
    if diversidade <= 17:
        risco += 1
    return risco


def interpretar_risco(risco):
    if risco <= 1:
        return "BAIXO"
    if risco == 2:
        return "MODERADO"
    return "ALTO"


# ======================================================
# CARREGA PALPITES
# ======================================================
def carregar_palpites(supabase, concurso):
    rows = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("concurso_referencia", concurso)
        .order("indice_palpite")
        .execute()
        .data
    )

    jogos = []
    for r in rows:
        jogos.append({
            "indice": r["indice_palpite"],
            "numeros": json.loads(r["numeros"])
        })
    return jogos


# ======================================================
# ANALISA PORTFÓLIO
# ======================================================
def analisar_portfolio(jogos):
    overlaps = []
    contador = Counter()
    matriz_overlap = []

    for i in range(len(jogos)):
        jogo_i = jogos[i]["numeros"]
        for dez in jogo_i:
            contador[dez] += 1

        for j in range(i + 1, len(jogos)):
            jogo_j = jogos[j]["numeros"]
            ov = calcular_overlap(jogo_i, jogo_j)  # Corrigido "juego" para "jogo"
            overlaps.append(ov)
            matriz_overlap.append({
                "j1": i + 1,
                "j2": j + 1,
                "overlap": ov
            })

    overlap_medio = round(statistics.mean(overlaps), 6) if overlaps else 0.0
    entropia = round(calcular_entropia(contador), 6)
    diversidade = calcular_score_diversidade([x["numeros"] for x in jogos])
    
    dezenas_superexpostas = [
        dez for dez, qtd in contador.items()
        if qtd >= LIMITE_EXPOSICAO_DEZENA
    ]

    risco_colapso = calcular_risco_colapso(overlap_medio, entropia, diversidade)
    nivel_risco = interpretar_risco(risco_colapso)

    status = "OK"
    alertas = []

    if overlap_medio >= LIMITE_OVERLAP_MEDIO:
        status = "ALERTA"
        alertas.append("Overlap excessivo")

    if entropia <= LIMITE_ENTROPIA:
        status = "ALERTA"
        alertas.append("Baixa entropia")

    if diversidade <= LIMITE_DIVERSIDADE:
        status = "ALERTA"
        alertas.append("Baixa diversidade")

    if dezenas_superexpostas:
        status = "ALERTA"
        alertas.append(f"Superexposição: {dezenas_superexpostas}")

    return {
        "status": status,
        "overlap_medio": overlap_medio,
        "entropia": entropia,
        "diversidade": diversidade,
        "risco_colapso": risco_colapso,
        "nivel_risco": nivel_risco,
        "dezenas_superexpostas": dezenas_superexpostas,
        "alertas": alertas,
        "matriz_overlap": matriz_overlap
    }


# ======================================================
# REMOVE PALPITES
# ======================================================
def remover_palpites_ruins(supabase, concurso):
    supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso).execute()


# ======================================================
# MAIN
# ======================================================
def main():
    print(f"🧠 {VERSAO}")
    supabase = get_supabase()

    # ==================================================
    # ÚLTIMO CONCURSO
    # ==================================================
    ultimo = (
        supabase
        .table("palpites_validos")
        .select("concurso_referencia")
        .order("concurso_referencia", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not ultimo:
        print("❌ Nenhum concurso encontrado.")
        return

    concurso = ultimo[0]["concurso_referencia"]

    # ==================================================
    # LOOP AUTO-REGENERAÇÃO
    # ==================================================
    tentativa = 1

    while tentativa <= MAX_REGENERACOES:
        print(f"\n♻️ Tentativa {tentativa}/{MAX_REGENERACOES}")

        jogos = carregar_palpites(supabase, concurso)

        if len(jogos) < QTD_PALPITES:
            print("⚠️ Menos de 7 palpites.")
            return

        analise = analisar_portfolio(jogos)
        status = analise["status"]

        # ==================================================
        # OUTPUT
        # ==================================================
        print("\n==============================")
        print("🧠 META VALIDAÇÃO FINAL")
        print("==============================\n")
        print(f"🎯 Concurso: {concurso}")
        print(f"📊 Overlap médio: {analise['overlap_medio']}")
        print(f"🧬 Entropia: {analise['entropia']}")
        print(f"🌎 Diversidade: {analise['diversidade']}")
        print(f"⚠️ Risco: {analise['nivel_risco']}")
        print(f"📌 Status: {status}")

        if analise["alertas"]:
            print("\n🚨 ALERTAS:")
            for a in analise["alertas"]:
                print(f"- {a}")

        # ==================================================
        # SALVA EXECUÇÃO
        # ==================================================
        payload = {
            "concurso_referencia": concurso,
            "overlap_medio": analise["overlap_medio"],
            "entropia_global": analise["entropia"],
            "diversidade_global": analise["diversidade"],
            "risco_colapso": analise["risco_colapso"],
            "nivel_risco": analise["nivel_risco"],
            "dezenas_superexpostas": analise["dezenas_superexpostas"],
            "status_validacao": status,
            "alertas": analise["alertas"],
            "tentativa": tentativa,
            "versao": VERSAO
        }

        try:
            supabase.table("meta_validacao_execucoes").upsert(
                payload,
                on_conflict="concurso_referencia"
            ).execute()
        except Exception as e:
            print(f"⚠️ Erro ao salvar: {e}")

        # ==================================================
        # PORTFÓLIO SAUDÁVEL (Indentação Corrigida)
        # ==================================================
        if status == "OK":
            print("\n✅ Portfólio aprovado e validado com sucesso!")
            return

        # ==================================================
        # DISPARA REGENERAÇÃO SE HOUVER TENTATIVAS RESTANTES
        # ==================================================
        if tentativa < MAX_REGENERACOES:
            print(f"\n🔥 Portfólio rejeitado na tentativa {tentativa}/{MAX_REGENERACOES}.")
            print("♻️ Removendo palpites inválidos...")
            remover_palpites_ruins(supabase, concurso)

            print("🚀 Executando engine de regeneração de jogos...")
            import subprocess
            subprocess.run([
                sys.executable,
                "scripts/gerar_palpites_diarios.py"
            ], check=True)

            tentativa += 1
        else:
            break

    # ==================================================
    # FALHA FINAL
    # ==================================================
    print("\n❌ FALHA CRÍTICA")
    print(f"⚠️ Limite de {MAX_REGENERACOES} tentativas atingido sem gerar um portfólio saudável.")
    print("🛑 Os últimos palpites gerados foram mantidos no banco para análise manual.")


if __name__ == "__main__":
    main()

