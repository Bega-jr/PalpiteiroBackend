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
QTD_PALPITES = 10
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

def preparar_jogos_memoria(payload_ia):
    """Converte o retorno em memória da IA para o formato de auditoria"""
    jogos = []
    for item in payload_ia:
        nums = item["numeros"]
        # Se por acaso vier string, converte, senão usa a lista pura
        if isinstance(nums, str):
            nums = json.loads(nums)
        jogos.append({
            "indice": item["indice_palpite"],
            "numeros": nums
        })
    return jogos

# ======================================================
# AUDITORIA DE PORTFÓLIO
# ======================================================
def analisar_portfolio(jogos, limite_exposicao=8, limite_overlap=11.2):
    overlaps = []
    contador = Counter()
    matriz_overlap = []

    for i in range(len(jogos)):
        jogo_i = jogos[i]["numeros"]
        for dez in jogo_i:
            contador[dez] += 1

        for j in range(i + 1, len(jogos)):
            jogo_j = jogos[j]["numeros"]
            ov = calcular_overlap(jogo_i, jogo_j)
            overlaps.append(ov)
            matriz_overlap.append({"j1": i + 1, "j2": j + 1, "overlap": ov})

    overlap_medio = round(statistics.mean(overlaps), 6) if overlaps else 0.0
    entropia = round(calcular_entropia(contador), 6)
    diversidade = calcular_score_diversidade([x["numeros"] for x in jogos])

    limite_exposicao_real = max(limite_exposicao, math.ceil(((len(jogos) * 15) / 25) * 1.20))
    dezenas_superexpostas = [dez for dez, qtd in contador.items() if qtd >= limite_exposicao_real]

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
        "dezenas_superexpostas": dezenas_superexpostas, "alertas": alertas,
        "matriz_overlap": matriz_overlap, "limite_exposicao_real": limite_exposicao_real
    }

def remover_palpites_ruins(supabase, concurso):
    try:
        supabase.table("palpites_validos").delete().eq("concurso_referencia", concurso).execute()
    except Exception as e:
        print(f"⚠️ Alerta na limpeza de tabela: {e}")

# ======================================================
# ENGINE CORE VALIDADOR
# ======================================================
def main():
    print(f"🧠 {VERSAO}")
    supabase = get_supabase()

    # 1. Determina concurso alvo a partir do histórico local
    try:
        from scripts.processamento_diario_lotofacil import carregar_historico
        hist = carregar_historico()
        concurso = int(hist[-1]["concurso"]) + 1
    except Exception as e:
        print(f"❌ Falha Crítica ao ler histórico local: {e}")
        return

    print(f"🎯 Concurso definitivo definido para validação: {concurso}")

    # ==================================================
    # LOOP AUTO-REGENERAÇÃO EM MEMÓRIA RAM
    # ==================================================
    tentativa = 1
    limite_exp_dinamico = LIMITE_EXPOSICAO_DEZENA
    limite_ov_dinamico = LIMITE_OVERLAP_MEDIO

    while tentativa <= MAX_REGENERACOES:
        print(f"\n♻️ Tentativa {tentativa}/{MAX_REGENERACOES}")

        # Calibração dinâmica das rédeas matemáticas conforme a rodada avança
        if tentativa == 2:
            limite_exp_dinamico = 9
        elif tentativa == 3:
            limite_exp_dinamico = 10
            limite_ov_dinamico = 11.5

        print(f"🚀 Acionando motor de IA para criar portfólio temporário...")
        from scripts.gerar_palpites_diarios import executar_motor_geracao
        
        # Executa a inteligência pura na memória RAM (passando o concurso dinamicamente se necessário)
        retorno_ia = executar_motor_geracao(modo_variacao="moderado")

        # --- SINCRONIA DE CHAVES DO SEU RETORNO ---
        payload_ia = retorno_ia.get("palpites", []) if isinstance(retorno_ia, dict) else []
        telegram_ia = retorno_ia.get("linhas_telegram", []) if isinstance(retorno_ia, dict) else []
        # ------------------------------------------

        if not payload_ia or len(payload_ia) < QTD_PALPITES:
            print(f"⚠️ Lote rejeitado: Gerados apenas {len(payload_ia)} de {QTD_PALPITES} palpites exigidos.")
            status = "REJEITADO_POR_VOLUME_INSUFICIENTE"
            analise = {
                "overlap_medio": 0.0, "entropia": 0.0, "diversidade": 0,
                "limite_exposicao_real": limite_exp_dinamico, "nivel_risco": "ALTO",
                "risco_colapso": 3, "dezenas_superexpostas": [],
                "alertas": [f"Lote incompleto na tentativa {tentativa}."]
            }
        else:
            # Audita as listas e os pesos contidos na RAM
            jogos_validacao = preparar_jogos_memoria(payload_ia)
            analise = analisar_portfolio(jogos_validacao, limite_exp_dinamico, limite_ov_dinamico)
            status = analise["status"]

        # ==================================================
        # OUTPUT DE AUDITORIA
        # ==================================================
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
        if analise["alertas"]:
            print("\n🚨 ALERTAS:")
            for a in analise["alertas"]:
                print(f"- {a}")

        # Salva log de auditoria no bucket de telemetria externa
        try:
            payload_meta = {
                "concurso_referencia": concurso, "overlap_medio": analise["overlap_medio"],
                "entropia_global": analise["entropia"], "diversidade_global": analise["diversidade"],
                "risco_colapso": analise["risco_colapso"], "nivel_risco": analise["nivel_risco"],
                "dezenas_superexpostas": analise["dezenas_superexpostas"], "status_validacao": status,
                "alertas": analise["alertas"], "tentativa": tentativa, "versao": VERSAO
            }
            supabase.table("meta_validacao_execucoes").upsert(payload_meta, on_conflict="concurso_referencia").execute()
        except Exception as e:
            print(f"⚠️ Falha ao salvar metadados de execução: {e}")

        # ==================================================
        # CRITÉRIO DE SUCESSO: COMMIT DO LOTE INTEIRO E TELEGRAM
        # ==================================================
        if status == "OK" and payload_ia:
            print("\n✅ Portfólio aprovado e validado com sucesso!")
            
            try:
                print(f"💾 Efetuando commit síncrono dos {len(payload_ia)} palpites na tabela 'palpites_validos'...")
                
                # Garante a formatação JSON em string para o banco antes do commit definitivo
                payload_banco = []
                for p in payload_ia:
                    p_copy = p.copy()
                    if isinstance(p_copy["numeros"], list):
                        p_copy["numeros"] = json.dumps(p_copy["numeros"])
                    payload_banco.append(p_copy)

                # Limpa qualquer lixo residual e persiste o portfólio oficial de uma vez só
                remover_palpites_ruins(supabase, concurso)
                supabase.table("palpites_validos").upsert(payload_banco, on_conflict="concurso_referencia,indice_palpite").execute()
                print(f"✅ [CONSOLIDADO] Dados persistidos com segurança absoluta.")
            except Exception as e:
                print(f"\n❌ [ERRO GRAVE] Falha catastrófica ao tentar salvar dados auditados: {e}")
                return

            # Dispara o print do Telegram limpo e definitivo na tela
            try:
                from scripts.gerar_palpites_diarios import montar_msg_telegram
                print("\n📲 TELEGRAM_PAYLOAD_START")
                print(montar_msg_telegram(concurso, telegram_ia))
                print("📲 TELEGRAM_PAYLOAD_END")
            except Exception as e:
                print(f"⚠️ Falha ao estruturar mensagem do Telegram: {e}")
            return

        # Se falhou por risco ou volume, o lote da memória RAM é limpo e avança o loop
        if tentativa < MAX_REGENERACOES:
            print(f"\n🔥 Portfólio rejeitado na tentativa {tentativa}. Reiniciando motor com limites expandidos...")
            tentativa += 1
        else:
            break

    print("\n❌ PIPELINE FINALIZADO COM RESTRIÇÕES")
    print(f"⚠️ O motor atingiu o limite de {MAX_REGENERACOES} tentativas sem obter a chancela ideal de risco.")

if __name__ == "__main__":
    main()
