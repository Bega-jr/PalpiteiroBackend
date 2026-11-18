import sys
import json
import math
import statistics
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.services.supabase_service import get_supabase
from scripts.gerar_palpites_diarios import (
    QTD_FINAL,
    executar_motor_geracao,
    montar_msg_telegram,
)

VERSAO = "v2.1-meta-validacao-segura"
LIMITE_OVERLAP_MEDIO = 11.5
LIMITE_EXPOSICAO_DEZENA = 8
LIMITE_ENTROPIA = 2.60
LIMITE_DIVERSIDADE = 18
MAX_REGENERACOES = 3

# ======================================================
# HELPERS MATEMÁTICOS
# ======================================================
def calcular_overlap(j1, j2):
    return len(set(j1) & set(j2))

def calcular_entropia(contagem):
    total = sum(contagem.values())
    if total == 0: return 0
    entropia = 0
    for v in contagem.values():
        p = v / total
        if p > 0: entropia -= p * math.log2(p)
    return entropia

def calcular_score_diversidade(jogos):
    dezenas = set()
    for j in jogos: dezenas.update(j)
    return len(dezenas)

def calcular_risco_colapso(overlap_medio, entropia, diversidade):
    risco = 0
    if overlap_medio >= 11: risco += 1
    if entropia <= 2.75: risco += 1
    if diversidade <= 17: risco += 1
    return risco

def interpretar_risco(risco):
    if risco <= 1: return "BAIXO"
    if risco == 2: return "MODERADO"
    return "ALTO"

def normalizar_palpites(rows):
    jogos = []
    for r in rows:
        dado_bruto = r["numeros"]
        if isinstance(dado_bruto, str):
            numeros_convertidos = json.loads(dado_bruto)
            if isinstance(numeros_convertidos, str):
                numeros_convertidos = json.loads(numeros_convertidos)
        else:
            numeros_convertidos = dado_bruto

        if (
            not isinstance(numeros_convertidos, list)
            or len(numeros_convertidos) != 15
            or any(type(numero) is not int or not 1 <= numero <= 25 for numero in numeros_convertidos)
            or len(set(numeros_convertidos)) != 15
        ):
            raise ValueError(
                f"Palpite {r.get('indice_palpite')} não contém 15 dezenas únicas válidas."
            )

        jogos.append({
            "indice": r["indice_palpite"],
            "numeros": numeros_convertidos,
        
            "score": r.get("score"),
            "score_potencial": r.get("score_potencial"),
            "score_montecarlo": r.get("score_montecarlo"),
            "score_estrutural": r.get("score_estrutural"),
        
            "cluster_id": r.get("cluster_id"),
            "hash_estrutura": r.get("hash_estrutura"),
        
            "metricas": r.get("metricas") or {},
            "filtros": r.get("filtros_aplicados") or {}
        })
    return jogos

def analisar_portfolio(jogos, limite_exposicao=8, limite_overlap=11.2):
    overlaps = []
    contador = Counter()
    for i in range(len(jogos)):
        jogo_i = jogos[i]["numeros"]
        for dez in jogo_i: contador[dez] += 1
        for j in range(i + 1, len(jogos)):
            overlaps.append(calcular_overlap(jogo_i, jogos[j]["numeros"]))

    overlap_medio = round(statistics.mean(overlaps), 6) if overlaps else 0.0
    entropia = round(calcular_entropia(contador), 6)
    diversidade = calcular_score_diversidade([x["numeros"] for x in jogos])
    limite_exposicao_real = max(limite_exposicao, math.ceil(((len(jogos) * 15) / 25) * 1.20))
    dezenas_superexpostas = [
        dez
        for dez, qtd in contador.items()
        if qtd > limite_exposicao_real
    ]
    risco_colapso = calcular_risco_colapso(overlap_medio, entropia, diversidade)
    nivel_risco = interpretar_risco(risco_colapso)

    status = "OK"
    alertas = []
    if overlap_medio >= limite_overlap:
        status = "ALERTA"
        alertas.append(f"Overlap excessivo ({overlap_medio})")
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
        "status": status, "overlap_medio": overlap_medio, "entropia": entropia,
        "diversidade": diversidade, "risco_colapso": risco_colapso, "nivel_risco": nivel_risco,
        "dezenas_superexpostas": dezenas_superexpostas, "alertas": alertas, "limite_exposicao_real": limite_exposicao_real
    }

# ======================================================
# MAIN (VALIDAÇÃO ANTES DA PERSISTÊNCIA)
# ======================================================
def main():
    print(f"🧠 {VERSAO}")
    supabase = get_supabase()

    try:
        from scripts.processamento_diario_lotofacil import carregar_historico
        hist = carregar_historico()
        concurso = int(hist[-1]["concurso"]) + 1
    except Exception as e:
        print(f"❌ Falha Crítica ao ler histórico: {e}")
        return 1

    print(f"🎯 Concurso definitivo definido para validação: {concurso}")

    tentativa = 1
    limite_exp_dinamico = LIMITE_EXPOSICAO_DEZENA
    limite_ov_dinamico = LIMITE_OVERLAP_MEDIO

    while tentativa <= MAX_REGENERACOES:
        print(f"\n♻️ Tentativa {tentativa}/{MAX_REGENERACOES}")

        # Define o modo de variação da IA baseado na rodada para forçar mutações matemáticas
        if tentativa == 1:
            modo_ia = "moderado"
        elif tentativa == 2:
            modo_ia = "agressivo"  # Afrouxa a entropia na IA para abrir o leque
            limite_exp_dinamico = 9
        else:
            modo_ia = "conservador"  # Tenta uma abordagem de segurança
            limite_exp_dinamico = 10
            limite_ov_dinamico = 11.5

        print(f"🚀 Executando motor de IA no modo: {modo_ia.upper()}...")
        
        resultado = executar_motor_geracao(
            concurso_alvo=concurso,
            modo_variacao=modo_ia,
        )
        palpites = resultado.get("palpites", []) if resultado else []
        jogos = normalizar_palpites(palpites)

        score_montecarlo_medio = statistics.mean([
            j.get("score_montecarlo", 0) or 0
            for j in jogos
        ]) if jogos else 0
        
        score_potencial_medio = statistics.mean([
            j.get("score_potencial", 0) or 0
            for j in jogos
        ]) if jogos else 0
        
        score_estrutural_medio = statistics.mean([
            j.get("score_estrutural", 0) or 0
            for j in jogos
        ]) if jogos else 0

        if len(palpites) != QTD_FINAL or len(jogos) != QTD_FINAL:
            print(
                f"⚠️ Lote rejeitado por volume: {len(jogos)} jogos válidos; "
                f"esperados {QTD_FINAL}."
            )
            status = "REJEITADO_POR_FALTA_DE_DADOS"
            analise = {
                "overlap_medio": 0.0, "entropia": 0.0, "diversidade": 0,
                "limite_exposicao_real": limite_exp_dinamico, "nivel_risco": "ALTO",
                "risco_colapso": 3, "dezenas_superexpostas": [], "alertas": ["Volume insuficiente"]
            }
            max_cluster = None
            max_estrutura = None
        else:
            analise = analisar_portfolio(jogos, limite_exp_dinamico, limite_ov_dinamico)
            status = analise["status"]

            # Análise complementar dos palpites
            contador_clusters = Counter(
                j["cluster_id"]
                for j in jogos
                if j.get("cluster_id") is not None
            )
            
            contador_estruturas = Counter(
                j["hash_estrutura"]
                for j in jogos
                if j.get("hash_estrutura")
            )
            
            max_cluster = (
                contador_clusters.most_common(1)[0][0]
                if contador_clusters
                else None
            )
            
            max_estrutura = (
                contador_estruturas.most_common(1)[0][0]
                if contador_estruturas
                else None
            )

        # OUTPUT DE AUDITORIA
        print("\n==============================")
        print("🧠 META VALIDAÇÃO FINAL")
        print("==============================\n")
        print(f"🎯 Concurso: {concurso}")
        print(f"📊 Overlap médio: {analise['overlap_medio']}")
        print(f"🧬 Entropia: {analise['entropia']}")
        print(f"🌎 Diversidade: {analise['diversidade']}")
        print(f"📈 Limite Exposição: {analise['limite_exposicao_real']}")
        print(f"⚠️ Risco: {analise['nivel_risco']}")
        print(f"📌 Status: {status}")
        print(f"🎲 Score MC Médio: {score_montecarlo_medio:.4f}")
        print(f"🚀 Score Potencial Médio: {score_potencial_medio:.4f}")
        print(f"🏗️ Score Estrutural Médio: {score_estrutural_medio:.4f}")
        print(f"🧩 Cluster Dominante: {max_cluster}")

        payload_meta = {
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
            "versao": VERSAO,
            "maior_cluster": max_cluster,
            "maior_estrutura": max_estrutura,
            "qtd_palpites": len(jogos),
            "score_montecarlo_medio": round(score_montecarlo_medio, 6),
            "score_potencial_medio": round(score_potencial_medio, 6),
        }

        # Persist only after the generated portfolio passes validation.
        if status == "OK":
            if len(palpites) != QTD_FINAL:
                raise RuntimeError(
                    f"Resultado incompleto: esperados {QTD_FINAL} palpites, "
                    f"recebidos {len(palpites)}."
                )

            (
                supabase.table("palpites_validos")
                .upsert(
                    palpites,
                    on_conflict="concurso_referencia,indice_palpite",
                )
                .execute()
            )
            (
                supabase.table("palpites_validos")
                .delete()
                .eq("concurso_referencia", concurso)
                .gt("indice_palpite", len(palpites))
                .execute()
            )
            (
                supabase.table("meta_validacao_execucoes")
                .upsert(
                    payload_meta,
                    on_conflict="concurso_referencia",
                )
                .execute()
            )

            print(f"\n✅ Portfólio de {len(jogos)} jogos aprovado com sucesso no modo {modo_ia.upper()}!")
            print("\n📲 TELEGRAM_PAYLOAD_START")
            print(
                montar_msg_telegram(
                    resultado["concurso"],
                    resultado["linhas_telegram"],
                    matriz=resultado.get("matriz"),
                    cobertura=resultado.get("cobertura_matriz"),
                )
            )
            print("📲 TELEGRAM_PAYLOAD_END")
            return 0

        (
            supabase.table("meta_validacao_execucoes")
            .upsert(
                payload_meta,
                on_conflict="concurso_referencia",
            )
            .execute()
        )

        if tentativa < MAX_REGENERACOES:
            print(
                f"\n🔥 Portfólio rejeitado na tentativa {tentativa}; "
                "dados persistidos preservados."
            )
            tentativa += 1
        else:
            break

    print("\n❌ PIPELINE FINALIZADO COM RESTRIÇÕES MÁXIMAS")
    return 1

if __name__ == "__main__":
    sys.exit(main())
