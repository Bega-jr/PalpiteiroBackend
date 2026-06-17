import sys
import json
import random
import itertools
import numpy as np
import pytz
import time
from collections import Counter
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais
from app.services.meta_learning_service import obter_pesos_ensemble
from app.services.persistencia_analytics_service import persistir_telemetria
from app.services.recompensa_evolutiva_service import calcular_recompensa_evolutiva
from app.services.feature_store_service import gerar_features_jogo
from app.services.clusterizacao_service import identificar_cluster_jogo
from app.services.diversidade_service import diversidade_avancada_ok
from app.services.montecarlo_service import simular_probabilidade_jogo
from app.services.motores_ensemble_service import calcular_score_ensemble
from app.services.selecao_genetica_service import selecionar_populacao_final
from scripts.processamento_diario_lotofacil import carregar_historico, extrair_estrutura

VERSAO = "v19.2-auto-aprendizado-variacao-roi"
QTD_FINAL = 10
MAX_TENTATIVAS = 45000

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

# ======================================================
# NOVO: Funções de Suporte (ROI + Modo de Variação)
# ======================================================
def calcular_roi():
    custo_jogo = 3.50
    total_custo = QTD_FINAL * custo_jogo
    print(f"💰 ROI Diário → R$ {total_custo:.2f} (10 jogos × R$ 3,50)")
    return total_custo

def aplicar_entropia_modo(score_final, modo_variacao):
    """Aplica variação conforme o modo escolhido"""
    if modo_variacao == "agressivo":
        return score_final * random.uniform(0.82, 1.18)
    elif modo_variacao == "conservador":
        return score_final * random.uniform(0.97, 1.03)
    else:  # moderado
        return score_final * random.uniform(0.96, 1.04)

# ======================================================
# FUNÇÕES ORIGINAIS (mantidas 100% iguais)
# ======================================================
def media_segura(v, fallback=0.5):
    validos = [x for x in v if x is not None]
    return float(np.mean(validos)) if validos else fallback

def concurso_ja_processado(supabase, concurso_ref):
    rows = supabase.table("palpites_validos")\
        .select("indice_palpite")\
        .eq("concurso_referencia", concurso_ref)\
        .limit(1).execute().data
    return len(rows) > 0

def calcular_filtros(nums, ultimo):
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in PRIMOS)
    moldura = sum(1 for n in nums if n in MOLDURA)
    soma = sum(nums)
    repetidos = len(set(nums) & set(ultimo))
    seq_max = 1
    atual = 1
    for i in range(len(nums) - 1):
        if nums[i + 1] == nums[i] + 1:
            atual += 1
            seq_max = max(seq_max, atual)
        else:
            atual = 1
    return {
        "pares": pares, "primos": primos, "moldura": moldura,
        "soma": soma, "repetidos": repetidos, "seq_max": seq_max
    }

def detectar_contexto(hist):
    janela = hist[-12:]
    repetidos = []
    somas = []
    sequencias = []
    for i, h in enumerate(janela):
        nums = h["numeros"]
        ant = janela[i - 1]["numeros"] if i > 0 else nums
        filtros = calcular_filtros(nums, ant)
        repetidos.append(filtros["repetidos"])
        somas.append(filtros["soma"])
        sequencias.append(filtros["seq_max"])
   
    return {
        "media_repetidos": float(np.mean(repetidos)),
        "media_soma": float(np.mean(somas)),
        "media_seq": float(np.mean(sequencias))
    }

def validar_autonomo(filtros, linhas, limites):
    return (
        limites["soma_min"] <= filtros["soma"] <= limites["soma_max"] and
        limites["pares_min"] <= filtros["pares"] <= limites["pares_max"] and
        limites["primos_min"] <= filtros["primos"] <= limites["primos_max"] and
        limites["moldura_min"] <= filtros["moldura"] <= limites["moldura_max"] and
        limites["repetidos_min"] <= filtros["repetidos"] <= limites["repetidos_max"] and
        filtros["seq_max"] <= limites["seq_max_limite"] and
        max(linhas) <= limites["max_linha_limite"]
    )

def score_base(jogo, base):
    s1 = media_segura([base.get((n,), 0.5) for n in jogo])
    s2 = media_segura([
        base.get(tuple(sorted(p)), 0.5)
        for p in itertools.combinations(jogo, 2)
    ])
    ternos = list(itertools.combinations(jogo, 3))
    random.shuffle(ternos)
    scores_ternos = [base.get(tuple(sorted(t)), 0.5) for t in ternos[:120]]
    s3 = (media_segura(scores_ternos) * 0.70) + (max(scores_ternos) * 0.30)
    return s1, s2, s3

def bonus_estrutura(mem):
    if not mem:
        return 1.0
    vezes = int(mem.get("vezes_gerado", 0))
    if vezes >= 40: return 0.93
    if vezes <= 5: return 1.05
    return 1.0

def bonus_fadiga(mem):
    if not mem: return 1.0
    fadiga = float(mem.get("fadiga_estrutura", 0))
    return max(0.88, 1 - (fadiga * 0.10))

def bonus_recencia(mem):
    if not mem: return 1.0
    taxa = float(mem.get("taxa_7d", 0))
    return 1 + (taxa * 0.05)

def bonus_moldura(filtros):
    qtd = filtros["moldura"]
    if 10 <= qtd <= 13: return 1.05
    if qtd <= 7: return 0.95
    return 1.0

def montar_msg_telegram(concurso_ref, linhas_palpites):
    linhas = [
        "🟢 Pipeline Lotofácil v19.2 concluído!",
        "",
        f"🎯 Palpites gerados para o concurso {concurso_ref}",
        ""
    ]
    linhas.extend(linhas_palpites)
    return "\n".join(linhas)

def score_potencial_alto(jogo, historico, base_scores):
    jogo_set = set(jogo)
    hits_historicos = []
    for concurso in historico[-80:]:
        resultado = set(concurso["numeros"])
        hits = len(jogo_set & resultado)
        if hits >= 11:
            hits_historicos.append(hits)
    fator_historico = 1.0
    if hits_historicos:
        media_hits = np.mean(hits_historicos)
        max_hits = max(hits_historicos)
        fator_historico = (media_hits * 0.6) + (max_hits * 0.4)
    quentes = [n for n in jogo if base_scores.get((n,), 0) > 0.65]
    frias = [n for n in jogo if base_scores.get((n,), 0) < 0.45]
    filtros = calcular_filtros(jogo, historico[-1]["numeros"])
    score = (
        fator_historico * 0.55 +
        (len(quentes) * 0.13 + len(frias) * 0.09) +
        (filtros["soma"] / 195) * 0.12 +
        (10 - abs(filtros["pares"] - 7.5)) * 0.11
    )
    return float(score)

# ======================================================
# INÍCIO DO MOTOR PRINCIPAL
# ======================================================
def executar_motor_geracao(concurso_alvo=None):
    """
    Função principal que encapsula a inteligência de IA.
    Ela será chamada pelo Meta Validador e retornará os palpites estruturados.
    """
    inicio_execucao = time.time()
    print(f"🚀 {VERSAO} - Modo: MODERADO | Potencial Alto + Tiers")
    calcular_roi()
    
    supabase = get_supabase()
    historico = carregar_historico()
    
    # Define o concurso alvo se não for passado pelo validador
    if concurso_alvo is None:
        concurso_ref = int(historico[-1]["concurso"]) + 1
    else:
        concurso_ref = concurso_alvo
        
# ======================================================
# MOTOR DE GERAÇÃO - Versão Modulada para o Meta-Validador
# ======================================================
def executar_motor_geracao(concurso_alvo=None, modo_variacao="moderado"):
    inicio_execucao = time.time()
    supabase = get_supabase()
    print(f"🚀 {VERSAO} - Modo: {modo_variacao.upper()} | Potencial Alto + Tiers")

    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()
    hist = carregar_historico()
    ultimo = hist[-1]["numeros"]
    
    # Se o validador enviou o concurso correto, usamos ele. Se não, calculamos.
    if concurso_alvo is None:
        concurso_ref = int(hist[-1]["concurso"]) + 1
    else:
        concurso_ref = concurso_alvo

    # Se rodado de forma avulsa e já processado, interrompe.
    # (Quando rodado pelo pai, o pai limpa a tabela antes, então este if não vai travar).
    if concurso_alvo is None and concurso_ja_processado(supabase, concurso_ref):
        print(f"ℹ️ Concurso {concurso_ref} já processado.")
        return []

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]
    pesos = obter_pesos_ensemble()
    contexto = detectar_contexto(hist)

    # Geração
    candidatos = []
    usados = {tuple(sorted(h["numeros"])) for h in hist}
    contador_dezenas = Counter()
    pool = list(range(1, 26))
    limites = {
        "soma_min": 158, "soma_max": 232, "pares_min": 5, "pares_max": 10,
        "primos_min": 3, "primos_max": 8, "moldura_min": 8, "moldura_max": 14,
        "repetidos_min": 6, "repetidos_max": 12,
        "seq_max_limite": 5, "max_linha_limite": 5
    }

    for _ in range(MAX_TENTATIVAS):
        if len(candidatos) >= 3500:
            break
        jogo = sorted(random.sample(pool, 15))
        if tuple(jogo) in usados:
            continue
        filtros = calcular_filtros(jogo, ultimo)
        estrutura = extrair_estrutura(jogo)
        memoria_estrutura = (
            supabase
            .table("memoria_cenarios")
            .select("*")
            .eq(
                "hash_estrutura",
                estrutura["hash_estrutura"]
            )
            .limit(1)
            .execute()
            .data
        )
        
        memoria_estrutura = (
            memoria_estrutura[0]
            if memoria_estrutura
            else None
        )
        if not validar_autonomo(filtros, estrutura["linhas"], limites):
            continue

        features = gerar_features_jogo(
            jogo=jogo,
            ultimo=ultimo,
            filtros=filtros,
            estrutura=estrutura,
            contexto=contexto
        )
        score_mc = simular_probabilidade_jogo(jogo, historico=hist)
        cluster_id = identificar_cluster_jogo(features)
        if not diversidade_avancada_ok(jogo, candidatos[-40:], estrutura, cluster_id):
            continue

        if candidatos:
            overlap_medio_local = np.mean([
                len(set(jogo) & set(c["nums"]))
                for c in candidatos[-50:]
            ])
            if overlap_medio_local > 8.5:
                continue

        s1, s2, s3 = score_base(jogo, base_scores)
        score_estatistico = (s1 * 0.30) + (s2 * 0.35) + (s3 * 0.35)
        score_potencial = score_potencial_alto(jogo, hist, base_scores)
        score_contextual = 0

        if memoria_estrutura:
            score_contextual = float(
                memoria_estrutura.get(
                    "score_contextual",
                    0
                )
            )

        score_final = calcular_score_ensemble(
            score_estatistico=score_estatistico,
            score_montecarlo=score_mc,
            fator_global=fator_global,
            fator_feedback=1.0,
            fator_regime=1.0,
            bonus_estrutura=bonus_estrutura(memoria_estrutura),
            bonus_fadiga=bonus_fadiga(memoria_estrutura),
            bonus_recencia=bonus_recencia(memoria_estrutura),
            bonus_moldura=bonus_moldura(filtros),
            pesos=pesos,
            bonus_recompensa=calcular_recompensa_evolutiva(estrutura, filtros, cluster_id)
        )

        score_final = (
            score_final * 0.65
            +
            score_potencial * 0.20
            +
            score_contextual * 0.15
        )
        
        score_final -= sum(
            contador_dezenas[n] * 0.045
            for n in jogo
        )
        
        score_final = aplicar_entropia_modo(
            score_final,
            modo_variacao
        )

        candidatos.append({
            "nums": jogo,
            "score": float(score_final),
            "score_potencial": float(score_potencial),
            "score_mc": float(score_mc),
            "filtros": filtros,
            "estrutura": estrutura,
            "features": features,
            "cluster_id": cluster_id
        })
        for n in jogo:
            contador_dezenas[n] += 1

    # Filtro global
    contador_global = Counter()
    candidatos_filtrados = []
    for cand in sorted(candidatos, key=lambda x: -x["score"]):
        excesso = False
        for n in cand["nums"]:
            if contador_global[n] >= 7:
                excesso = True
                break
        if excesso:
            continue
        candidatos_filtrados.append(cand)
        for n in cand["nums"]:
            contador_global[n] += 1

    # ==================== SELEÇÃO FINAL ROBUSTA ====================
    candidatos_filtrados.sort(key=lambda x: x["score"], reverse=True)

    if len(candidatos_filtrados) < 7:
        print(f"⚠️ Poucos candidatos ({len(candidatos_filtrados)}). Aplicando fallback completo.")
        candidatos_filtrados = sorted(candidatos, key=lambda x: -x["score"])

    finais = []

    # Conservadores + Equilibrados
    finais.extend(candidatos_filtrados[:7])

    # Agressivos com mais variação
    resto = [c for c in candidatos_filtrados[7:] if c not in finais]
    random.shuffle(resto)
    for cand in resto:
        if len(finais) >= QTD_FINAL:
            break
        overlap_max = max([len(set(cand["nums"]) & set(f["nums"])) for f in finais], default=0)
        if overlap_max <= 8:
            finais.append(cand)

    # GARANTIA FORTE DE 10 JOGOS
    while len(finais) < QTD_FINAL and len(candidatos_filtrados) > len(finais):
        prox = candidatos_filtrados[len(finais)]
        if prox not in finais:
            finais.append(prox)

    finais = finais[:QTD_FINAL]

    if len(finais) < QTD_FINAL:
        print(f"⚠️ Ainda faltaram palpites. Gerados: {len(finais)}")

    # ROI
    calcular_roi()

    # Estruturação dos dados de retorno para o Pai
    dados_palpites = []
    linhas_telegram = []
    
    for i, c in enumerate(finais, 1):
        tier = "conservador" if i <= 3 else "equilibrado" if i <= 7 else "agressivo"
        
        # Texto original mantendo Pot e MC para a mensagem do Telegram
        texto_linha_telegram = (
            f"{i}º | {c['score']:.5f} | "
            f"Pot={c['score_potencial']:.3f} | "
            f"MC={c['score_mc']:.4f} | "
            f"{tier.upper()} | {c['nums']}"
        )
        linhas_telegram.append(texto_linha_telegram)
        
        # Dicionário cru para o banco de dados e para a meta-validação
        dados_palpites.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": tier,
            "numeros": c["nums"],  # Enviamos como lista pura, o pai converte em string/json na aprovação
            "score": round(float(c["score"]), 8),
            "score_potencial": round(float(c["score_potencial"]), 8),
            "score_montecarlo": round(float(c["score_mc"]), 8),
            "versao_gerador": VERSAO
        })

    print(f"⏱️ Tempo total da geração: {time.time() - inicio_execucao:.1f} segundos")
    
    # RETORNO CRU: O pai recebe os dados do banco e o formato do Telegram prontos em memória!
    return {
        "palpites": dados_palpites,
        "linhas_telegram": linhas_telegram,
        "concurso": concurso_ref
    }


# ======================================================
# ENTRYPOINT (Modo isolado para testes manuais no terminal)
# ======================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--modo", default="moderado", choices=["conservador", "moderado", "agressivo"])
    # Adicionamos a flag --force para o Meta-Validador poder injetar comandos de mutação se necessário
    parser.add_argument("--force", action="store_true", help="Força a regeneração ignorando travas de banco")
    args = parser.parse_args()
    
    try:
        sb = get_supabase()
        
        # Como o código roda de forma isolada, precisamos calcular o concurso_ref para a trava
        from scripts.processamento_diario_lotofacil import carregar_historico
        hist = carregar_historico()
        concurso_ref = int(hist[-1]["concurso"]) + 1
        
        # TRAVA DE SEGURANÇA INTELIGENTE:
        # Se NÃO tiver a flag --force E o concurso já existir no banco, ele protege o banco.
        # Se tiver --force (enviado pelo Pai), ele limpa e avança para a IA gerar novos padrões.
        if not args.force and concurso_ja_processado(sb, concurso_ref):
            print(f"ℹ️ Concurso {concurso_ref} já processado no banco. Ignorando geração para segurança.")
            sys.exit(0)

        print("⚙️ Executando engine em modo de teste isolado...")
        resultado_teste = executar_motor_geracao(modo_variacao=args.modo)
        
        if resultado_teste:
            # Simula a gravação antiga para propósitos de teste isolado
            payload_teste = []
            for p in resultado_teste["palpites"]:
                p_copy = p.copy()
                p_copy["numeros"] = json.dumps(p_copy["numeros"]) # Formata json para salvar
                payload_teste.append(p_copy)
                
            sb.table("palpites_validos").upsert(
                payload_teste, on_conflict="concurso_referencia,indice_palpite"
            ).execute()
            print(f"✅ [TESTE BUCKET] {len(payload_teste)} palpites gravados no banco.")
            
            # Imprime o Telegram na tela para validação visual do teste
            print("\n📲 TELEGRAM_PAYLOAD_START")
            print(montar_msg_telegram(resultado_teste["concurso"], resultado_teste["linhas_telegram"]))
            print("📲 TELEGRAM_PAYLOAD_END")
            
    except Exception:
        import traceback
        traceback.print_exc()
        raise
