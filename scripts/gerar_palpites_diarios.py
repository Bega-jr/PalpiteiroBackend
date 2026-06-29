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
from dataclasses import dataclass, field
from typing import Any, Dict, List

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

VERSAO = "v19.3-portfolio-inteligente"
QTD_FINAL = 10
MAX_TENTATIVAS = 45000
MAX_OCORRENCIAS_GLOBAL = 7
PESO_PENALIDADE_SATURACAO = 0.03
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

# ==========================================================
# PORTFOLIO ENGINE
# ==========================================================
@dataclass
class PortfolioState:
    jogos: List[Dict[str, Any]] = field(default_factory=list)
    dezenas_counter: Counter = field(default_factory=Counter)
    cluster_counter: Counter = field(default_factory=Counter)
    hash_counter: Counter = field(default_factory=Counter)
    score_total: float = 0.0

    def adicionar(self, candidato: Dict[str, Any]) -> None:
        numeros = candidato.get("numeros") or candidato.get("nums", [])
        self.jogos.append(candidato)
        self.dezenas_counter.update(numeros)
        self.cluster_counter[candidato.get("cluster_id", 0)] += 1
        self.hash_counter[candidato.get("hash_estrutura", "")] += 1
        self.score_total += candidato.get("score", 0.0)


class PortfolioEngine:
    def __init__(self):
        self.config = {
            "ELITE": {
                "range": range(0, 3),
                "weight_ensemble": 0.58,
                "weight_diversity": 0.07,
                "weight_tens_coverage": 0.12,
                "weight_cluster": 0.10,
                "weight_hash": 0.05,
                "weight_roi": 0.08,
            },
            "BALANCEADO": {
                "range": range(3, 7),
                "weight_ensemble": 0.42,
                "weight_diversity": 0.18,
                "weight_tens_coverage": 0.18,
                "weight_cluster": 0.10,
                "weight_hash": 0.05,
                "weight_roi": 0.07,
            },
            "EXPLORADOR": {
                "range": range(7, 9),
                "weight_ensemble": 0.25,
                "weight_diversity": 0.35,
                "weight_tens_coverage": 0.20,
                "weight_cluster": 0.10,
                "weight_hash": 0.05,
                "weight_roi": 0.05,
            },
            "EXTREMO": {
                "range": range(9, 999),
                "weight_ensemble": 0.15,
                "weight_diversity": 0.50,
                "weight_tens_coverage": 0.25,
                "weight_cluster": 0.05,
                "weight_hash": 0.05,
                "weight_roi": 0.00,
            }
        }
        self.papeis = tuple(self.config.items())
        self.set_cache: Dict[int, set] = {}
        self.overlap_cache: Dict[tuple, int] = {}
        self.max_overlap = 11

    def obter_overlap(self, idx_a: int, idx_b: int) -> int:
        chave = (min(idx_a, idx_b), max(idx_a, idx_b))
        if chave not in self.overlap_cache:
            self.overlap_cache[chave] = len(self.set_cache[idx_a] & self.set_cache[idx_b])
        return self.overlap_cache[chave]

    def obter_pesos_papel(self, indice: int) -> Dict[str, float]:
        for _, dados in self.papeis:
            if indice in dados["range"]:
                return dados
        return self.config["EXTREMO"]

    def calcular_ganho_marginal(self, candidato, idx_candidato, indices_atual, dezenas_counter, cluster_counter, hash_counter, pesos):
        score_ensemble = candidato.get("score", 0.0)
        score_roi = candidato.get("score_potencial", 0.0)

        if not indices_atual:
            score_diversidade = 1.0
        else:
            soma_distancias = 0
            for idx in indices_atual:
                overlap = self.obter_overlap(idx_candidato, idx)
                if overlap > self.max_overlap:
                    return -9999.0
                soma_distancias += (15 - overlap)
            score_diversidade = (soma_distancias / len(indices_atual)) / 15.0

        total_jogos = len(indices_atual) + 1
        freq_ideal = (total_jogos * 15) / 25.0
        score_dezenas = 0.0
        for dezena in self.set_cache.get(idx_candidato, set()):
            freq = dezenas_counter[dezena]
            if freq < freq_ideal - 0.5:
                score_dezenas += 1.4
            elif freq < freq_ideal + 1.5:
                score_dezenas += 1.0
            else:
                score_dezenas += 0.5
        score_dezenas /= 15

        score_cluster = 1 / (cluster_counter.get(candidato.get("cluster_id", 0), 0) + 1)
        score_hash = 1 / (hash_counter.get(candidato.get("hash_estrutura", ""), "") + 1)

        return (
            score_ensemble * pesos["weight_ensemble"] +
            score_diversidade * pesos["weight_diversity"] +
            score_dezenas * pesos["weight_tens_coverage"] +
            score_cluster * pesos["weight_cluster"] +
            score_hash * pesos["weight_hash"] +
            score_roi * pesos["weight_roi"]
        )

    def selecionar_portfolio(self, candidatos: List[Dict], tamanho: int = 10):
        if not candidatos:
            return []
        
        self.set_cache = {idx: set(c.get("numeros", c.get("nums", []))) for idx, c in enumerate(candidatos)}
        self.overlap_cache.clear()

        estado = PortfolioState()
        indices_escolhidos = set()

        while len(estado.jogos) < tamanho and len(indices_escolhidos) < len(candidatos):
            pesos = self.obter_pesos_papel(len(estado.jogos))
            melhor_idx = None
            melhor_score = -float('inf')

            for idx, candidato in enumerate(candidatos):
                if idx in indices_escolhidos:
                    continue
                ganho = self.calcular_ganho_marginal(
                    candidato, idx, list(indices_escolhidos),
                    estado.dezenas_counter, estado.cluster_counter,
                    estado.hash_counter, pesos
                )
                if ganho > melhor_score:
                    melhor_score = ganho
                    melhor_idx = idx

            if melhor_idx is None:
                break

            escolhido = candidatos[melhor_idx]
            estado.adicionar(escolhido)
            indices_escolhidos.add(melhor_idx)

        return estado.jogos
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
# MOTOR DE GERAÇÃO - Versão Modulada e Unificada
# ======================================================
def executar_motor_geracao(concurso_alvo=None, modo_variacao="moderado"):
    inicio_execucao = time.time()
    supabase = get_supabase()
    print(f"🚀 {VERSAO} - Modo: {modo_variacao.upper()} | Potencial Alto + Portfolio Engine [UNIFICADO]")
   
    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()
    hist = carregar_historico()
    ultimo = hist[-1]["numeros"]
  
    if concurso_alvo is None:
        concurso_ref = int(hist[-1]["concurso"]) + 1
    else:
        concurso_ref = concurso_alvo

    if concurso_alvo is None and concurso_ja_processado(supabase, concurso_ref):
        print(f"ℹ️ Concurso {concurso_ref} já processado.")
        return []

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]
    pesos = obter_pesos_ensemble()
    contexto = detectar_contexto(hist)
   
    print("🧠 Carregando memória estrutural...")
    # Removida a duplicação: Apenas uma chamada otimizada ao Supabase
    memorias = (
        supabase
        .table("memoria_cenarios")
        .select("hash_estrutura, score_contextual, score_previsibilidade, score_medio_real, vezes_gerado, taxa_sobrevivencia")
        .execute()
        .data
    )
  
    memoria_cache = {m["hash_estrutura"]: m for m in memorias}
    print(f"✅ Estruturas carregadas: {len(memoria_cache)}")

    # Geração de candidatos
    candidatos = []
    usados = {tuple(sorted(h["numeros"])) for h in hist}
    contador_dezenas = Counter()
   
    pool = list(range(1, 26))
   
    limites = {
        "soma_min": 158, "soma_max": 232,
        "pares_min": 5, "pares_max": 10,
        "primos_min": 3, "primos_max": 8,
        "moldura_min": 8, "moldura_max": 14,
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

        if not validar_autonomo(filtros, estrutura["linhas"], limites):
            continue

        # =====================================
        # MEMÓRIA ESTRUTURAL & FILTROS DE CONFIANÇA
        # =====================================
        memoria_estrutura = memoria_cache.get(estrutura["hash_estrutura"])

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

            # Filtro de Confiança Estrutural v19.3
            if vezes_gerado >= 5 and score_contextual < 4.8 and score_medio_real < 8:
                continue

            # Filtro de Estruturas Ruins (Segunda Versão)
            if score_medio_real < 6 and vezes_gerado >= 3:
                continue

        # =====================================
        # FEATURES & SIMULAÇÕES MONE CARLO
        # =====================================
        features = gerar_features_jogo(
            jogo=jogo, ultimo=ultimo, filtros=filtros, estrutura=estrutura, contexto=contexto
        )
    
        score_mc = simular_probabilidade_jogo(jogo, historico=hist)
        cluster_id = identificar_cluster_jogo(features)
    
        # =====================================
        # TRAVAS DE DIVERSIDADE E OVERLAP
        # =====================================
        if not diversidade_avancada_ok(jogo, candidatos[-40:], estrutura, cluster_id):
            continue
    
        if candidatos:
            overlap_medio_local = np.mean([
                len(set(jogo) & set(c["nums"])) for c in candidatos[-50:]
            ])
            if overlap_medio_local > 8.5:
                continue

        # =====================================
        # PONTUAÇÃO (SCORE) E ENSEMBLE EVOLUTIVO
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
    
        # Ponderação com Aprendizado Real
        score_final = (
            score_final * 0.40
            + score_potencial * 0.30
            + score_contextual * 0.15
            + score_previsibilidade * 0.05
            + (score_medio_real / 15.0) * 0.10
        )
    
        # Multiplicadores de Recompensa (Bônus de Elite)
        if score_medio_real >= 9.5:
            score_final *= 1.12
        elif score_medio_real >= 9:
            score_final *= 1.08

        # Inclusão do Candidato com Metadados completos para os dois módulos
        candidatos.append({
            "nums": jogo,
            "score": float(score_final),
            "score_potencial": float(score_potencial),
            "score_mc": float(score_mc),
            "score_contextual": float(score_contextual),
            "score_previsibilidade": float(score_previsibilidade),
            "score_medio_real": float(score_medio_real),
            "filtros": filtros,
            "estrutura": estrutura,
            "features": features,
            "cluster_id": cluster_id
        })
   
        for n in jogo:
            contador_dezenas[n] += 1

    # Filtro global de saturação por frequência de dezenas
    contador_global = Counter()
    candidatos_filtrados = []
    for cand in sorted(candidatos, key=lambda x: -x["score"]):
        penalidade = sum(PESO_PENALIDADE_SATURACAO for n in cand["nums"] if contador_global[n] >= MAX_OCORRENCIAS_GLOBAL)
        cand["score"] = cand["score"] - penalidade
        candidatos_filtrados.append(cand)
        for n in cand["nums"]:
            contador_global[n] += 1

    # ==================== SELEÇÃO FINAL COM PORTFOLIO ENGINE ====================
    print("🔀 Aplicando Portfolio Engine Inteligente (ELITE → EXTREMO)...")

    # Mapeia 'nums' para 'numeros' exigido pelo Portfolio Engine e blocos posteriores
    for cand in candidatos_filtrados:
        if "nums" in cand and "numeros" not in cand:
            cand["numeros"] = cand.pop("nums")

    engine = PortfolioEngine()
    portfolio_final = engine.selecionar_portfolio(candidatos_filtrados, QTD_FINAL)

    # Fallback de segurança se o Portfolio Engine falhar em preencher a quantidade
    if len(portfolio_final) < QTD_FINAL:
        print(f"⚠️ Portfolio Engine retornou {len(portfolio_final)} jogos. Usando fallback.")
        portfolio_final = sorted(
            candidatos_filtrados,
            key=lambda x: (x.get("score", 0), x.get("score_medio_real", 0)),
            reverse=True
        )[:QTD_FINAL]

    finais = portfolio_final

    # Cálculo do ROI esperado
    calcular_roi(len(finais))
    print(f"✅ Portfolio Engine concluiu com {len(finais)} jogos")

        # =====================================================
    # ESTRUTURAÇÃO DOS DADOS DE RETORNO (TELEGRAM & DB)
    # =====================================================
    dados_palpites = []
    linhas_telegram = []
   
    for i, c in enumerate(finais, 1):
        tier = "conservador" if i <= 3 else "equilibrado" if i <= 7 else "agressivo"
   
        score_estrutural = round(
            c.get("score_contextual", 0) * 0.40 +
            c.get("score_previsibilidade", 0) * 0.30 +
            c.get("score_medio_real", 0) * 0.30, 8
        )

        numeros_jogo = c.get("numeros") or c.get("nums", [])

        texto_linha_telegram = (
            f"{i}º | {c.get('score', 0):.5f} | "
            f"Pot={c.get('score_potencial', 0):.3f} | "
            f"MC={c.get('score_mc', 0):.4f} | "
            f"{tier.upper()} | {numeros_jogo}"
        )
   
        linhas_telegram.append(texto_linha_telegram)

        if i <= 3:
            print("\n====================")
            print("DEBUG FINALISTA")
            print("====================")
            print({
                "cluster_id": c.get("cluster_id"),
                "score_contextual": c.get("score_contextual"),
                "score_previsibilidade": c.get("score_previsibilidade"),
                "score_medio_real": c.get("score_medio_real"),
                "estrutura": c.get("estrutura")
            })

        dados_palpites.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": tier,
            "numeros": numeros_jogo,
            "score": round(float(c.get("score", 0)), 8),
            "score_potencial": round(float(c.get("score_potencial", 0)), 8),
            "score_montecarlo": round(float(c.get("score_mc", 0)), 8),
            "score_estrutural": score_estrutural,
            "cluster_id": c.get("cluster_id"),
            "hash_estrutura": c.get("estrutura", {}).get("hash_estrutura") if c.get("estrutura") else None,
            "soma_total": c.get("filtros", {}).get("soma"),
            "pares": c.get("filtros", {}).get("pares"),
            "impares": 15 - c.get("filtros", {}).get("pares", 0),
            "qtd_sequencias": c.get("filtros", {}).get("seq_max"),
            "usa_mais_sorteados": None,
            "usa_menos_sorteados": None,
            "metricas": {},              # Mantém estrutura limpa para o seu dict de métricas
            "filtros_aplicados": {},     # Mantém estrutura limpa para os seus filtros aplicados
            "processado": False,
            "versao_gerador": VERSAO
        })
   
    print(f"⏱️ Tempo total da geração: {time.time() - inicio_execucao:.1f} segundos")
   
    return {
        "palpites": dados_palpites,
        "linhas_telegram": linhas_telegram,
        "concurso": concurso_ref
    }
