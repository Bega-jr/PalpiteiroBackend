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
from app.services.portfolio_engine import PortfolioEngine

VERSAO = "v19.2-auto-aprendizado-variacao-roi"

QTD_FINAL = 10
MAX_TENTATIVAS = 45000

MAX_OCORRENCIAS_GLOBAL = 7
PESO_PENALIDADE_SATURACAO = 0.03

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

# ======================================================
# NOVO: Funções de Suporte (ROI + Modo de Variação)
# ======================================================
def calcular_roi(quantidade_palpites=None):
    custo_jogo = 3.50
    qty = quantidade_palpites if quantidade_palpites is not None else QTD_FINAL
    total_custo = qty * custo_jogo
    print(f"💰 ROI Diário → R$ {total_custo:.2f} ({qty} jogos × R$ 3,50)")
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

    score_ctx = float(
        mem.get(
            "score_contextual",
            0
        )
    )

    if score_ctx >= 5.8:
        return 1.18

    if score_ctx >= 5.5:
        return 1.12

    if score_ctx >= 5.2:
        return 1.08

    if score_ctx >= 5.0:
        return 1.03

    return 0.95

def bonus_confianca(mem):

    if not mem:
        return 1.00

    score_real = float(
        mem.get(
            "score_medio_real",
            0
        )
    )

    if score_real >= 10:
        return 1.12

    if score_real >= 9:
        return 1.08

    if score_real >= 8:
        return 1.04

    return 1.00

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
    if concurso_alvo is None and concurso_ja_processado(supabase, concurso_ref):
        print(f"ℹ️ Concurso {concurso_ref} já processado.")
        return {
            "palpites": [],
            "linhas_telegram": [],
            "concurso": concurso_ref
        }

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]
    pesos = obter_pesos_ensemble()
    contexto = detectar_contexto(hist)
    print("🧠 Carregando memória estrutural...")

    memorias = (
        supabase
        .table("memoria_cenarios")
        .select(
            """
            hash_estrutura,
            score_contextual,
            score_previsibilidade,
            score_medio_real,
            vezes_gerado,
            taxa_sobrevivencia
            """
        )
        .execute()
        .data
    )
    
    memoria_cache = {
        m["hash_estrutura"]: m
        for m in memorias
    }
    
    print(f"✅ Estruturas carregadas: {len(memoria_cache)}")

    # Geração
    candidatos = []
    usados = {tuple(sorted(h["numeros"])) for h in hist}
    
    pool = list(range(1, 26))
    
    limites = {
        "soma_min": 158,
        "soma_max": 232,
        "pares_min": 5,
        "pares_max": 10,
        "primos_min": 3,
        "primos_max": 8,
        "moldura_min": 8,
        "moldura_max": 14,
        "repetidos_min": 6,
        "repetidos_max": 12,
        "seq_max_limite": 5,
        "max_linha_limite": 5
    }
    
    for _ in range(MAX_TENTATIVAS):
    
        if len(candidatos) >= 3500:
            break
    
        jogo = sorted(random.sample(pool, 15))
    
        if tuple(jogo) in usados:
            continue
    
        filtros = calcular_filtros(jogo, ultimo)
        estrutura = extrair_estrutura(jogo)
    
        if not validar_autonomo(filtros, estrutura["linhas"], limites):
            continue
    
        # =====================================
        # MEMÓRIA ESTRUTURAL
        # =====================================
        memoria_estrutura = memoria_cache.get(estrutura["hash_estrutura"])
        
        # FILTRO DE CONFIANÇA ESTRUTURAL
        if memoria_estrutura:
            score_ctx_tmp = float(memoria_estrutura.get("score_contextual", 0))
            score_real_tmp = float(memoria_estrutura.get("score_medio_real", 0))
            vezes_tmp = int(memoria_estrutura.get("vezes_gerado", 0))

            if vezes_tmp >= 5 and score_ctx_tmp < 4.8 and score_real_tmp < 8:
                continue
    
        score_contextual = 0.0
        score_previsibilidade = 0.0
        score_medio_real = 0.0
        taxa_sobrevivencia = 0.0
        vezes_gerado = 0
    
        if memoria_estrutura:
            score_contextual = float(memoria_estrutura.get("score_contextual", 0))
            score_previsibilidade = float(memoria_estrutura.get("score_previsibilidade", 0))
            score_medio_real = float(memoria_estrutura.get("score_medio_real", 0))
            taxa_sobrevivencia = float(memoria_estrutura.get("taxa_sobrevivencia", 0))
            vezes_gerado = int(memoria_estrutura.get("vezes_gerado", 0))

        # FILTRO DE ESTRUTURAS RUINS
        if memoria_estrutura:
            if score_medio_real < 6 and vezes_gerado >= 3:
                continue
    
        # =====================================
        # FEATURES
        # =====================================
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
    
        # =====================================
        # SCORE ESTATÍSTICO & ENSEMBLE
        # =====================================
        s1, s2, s3 = score_base(jogo, base_scores)
    
        score_estatistico = (s1 * 0.30 + s2 * 0.35 + s3 * 0.35)
        score_potencial = score_potencial_alto(jogo, hist, base_scores)
    
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
    
        # =====================================
        # APRENDIZADO REAL
        # =====================================
        score_final = (
            score_final * 0.40
            + score_potencial * 0.30
            + score_contextual * 0.15
            + score_previsibilidade * 0.05
            + (score_medio_real / 15.0) * 0.10
        )
    
        # Estruturas comprovadas ganham bônus
        if score_medio_real >= 9.5:
            score_final *= 1.12
        elif score_medio_real >= 9:
            score_final *= 1.08
        elif score_medio_real >= 8.5:
            score_final *= 1.05
        elif score_medio_real >= 8:
            score_final *= 1.03

        # Novo: Aplicar variação conforme o modo escolhido
        score_final = aplicar_entropia_modo(score_final, modo_variacao)

        # Salva o candidato incluindo as métricas que alimentarão o Telegram/Banco
        candidatos.append({
            "nums": jogo,
            "score": float(score_final),
            "cluster": cluster_id,
            "hash_estrutura": estrutura["hash_estrutura"],
            "filtros": filtros,
            "score_mc": score_mc,
            "score_potencial": score_potencial,
            "score_contextual": score_contextual,
            "score_previsibilidade": score_previsibilidade,
            "score_medio_real": score_medio_real
        })

    print(f"📦 Total de candidatos gerados para análise: {len(candidatos)}")

    # ======================================================
    # OTIMIZAÇÃO INTELIGENTE VIA PORTFOLIO_ENGINE
    # ======================================================
    if not candidatos:
        print("⚠️ Nenhum candidato válido passou pelos filtros iniciais.")
        return {
            "palpites": [],
            "linhas_telegram": [],
            "concurso": concurso_ref
        }

    print("💼 Otimizando carteira final via PortfolioEngine...")
    
    engine = PortfolioEngine()
    finais = engine.selecao_greedy_inteligente(candidatos, qtd_final=QTD_FINAL)
    
    # Executa a telemetria do motor baseado no portfólio montado
    telemetria = engine.calcular_telemetria_final(finais)
    
    # Registra o tempo total e persiste a telemetria
    tempo_total_ms = (time.time() - inicio_execucao) * 1000
    telemetria["execution_time_ms"] = tempo_total_ms
    persistir_telemetria(supabase, concurso_ref, telemetria, versao=VERSAO)
    
    # Exibe informações financeiras/ROI
    calcular_roi(len(finais))

    # ======================================================
    # MANTIDO: ESTRUTURAÇÃO DOS DADOS DE RETORNO (MANTENDO TELEGRAM/BANCO)
    # ======================================================
    dados_palpites = []
    linhas_telegram = []
    
    for i, c in enumerate(finais, 1):
    
        tier = (
            "conservador"
            if i <= 3
            else "equilibrado"
            if i <= 7
            else "agressivo"
        )
    
        score_estrutural = round(
            (
                c.get("score_contextual", 0) * 0.40
                + c.get("score_previsibilidade", 0) * 0.30
                + c.get("score_medio_real", 0) * 0.30
            ),
            8
        )
    
        texto_linha_telegram = (
            f"{i}º | {c['score']:.5f} | "
            f"Pot={c['score_potencial']:.3f} | "
            f"MC={c['score_mc']:.4f} | "
            f"{tier.upper()} | {c['nums']}"
        )
    
        linhas_telegram.append(texto_linha_telegram)
        if i <= 3:
            print("\n====================")
            print("DEBUG FINALISTA")
            print("====================")
            print({
                "cluster_id": c.get("cluster"),
                "score_contextual": c.get("score_contextual"),
                "score_previsibilidade": c.get("score_previsibilidade"),
                "score_medio_real": c.get("score_medio_real"),
                "estrutura": c.get("hash_estrutura")
            })
            
        dados_palpites.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": tier,
            "numeros": c["nums"],
            "score": round(float(c["score"]), 8),
            "score_potencial": round(float(c["score_potencial"]), 8),
            "score_montecarlo": round(float(c["score_mc"]), 8),
            "score_estrutural": score_estrutural,
            "score_contextual_real": round(float(c.get("score_contextual", 0)), 8),
            "score_previsibilidade_real": round(float(c.get("score_previsibilidade", 0)), 8),
            "score_medio_real": round(float(c.get("score_medio_real", 0)), 8),
            "cluster_id": c.get("cluster"),
            "hash_estrutura": c.get("hash_estrutura"),
            "soma_total": c["filtros"]["soma"],
            "pares": c["filtros"]["pares"],
            "impares": (15 - c["filtros"]["pares"]),
            "qtd_sequencias": c["filtros"]["seq_max"],
            "usa_mais_sorteados": None,
            "usa_menos_sorteados": None,
            "metricas": {
                "score_contextual": round(float(c.get("score_contextual", 0)), 8),
                "score_previsibilidade": round(float(c.get("score_previsibilidade", 0)), 8),
                "score_medio_real": round(float(c.get("score_medio_real", 0)), 8),
                "score_montecarlo": round(float(c["score_mc"]), 8),
                "score_potencial": round(float(c["score_potencial"]), 8),
                "score_final": round(float(c["score"]), 8)
            },
            "filtros_aplicados": {
                "pares": c["filtros"]["pares"],
                "primos": c["filtros"]["primos"],
                "moldura": c["filtros"]["moldura"],
                "soma": c["filtros"]["soma"],
                "repetidos": c["filtros"]["repetidos"],
                "seq_max": c["filtros"]["seq_max"]
            },
            "processado": False,
            "versao_gerador": VERSAO
        })
    
    print(f"⏱️ Tempo total da geração: {time.time() - inicio_execucao:.1f} segundos")
    
    return {
        "palpites": dados_palpites,
        "linhas_telegram": linhas_telegram,
        "concurso": concurso_ref
    }
