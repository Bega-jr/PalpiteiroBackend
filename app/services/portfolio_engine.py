import logging
import random
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List
import numpy as np  # para desvio padrão

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
        self.cluster_counter[candidato["cluster_id"]] += 1
        self.hash_counter[candidato["hash_estrutura"]] += 1
        self.score_total += candidato.get("score", 0.0)


# ==========================================================
# LOG
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("LotofacilPortfolioEngine")


# ==========================================================
# CONFIGURAÇÃO DOS PAPÉIS
# ==========================================================
DEFAULT_PORTFOLIO_CONFIG = {
    "ELITE": {
        "range": range(0, 3),
        "weight_ensemble": 0.50,
        "weight_diversity": 0.10,
        "weight_tens_coverage": 0.10,
        "weight_cluster": 0.10,
        "weight_hash": 0.10,
        "weight_roi": 0.10,
    },
    "BALANCEADO": {
        "range": range(3, 7),
        "weight_ensemble": 0.35,
        "weight_diversity": 0.20,
        "weight_tens_coverage": 0.15,
        "weight_cluster": 0.10,
        "weight_hash": 0.10,
        "weight_roi": 0.10,
    },
    "EXPLORADOR": {
        "range": range(7, 9),
        "weight_ensemble": 0.20,
        "weight_diversity": 0.30,
        "weight_tens_coverage": 0.20,
        "weight_cluster": 0.15,
        "weight_hash": 0.10,
        "weight_roi": 0.05,
    },
    "EXTREMO": {
        "range": range(9, 999),
        "weight_ensemble": 0.05,
        "weight_diversity": 0.50,
        "weight_tens_coverage": 0.30,
        "weight_cluster": 0.05,
        "weight_hash": 0.10,
        "weight_roi": 0.00,
    }
}


# ==========================================================
# ENGINE
# ==========================================================
class PortfolioEngine:
    def __init__(self, config: Dict[str, Dict[str, Any]] | None = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.papeis = tuple(self.config.items())

        self.set_cache: Dict[int, set[int]] = {}
        self.overlap_cache: Dict[tuple[int, int], int] = {}

        self.random = random.Random()
        self.max_overlap = 12  # limite máximo de números em comum

        self.telemetry = {
            "execution_time_ms": 0,
            "iterations": 0,
            "candidates_evaluated": 0,
            "score_medio": 0,
            "score_minimo": 0,
            "score_maximo": 0,
            "desvio_padrao_score": 0,
            "overlap_medio": 0,
            "clusters_usados": 0,
            "hashes_unicos": 0,
            "dezenas_cobertas": 0,
            "frequencia_maxima": 0,
            "frequencia_minima": 0,
            "portfolio_score": 0
        }

    def obter_overlap(self, idx_a: int, idx_b: int) -> int:
        chave = (min(idx_a, idx_b), max(idx_a, idx_b))
        if chave not in self.overlap_cache:
            self.overlap_cache[chave] = len(
                self.set_cache[idx_a] & self.set_cache[idx_b]
            )
        return self.overlap_cache[chave]

    def obter_pesos_papel(self, indice: int) -> Dict[str, float]:
        for _, dados in self.papeis:
            if indice in dados["range"]:
                return dados
        return self.config["EXTREMO"]

    def calcular_ganho_marginal(
        self,
        candidato: Dict[str, Any],
        idx_candidato: int,
        indices_portfolio_atual: List[int],
        dezenas_counter: Counter,
        cluster_counter: Counter,
        hash_counter: Counter,
        pesos: Dict[str, float]
    ) -> float:
        # Score base
        score_ensemble = candidato.get("score", 0.0)
        score_roi = candidato.get("roi_estimado", candidato.get("score_potencial", 0.0))

        # Diversidade
        if not indices_portfolio_atual:
            score_diversidade = 1.0
        else:
            soma_distancias = 0
            for idx_existente in indices_portfolio_atual:
                overlap = self.obter_overlap(idx_candidato, idx_existente)
                if overlap > self.max_overlap:
                    return -9999.0  # rejeita completamente
                soma_distancias += (15 - overlap)
            score_diversidade = (soma_distancias / len(indices_portfolio_atual)) / 15.0

        # Cobertura das dezenas
        total_jogos = len(indices_portfolio_atual) + 1
        frequencia_ideal = (total_jogos * 15) / 25
        score_dezenas = 0.0

        for dezena in self.set_cache[idx_candidato]:
            freq = dezenas_counter[dezena]
            if freq < frequencia_ideal:
                score_dezenas += 1.0
            else:
                score_dezenas += 1.0 / (freq + 1)

        score_dezenas /= 15

        # Cluster e Hash
        score_cluster = 1 / (cluster_counter[candidato.get("cluster_id")] + 1)
        score_hash = 1 / (hash_counter[candidato.get("hash_estrutura")] + 1)

        # Score final ponderado
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
        tamanho_portfolio: int
    ) -> List[Dict[str, Any]]:
        
        start_time = time.perf_counter()
        logger.info("Iniciando seleção de portfólio (%d candidatos)", len(candidatos))

        if not candidatos or tamanho_portfolio <= 0:
            return []

        # Pré-processamento
        self.overlap_cache.clear()
        self.set_cache.clear()
        for idx, candidato in enumerate(candidatos):
            self.set_cache[idx] = set(candidato["numeros"])

        estado = PortfolioState()
        indices_escolhidos = set()
        indices_portfolio = []

        # Primeiro jogo = maior score
        primeiro_idx = max(
            range(len(candidatos)),
            key=lambda i: candidatos[i].get("score", 0)
        )
        primeiro = candidatos[primeiro_idx]
        estado.adicionar(primeiro)
        indices_escolhidos.add(primeiro_idx)
        indices_portfolio.append(primeiro_idx)

        logger.info("Primeiro jogo escolhido | Score %.4f", primeiro.get("score", 0))

        # Seleção greedy
        while len(estado.jogos) < tamanho_portfolio and len(indices_escolhidos) < len(candidatos):
            self.telemetry["iterations"] += 1
            pesos = self.obter_pesos_papel(len(estado.jogos))

            melhor_idx = None
            melhor_score = -float('inf')

            for idx, candidato in enumerate(candidatos):
                if idx in indices_escolhidos:
                    continue

                self.telemetry["candidates_evaluated"] += 1

                ganho = self.calcular_ganho_marginal(
                    candidato=candidato,
                    idx_candidato=idx,
                    indices_portfolio_atual=indices_portfolio,
                    dezenas_counter=estado.dezenas_counter,
                    cluster_counter=estado.cluster_counter,
                    hash_counter=estado.hash_counter,
                    pesos=pesos
                )

                if ganho > melhor_score:
                    melhor_score = ganho
                    melhor_idx = idx

            if melhor_idx is None:
                break

            escolhido = candidatos[melhor_idx]
            estado.adicionar(escolhido)
            indices_escolhidos.add(melhor_idx)
            indices_portfolio.append(melhor_idx)

            logger.info(
                "Iteração %d | Escolhido=%d | Ganho=%.4f",
                self.telemetry["iterations"], melhor_idx, melhor_score
            )

        # Finaliza telemetria
        end_time = time.perf_counter()
        self.calcular_telemetria_final(estado, start_time, end_time)

        return estado.jogos

    def calcular_telemetria_final(self, estado: PortfolioState, inicio: float, fim: float):
        self.telemetry["execution_time_ms"] = (fim - inicio) * 1000

        if not estado.jogos:
            return

        scores = [j.get("score", 0) for j in estado.jogos]

        self.telemetry.update({
            "score_medio": sum(scores) / len(scores),
            "score_minimo": min(scores),
            "score_maximo": max(scores),
            "desvio_padrao_score": float(np.std(scores)) if len(scores) > 1 else 0.0,
            "clusters_usados": len(estado.cluster_counter),
            "hashes_unicos": len(estado.hash_counter),
            "dezenas_cobertas": len(estado.dezenas_counter),
            "frequencia_maxima": max(estado.dezenas_counter.values()) if estado.dezenas_counter else 0,
            "frequencia_minima": min(estado.dezenas_counter.values()) if estado.dezenas_counter else 0,
        })

        # Overlap médio
        overlaps = []
        for i in range(len(estado.jogos)):
            for j in range(i + 1, len(estado.jogos)):
                overlap = len(set(estado.jogos[i]["numeros"]) & set(estado.jogos[j]["numeros"]))
                overlaps.append(overlap)

        self.telemetry["overlap_medio"] = sum(overlaps) / len(overlaps) if overlaps else 0

        # Score geral do portfólio
        self.telemetry["portfolio_score"] = (
            self.telemetry["score_medio"] * 0.40 +
            ((15 - self.telemetry["overlap_medio"]) / 15) * 0.60
        )

        logger.info(
            "Portfólio concluído | %d jogos | Score Geral %.4f",
            len(estado.jogos), self.telemetry["portfolio_score"]
        )


# ==========================================================
# TESTE LOCAL
# ==========================================================
if __name__ == "__main__":
    exemplos = [
        {
            "numeros": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
            "score": 1.42,
            "score_potencial": 0.88,
            "cluster_id": 1,
            "hash_estrutura": "A"
        },
        {
            "numeros": [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],
            "score": 1.30,
            "score_potencial": 0.74,
            "cluster_id": 2,
            "hash_estrutura": "B"
        },
        {
            "numeros": [1,3,5,7,9,11,13,15,17,19,21,22,23,24,25],
            "score": 1.55,
            "score_potencial": 0.91,
            "cluster_id": 3,
            "hash_estrutura": "C"
        }
    ]

    engine = PortfolioEngine()
    portfolio = engine.selecao_greedy_inteligente(
        candidatos=exemplos,
        tamanho_portfolio=2
    )

    print("\n===== PORTFÓLIO =====")
    for i, jogo in enumerate(portfolio, 1):
        print(f"{i}: score={jogo['score']:.3f} -> {jogo['numeros']}")

    print("\n===== TELEMETRIA =====")
    for k, v in engine.telemetry.items():
        print(f"{k}: {v}")
