import logging
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

# ==========================================================
# ESTADO DO PORTFÓLIO
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


# ==========================================================
# CONFIGURAÇÃO (AJUSTADA PARA ROI + COBERTURA)
# ==========================================================
DEFAULT_PORTFOLIO_CONFIG = {
    "ELITE": {
        "range": range(0, 4),
        "weight_ensemble": 0.55,
        "weight_diversity": 0.08,
        "weight_tens_coverage": 0.12,
        "weight_cluster": 0.10,
        "weight_hash": 0.05,
        "weight_roi": 0.10,
    },
    "BALANCEADO": {
        "range": range(4, 8),
        "weight_ensemble": 0.40,
        "weight_diversity": 0.20,
        "weight_tens_coverage": 0.15,
        "weight_cluster": 0.10,
        "weight_hash": 0.05,
        "weight_roi": 0.10,
    },
    "EXTREMO": {
        "range": range(8, 999),
        "weight_ensemble": 0.20,
        "weight_diversity": 0.45,
        "weight_tens_coverage": 0.20,
        "weight_cluster": 0.05,
        "weight_hash": 0.05,
        "weight_roi": 0.05,
    }
}


class PortfolioEngine:
    def __init__(self, config=None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.papeis = tuple(self.config.items())
        self.set_cache: Dict[int, set[int]] = {}
        self.overlap_cache: Dict[tuple, int] = {}
        self.random = random.Random()
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
            soma_distancias = 0
            for idx_existente in indices_portfolio_atual:
                overlap = self.obter_overlap(idx_candidato, idx_existente)
                if overlap > self.max_overlap:
                    return -9999.0
                soma_distancias += (15 - overlap)
            score_diversidade = (soma_distancias / len(indices_portfolio_atual)) / 15.0

        # Cobertura com viés para concentração
        total_jogos = len(indices_portfolio_atual) + 1
        freq_ideal = (total_jogos * 15) / 25.0
        score_dezenas = 0.0
        for dezena in self.set_cache[idx_candidato]:
            freq = dezenas_counter[dezena]
            if freq < freq_ideal - 0.3:
                score_dezenas += 1.35
            elif freq <= freq_ideal + 1.2:
                score_dezenas += 1.0
            else:
                score_dezenas += 0.55
        score_dezenas /= 15

        score_cluster = 1 / (cluster_counter[candidato.get("cluster_id", 0)] + 1)
        score_hash = 1 / (hash_counter[candidato.get("hash_estrutura", "")] + 1)

        return (
            score_ensemble * pesos["weight_ensemble"] +
            score_diversidade * pesos["weight_diversity"] +
            score_dezenas * pesos["weight_tens_coverage"] +
            score_cluster * pesos["weight_cluster"] +
            score_hash * pesos["weight_hash"] +
            score_roi * pesos["weight_roi"]
        )

    def selecao_greedy_inteligente(
        self,
        candidatos: List[Dict[str, Any]],
        tamanho_portfolio: int,
        ultimos_palpites: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        
        start_time = time.perf_counter()
        logger.info(f"Iniciando seleção com {len(candidatos)} candidatos | Tamanho: {tamanho_portfolio}")

        if not candidatos:
            return []

        # Pré-processamento
        self.overlap_cache.clear()
        self.set_cache.clear()
        for idx, cand in enumerate(candidatos):
            self.set_cache[idx] = set(cand["numeros"])

        estado = PortfolioState()
        indices_escolhidos = set()

        # ====================== INCLUI OS 2 ÚLTIMOS PALPITES ======================
        palpites_iniciais = ultimos_palpites[:2] if ultimos_palpites else []
        
        for i, palpite in enumerate(palpites_iniciais):
            if not palpite or "numeros" not in palpite:
                continue
            # Busca o índice correspondente nos candidatos
            for idx, cand in enumerate(candidatos):
                if set(cand["numeros"]) == set(palpite["numeros"]):
                    estado.adicionar(cand)
                    indices_escolhidos.add(idx)
                    logger.info(f"Palpite anterior {i+1} incluído obrigatoriamente")
                    break

        # Preenche o restante
        while len(estado.jogos) < tamanho_portfolio and len(indices_escolhidos) < len(candidatos):
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

        end_time = time.perf_counter()
        self.calcular_telemetria_final(estado, start_time, end_time)
        return estado.jogos

    def calcular_telemetria_final(self, estado: PortfolioState, inicio: float, fim: float):
        # (mesmo método da versão anterior - mantido igual)
        self.telemetry = getattr(self, 'telemetry', {})
        # ... preencher telemetry (pode copiar da versão anterior completa)
        logger.info(f"Portfólio finalizado com {len(estado.jogos)} jogos")


# ==========================================================
# EXEMPLO DE USO
# ==========================================================
if __name__ == "__main__":
    # Seus candidatos (gerados pelo seu modelo)
    candidatos = [...]  # sua lista aqui

    ultimos_palpites = [
        {"numeros": [1,3,5,7,9,11,13,15,17,19,21,22,23,24,25], "score": 1.55, ...},
        {"numeros": [2,4,6,8,10,12,14,16,18,20,21,22,23,24,25], "score": 1.48, ...}
    ]

    engine = PortfolioEngine()
    portfolio = engine.selecao_greedy_inteligente(
        candidatos=candidatos,
        tamanho_portfolio=10,
        ultimos_palpites=ultimos_palpites
    )

    print(f"Portfólio gerado com {len(portfolio)} jogos")
