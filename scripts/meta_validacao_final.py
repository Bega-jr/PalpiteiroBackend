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
        dado_bruto = r["numeros"]
        
        # Se for uma string (formato antigo "[1, 2...]")
        if isinstance(dado_bruto, str):
            try:
                numeros_convertidos = json.loads(dado_bruto)
                # Se o json.loads ainda retornar uma string, limpa de novo
                if isinstance(numeros_convertidos, str):
                    numeros_convertidos = json.loads(numeros_convertidos)
            except Exception:
                numeros_convertidos = []
        # Se já vier como lista nativa do Python
        elif isinstance(dado_bruto, list):
            numeros_convertidos = dado_bruto
        else:
            numeros_convertidos = []

        jogos.append({
            "indice": r["indice_palpite"],
            "numeros": numeros_convertidos
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

    # ==================================================
    # LIMITE DINÂMICO DE EXPOSIÇÃO
    # ==================================================
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

        alertas.append(
            f"Overlap excessivo ({overlap_medio})"
        )

    if entropia <= LIMITE_ENTROPIA:

        status = "ALERTA"

        alertas.append(
            "Baixa entropia"
        )

    if diversidade <= LIMITE_DIVERSIDADE:

        status = "ALERTA"

        alertas.append(
            "Baixa diversidade"
        )

    if dezenas_superexpostas:

        status = "ALERTA"

        alertas.append(
            f"Superexposição: {dezenas_superexpostas}"
        )

    return {

        "status": status,

        "overlap_medio": overlap_medio,

        "entropia": entropia,

        "diversidade": diversidade,

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

    # Correção aplicada: adicionado o índice [0] como você colocou
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

        # Se forçado pelo auto-ajuste, ignora a leitura e simula métricas zeradas
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
            jogos = carregar_palpites(supabase, concurso)
            if len(jogos) < QTD_PALPITES:
                print(f"⚠️ Menos de {QTD_PALPITES} palpites reais encontrados no banco.")
                # Se faltar jogo em uma tentativa avançada, força o gatilho de recriação
                status = "REJEITADO_POR_FALTA_DE_DADOS"
                analise = {
                    "overlap_medio": 0.0, "entropia": 0.0, "diversidade": 0,
                    "limite_exposicao_real": limite_exp_dinamico, "nivel_risco": "ALTO",
                    "risco_colapso": 3, "dezenas_superexpostas": [],
                    "alertas": ["Dados insuficientes no banco."]
                }
            else:
                analise = analisar_portfolio(jogos, limite_exp_dinamico, limite_ov_dinamico)
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
        # PORTFÓLIO SAUDÁVEL
        # ==================================================
        if status == "OK":
            print("\n✅ Portfólio aprovado e validado com sucesso!")
            
            # --- NOVO BLOCO: ENVIO DO TELEGRAM CONSOLIDADO ---
            try:
                # Importa a função de montagem do próprio script filho
                from scripts.gerar_palpites_diarios import montar_msg_telegram
                
                # Recarrega os jogos finais e limpos direto do banco
                jogos_finais = carregar_palpites(supabase, concurso)
                
                # Adapta o formato para a estrutura que a sua função montar_msg_telegram espera
                # (Extrai apenas as listas de números dos dicionários se necessário)
                lista_jogos_simples = [j["numeros"] for j in jogos_finais]
                
                print("\n📲 TELEGRAM_PAYLOAD_START")
                # Passa a lista validada de 10 jogos para a função de mensagem
                print(montar_msg_telegram(concurso, lista_jogos_simples))
                print("📲 TELEGRAM_PAYLOAD_END")
                
            except Exception as e:
                print(f"⚠️ Erro ao gerar o payload do Telegram no validador: {e}")
            # -------------------------------------------------

            return

        # ==================================================
        # DISPARA REGENERAÇÃO SE HOUVER TENTATIVAS RESTANTES
        # ==================================================
        if tentativa < MAX_REGENERACOES:
            print(f"\n🔥 Portfólio rejeitado/forçado na tentativa {tentativa}/{MAX_REGENERACOES}.")
            print("♻️ Limpando possíveis resquícios da tabela...")
            remover_palpites_ruins(supabase, concurso)

            if tentativa == 1:
                limite_exp_dinamico = 7
            elif tentativa == 2:
                limite_exp_dinamico = 7
                limite_ov_dinamico = 11.5

            print(f"🚀 Executando engine de regeneração com limites calibrados (Exposição Máx: {limite_exp_dinamico})...")
            import subprocess
            subprocess.run([
                sys.executable,
                "scripts/gerar_palpites_diarios.py"
            ], check=True)
            
            # Desativa o bypass para a tentativa 2 consultar os palpites recém-gerados pela engine
            forçar_regeneracao_imediata = False 
            tentativa += 1
        else:
            break

    print("\n❌ FALHA CRÍTICA")
    print(f"⚠️ Limite de {MAX_REGENERACOES} tentativas atingido sem gerar um portfólio saudável.")
    print("🛑 Os últimos palpites gerados foram mantidos no banco para análise manual.")

if __name__ == "__main__":
    main()
