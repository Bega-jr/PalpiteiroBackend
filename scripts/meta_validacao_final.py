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
# CARREGA E PREPARA PALPITES
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
        dado_bruto = r["numeros"]
        
        if isinstance(dado_bruto, str):
            try:
                numeros_convertidos = json.loads(dado_bruto)
                if isinstance(numeros_convertidos, str):
                    numeros_convertidos = json.loads(numeros_convertidos)
            except Exception:
                numeros_convertidos = []
        elif isinstance(dado_bruto, list):
            numeros_convertidos = dado_bruto
        else:
            numeros_convertidos = []

        jogos.append({
            "indice": r["indice_palpite"],
            "numeros": numeros_convertidos
        })
        
    return jogos


def preparar_jogos_memoria(retorno_ia):
    """
    NOVO HELP: Transforma os objetos brutos gerados pela IA em memória 
    no mesmo formato estruturado esperado pelo analisador de portfólio.
    """
    jogos = []
    # Dependendo se retornar a lista direta do payload ou finais_candidatos
    for idx, item in enumerate(retorno_ia, start=1):
        # Verifica se o item veio com a chave 'nums' ou se já é o dicionário de payload pronto
        if "nums" in item:
            nums = item["nums"]
        elif "numeros" in item:
            # Se for string JSON vinda do dicionário de payload
            nums = json.loads(item["numeros"]) if isinstance(item["numeros"], str) else item["numeros"]
        else:
            nums = item

        jogos.append({
            "indice": idx,
            "numeros": nums
        })
    return jogos


# ======================================================
# ANALISA PORTFÓLIO
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

            ov = calcular_overlap(
                jogo_i,
                jogo_j
            )

            overlaps.append(ov)

            matriz_overlap.append({
                "j1": i + 1,
                "j2": j + 1,
                "overlap": ov
            })

    overlap_medio = (
        round(statistics.mean(overlaps), 6)
        if overlaps else 0.0
    )

    entropia = round(
        calcular_entropia(contador),
        6
    )

    diversidade = calcular_score_diversidade(
        [x["numeros"] for x in jogos]
    )

    limite_exposicao_real = max(
        limite_exposicao,
        math.ceil(
            ((len(jogos) * 15) / 25) * 1.20
        )
    )

    dezenas_superexpostas = [
        dez
        for dez, qtd in contador.items()
        if qtd >= limite_exposicao_real
    ]

    risco_colapso = calcular_risco_colapso(
        overlap_medio,
        entropia,
        diversidade
    )

    nivel_risco = interpretar_risco(
        risco_colapso
    )

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
        "status": status,
        "overlap_medio": overlap_medio,
        "entropia": entropia,
        "diversidade": diversidade,
        "risco_colapso": riesgo_colapso if 'riesgo_colapso' not in locals() else risco_colapso, # correção preventiva de escopo
        "risco_colapso": risco_colapso,
        "nivel_risco": nivel_risco,
        "dezenas_superexpostas": dezenas_superexpostas,
        "alertas": alertas,
        "matriz_overlap": matriz_overlap,
        "limite_exposicao_real": limite_exposicao_real
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
    # DETECÇÃO AUTO-AJUSTÁVEL DE CONCURSO (FALLBACK ATIVO)
    # ==================================================
    try:
        from scripts.gerar_palpites_diarios import carregar_historico
        hist = carregar_historico()
        concurso_alvo_real = int(hist[-1]["concurso"]) + 1
    except Exception as e:
        print(f"⚠️ Não foi possível ler o histórico oficial ({e}). Tentando inferir pelo banco...")
        concurso_alvo_real = None

    ultimo_gravado_banco = (
        supabase
        .table("palpites_validos")
        .select("concurso_referencia")
        .order("concurso_referencia", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not ultimo_gravado_banco:
        print("❌ Tabela 'palpites_validos' vazia. Não há dados para validar.")
        return

    concurso_banco_max = ultimo_gravado_banco[0]["concurso_referencia"] 

    # Inicializa flag de controle
    forçar_regeneracao_imediata = False

    if concurso_alvo_real and concurso_banco_max != concurso_alvo_real:
        print(f"\n⚠️ [DESALINHAMENTO DETECTADO]")
        print(f"   O histórico aponta para o Concurso: {concurso_alvo_real}")
        print(f"   O banco possui palpites apenas até o Concurso: {concurso_banco_max}")
        print(f"   🚨 Um ou mais concursos foram perdidos no meio do caminho!")
        print(f"   ⚙️ Forçando auto-ajuste para o Concurso {concurso_alvo_real} para investigação...")
        
        concurso = concurso_alvo_real
        forçar_regeneracao_imediata = True
    else:
        concurso = concurso_banco_max

    print(f"🎯 Concurso definitivo definido para validação: {concurso}")

    # ==================================================
    # LOOP AUTO-REGENERAÇÃO
    # ==================================================
    tentativa = 1
    limite_exp_dinamico = LIMITE_EXPOSICAO_DEZENA
    limite_ov_dinamico = LIMITE_OVERLAP_MEDIO

    while tentativa <= MAX_REGENERACOES:
        print(f"\n♻️ Tentativa {tentativa}/{MAX_REGENERACOES}")

        if tentativa == 2:
            limite_exp_dinamico = 9
        elif tentativa == 3:
            limite_exp_dinamico = 10
            limite_ov_dinamico = 11.5

        # Inicializa estruturas locais para a rodada atual
        payload_ia = []
        telegram_ia = []

        # Se forçado pelo auto-ajuste na tentativa 1, ignora a geração imediata
        if forçar_regeneracao_imediata and tentativa == 1:
            print("ℹ️ Aplicando métricas zeradas temporárias para disparar o motor de geração...")
            status = "REJEITADO_FORCADO"
            analise = {
                "overlap_medio": 0.0,
                "entropia": 0.0,
                "diversidade": 0,
                "limite_exposicao_real": limite_exp_dinamico,
                "nivel_risco": "NENHUM (AUTO-AJUSTE)",
                "risco_colapso": 0,
                "dezenas_superexpostas": [],
                "alertas": ["Desalinhamento de histórico: Forçando criação de raiz do concurso."]
            }
        else:
            print(f"🚀 Chamando motor de IA para gerar candidatos (Modo de variação calibrado)...")
            from scripts.gerar_palpites_diarios import executar_motor_geracao
            
            # Executa a inteligência
            dados_ia_memoria = executar_motor_geracao(concurso_alvo=concurso)
            
            # --- BLINDAGEM DE RETORNO (Evita o KeyError) ---
            if isinstance(dados_ia_memoria, dict):
                payload_ia = dados_ia_memoria.get("payload", [])
                telegram_ia = dados_ia_memoria.get("telegram", [])
            elif isinstance(dados_ia_memoria, list):
                # Fallback caso a função tenha retornado a lista direta
                payload_ia = dados_ia_memoria
                telegram_ia = [f"Jogo {idx+1} | {j}" for idx, j in enumerate(payload_ia)]
            # -----------------------------------------------

            if not payload_ia or len(payload_ia) < QTD_PALPITES:
                print(f"⚠️ Menos de {QTD_PALPITES} palpites gerados em memória pela IA (Gerados: {len(payload_ia)}).")
                status = "REJEITADO_POR_FALTA_DE_DADOS"
                analise = {
                    "overlap_medio": 0.0, "entropia": 0.0, "diversidade": 0,
                    "limite_exposicao_real": limite_exp_dinamico, "nivel_risco": "ALTO",
                    "risco_colapso": 3, "dezenas_superexpostas": [],
                    "alertas": [f"Dados gerados insuficientes na tentativa {tentativa}."]
                }
            else:
                # Adapta os dados de memória para o formato do validador estruturado
                jogos_validacao = preparar_jogos_memoria(payload_ia)
                analise = analisar_portfolio(jogos_validacao, limite_exp_dinamico, limite_ov_dinamico)
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
        print(f"📈 Limite Exposição: {analise['limite_exposicao_real']}")
        print(f"⚠️ Risco: {analise['nivel_risco']}")
        print(f"📌 Status: {status}")
        if analise["alertas"]:
            print("\n🚨 ALERTAS:")
            for a in analise["alertas"]:
                print(f"- {a}")

        # ==================================================
        # SALVA TELEMETRIA DA EXECUÇÃO
        # ==================================================
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
            "versao": VERSAO
        }
        try:
            supabase.table("meta_validacao_execucoes").upsert(
                payload_meta,
                on_conflict="concurso_referencia"
            ).execute()
        except Exception as e:
            print(f"⚠️ Erro ao salvar log de execução: {e}")

        # ==================================================
        # PORTFÓLIO SAUDÁVEL: SALVAMENTO E ENVIO DO TELEGRAM DEFINITIVOS
        # ==================================================
        if status == "OK" and payload_ia:
            print("\n✅ Portfólio aprovado e validado com sucesso!")
            
            try:
                print(f"💾 Persistindo {len(payload_ia)} palpites validados na tabela 'palpites_validos'...")
                remover_palpites_ruins(supabase, concurso)
                
                supabase.table("palpites_validos").upsert(
                    payload_ia, 
                    on_conflict="concurso_referencia,indice_palpite"
                ).execute()
                print(f"✅ [BANCO] {len(payload_ia)} palpites salvos com sucesso absoluto!")
            except Exception as e:
                print(f"\n❌ [ERRO CRÍTICO] O banco recusou a gravação do portfólio definitivo: {e}")
                return

            try:
                from scripts.gerar_palpites_diarios import montar_msg_telegram
                
                print("\n📲 TELEGRAM_PAYLOAD_START")
                print(montar_msg_telegram(concurso, telegram_ia))
                print("📲 TELEGRAM_PAYLOAD_END")
                
            except Exception as e:
                print(f"⚠️ Erro ao gerar o payload do Telegram no validador: {e}")

            return

        # ==================================================
        # CONTROLE DAS REGENERAÇÕES RESTANTES
        # ==================================================
        if tentativa < MAX_REGENERACOES:
            print(f"\n🔥 Portfólio rejeitado/forçado na tentativa {tentativa}/{MAX_REGENERACOES}.")
            forçar_regeneracao_imediata = False 
            tentativa += 1
        else:
            break

    print("\n❌ FALHA CRÍTICA")
    print(f"⚠️ Limite de {MAX_REGENERACOES} tentativas atingido sem gerar um portfólio saudável.")
