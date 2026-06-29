import sys
from pathlib import Path
import numpy as np
import json
from datetime import datetime
import logging
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import (
    obter_estatisticas_com_score,
    carregar_historico
)

# ==========================================================
# CONFIGURAÇÃO DE LOG
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("LotofacilProcessamento")

# ==========================================================
# PORTFOLIO ENGINE (INTEGRADO)
# ==========================================================
@dataclass
class PortfolioState:
    jogos: List[Dict[str, Any]] = field(default_factory=list)
    dezenas_counter: Counter = field(default_factory=Counter)
    cluster_counter: Counter = field(default_factory=Counter)
    hash_counter: Counter = field(default_factory=Counter)
    score_total: float = 0.0

    def adicionar(self, candidato: Dict[str, Any]) -> None:
        self.jogos.append(candidato)
        self.dezenas_counter.update(candidato["numeros"])
        self.cluster_counter[candidato.get("cluster_id", 0)] += 1
        self.hash_counter[candidato.get("hash_estrutura", "")] += 1
        self.score_total += candidato.get("score", 0.0)


DEFAULT_PORTFOLIO_CONFIG = {
    "ELITE": {"range": range(0, 3), "weight_ensemble": 0.58, "weight_diversity": 0.07,
              "weight_tens_coverage": 0.12, "weight_cluster": 0.10, "weight_hash": 0.05, "weight_roi": 0.08},
    "BALANCEADO": {"range": range(3, 7), "weight_ensemble": 0.42, "weight_diversity": 0.18,
                   "weight_tens_coverage": 0.18, "weight_cluster": 0.10, "weight_hash": 0.05, "weight_roi": 0.07},
    "EXPLORADOR": {"range": range(7, 9), "weight_ensemble": 0.25, "weight_diversity": 0.35,
                   "weight_tens_coverage": 0.20, "weight_cluster": 0.10, "weight_hash": 0.05, "weight_roi": 0.05},
    "EXTREMO": {"range": range(9, 999), "weight_ensemble": 0.15, "weight_diversity": 0.50,
                "weight_tens_coverage": 0.25, "weight_cluster": 0.05, "weight_hash": 0.05, "weight_roi": 0.00}
}


class PortfolioEngine:
    def __init__(self, config=None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
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

    def calcular_ganho_marginal(self, candidato, idx_candidato, indices_portfolio_atual,
                                dezenas_counter, cluster_counter, hash_counter, pesos):
        score_ensemble = candidato.get("score", 0.0)
        score_roi = candidato.get("roi_estimado", candidato.get("score_potencial", 0.0))

        if not indices_portfolio_atual:
            score_diversidade = 1.0
        else:
            soma_distancias = sum(15 - self.obter_overlap(idx_candidato, idx) 
                                for idx in indices_portfolio_atual 
                                if self.obter_overlap(idx_candidato, idx) <= self.max_overlap)
            score_diversidade = (soma_distancias / len(indices_portfolio_atual)) / 15.0

        total_jogos = len(indices_portfolio_atual) + 1
        freq_ideal = (total_jogos * 15) / 25.0
        score_dezenas = sum(
            1.4 if freq < freq_ideal - 0.5 else 1.0 if freq < freq_ideal + 1.5 else 0.5
            for dezena in self.set_cache[idx_candidato]
            if (freq := dezenas_counter[dezena]) is not None
        ) / 15

        score_cluster = 1 / (cluster_counter[candidato.get("cluster_id", 0)] + 1)
        score_hash = 1 / (hash_counter[candidato.get("hash_estrutura", "")] + 1)

        return (score_ensemble * pesos["weight_ensemble"] +
                score_diversidade * pesos["weight_diversity"] +
                score_dezenas * pesos["weight_tens_coverage"] +
                score_cluster * pesos["weight_cluster"] +
                score_hash * pesos["weight_hash"] +
                score_roi * pesos["weight_roi"])

    def selecao_greedy_inteligente(self, candidatos, tamanho_portfolio=10, ultimos_palpites=None):
        start = time.perf_counter()
        if not candidatos:
            return []

        self.set_cache = {idx: set(c["numeros"]) for idx, c in enumerate(candidatos)}
        self.overlap_cache.clear()

        estado = PortfolioState()
        indices_escolhidos = set()

        # Incluir últimos palpites como âncoras
        if ultimos_palpites:
            for palpite in ultimos_palpites[:2]:
                for idx, cand in enumerate(candidatos):
                    if set(cand["numeros"]) == set(palpite.get("numeros", [])):
                        estado.adicionar(cand)
                        indices_escolhidos.add(idx)
                        logger.info("Último palpite incluído como âncora")
                        break

        while len(estado.jogos) < tamanho_portfolio and len(indices_escolhidos) < len(candidatos):
            pesos = self.obter_pesos_papel(len(estado.jogos))
            melhor_idx, melhor_score = None, -float('inf')

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

        logger.info(f"Portfólio gerado com {len(estado.jogos)} jogos em {(time.perf_counter()-start)*1000:.1f}ms")
        return estado.jogos


# ==========================================================
# SEU CÓDIGO ORIGINAL (UTILITÁRIOS)
# ==========================================================
NUMEROS_PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
VERSAO = "v19.1-contextual-portfolio"

def normalizar(col):
    return (col - col.min()) / (col.max() - col.min() + 1e-9)

def calcular_tendencia(historico, numero, janela=25):
    ultimos = historico[-janela:]
    presencas = [1 if numero in h["numeros"] else 0 for h in ultimos]
    return float(np.mean(presencas))

def calcular_ciclo_historico_completo(historico):
    todos_25 = set(range(1, 26))
    sorteados = set()
    ciclo = 1
    for concurso in historico:
        sorteados.update(concurso["numeros"])
        if sorteados == todos_25:
            sorteados = set()
            ciclo += 1
    faltantes = sorted(todos_25 - sorteados)
    return (faltantes if faltantes else list(range(1, 26)), ciclo)

def extrair_estrutura(nums):
    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in NUMEROS_PRIMOS),
        "linhas": linhas,
        "hash_estrutura": "-".join(map(str, linhas))
    }

def calcular_estabilidade(acertos):
    if not acertos: return 0.0
    dp = float(np.std(acertos))
    return round(max(0.0, 1 - (dp / 5)), 4)

def calcular_dispersao(acertos):
    if not acertos: return 0
    return int(max(acertos) - min(acertos))

def parse_numeros(valor):
    if valor is None: return []
    if isinstance(valor, list):
        return [int(x) for x in valor]
    if isinstance(valor, str):
        try:
            return [int(x) for x in json.loads(valor)]
        except:
            return []
    return []

# (Mantive suas funções de memória, ajustar_por_memoria, etc. iguais)
def buscar_memoria_real(supabase, estrutura):
    # ... (seu código original)
    pass  # mantenha sua implementação

def ajustar_por_memoria(df, memoria):
    # ... (seu código original completo)
    return df  # mantenha sua implementação

# ======================================================
# MAIN - COM INTEGRAÇÃO DO PORTFOLIO
# ======================================================
def main():
    supabase = get_supabase()
    print(f"🚀 [{VERSAO}] Processamento Inteligente + Portfolio Engine Ativo")

    try:
        historico = carregar_historico()
        if not historico:
            print("⚠️ Histórico vazio")
            return

        ultimo = historico[-1]
        concurso = ultimo["concurso"]
        data = ultimo["data"]
        dezenas = ultimo["numeros"]

        print(f"📌 Concurso {concurso} | Data {data}")

        # === SEU PROCESSAMENTO ORIGINAL ===
        df = obter_estatisticas_com_score()
        # ... (todo seu código de estatísticas, memória, feedback loop, etc. permanece igual)

        # === GERAÇÃO DE CANDIDATOS (exemplo - adapte conforme sua lógica real) ===
        # Aqui você deve transformar seu df ou outra fonte em lista de jogos com score
        candidatos = []  # ← Substitua pela sua geração real de palpites
        # Exemplo:
        # for comb in gerar_combinacoes_inteligentes(df):
        #     candidatos.append({"numeros": comb, "score": calc_score(comb), "cluster_id": ..., "hash_estrutura": ...})

        # === SELEÇÃO DO PORTFÓLIO ===
        engine = PortfolioEngine()

        # Carregar últimos palpites (opcional)
        ultimos_palpites = []
        try:
            ultimos = supabase.table("palpites_validos").select("numeros,score").order("created_at", desc=True).limit(2).execute().data
            ultimos_palpites = [{"numeros": parse_numeros(p["numeros"]), "score": p.get("score", 0)} for p in ultimos]
        except:
            pass

        portfolio_final = engine.selecao_greedy_inteligente(
            candidatos=candidatos,
            tamanho_portfolio=10,
            ultimos_palpites=ultimos_palpites
        )

        # === SALVAR PORTFÓLIO ===
        if portfolio_final:
            payload = [{
                "concurso_referencia": int(concurso),
                "numeros": jogo["numeros"],
                "score": float(jogo.get("score", 0)),
                "posicao": i+1,
                "versao": VERSAO,
                "created_at": datetime.now().isoformat()
            } for i, jogo in enumerate(portfolio_final)]

            supabase.table("palpites_validos").insert(payload).execute()
            print(f"✅ Portfólio de {len(portfolio_final)} jogos salvo com sucesso!")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
