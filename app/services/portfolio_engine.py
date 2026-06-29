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
# LOG
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("LotofacilPortfolioEngine")


# ==========================================================
# CONFIGURAÇÃO DOS PAPÉIS (AJUSTADA PARA SEU NOVO LAYOUT)
# ==========================================================
DEFAULT_PORTFOLIO_CONFIG = {
    "ELITE": {           # Jogos 1-3 → Máxima probabilidade
        "range": range(0, 3),
        "weight_ensemble": 0.58,
        "weight_diversity": 0.07,
        "weight_tens_coverage": 0.12,
        "weight_cluster": 0.10,
        "weight_hash": 0.05,
        "weight_roi": 0.08,
    },
    "BALANCEADO": {      # Jogos 4-7 → Cobertura estatística
        "range": range(3, 7),
        "weight_ensemble": 0.42,
        "weight_diversity": 0.18,
        "weight_tens_coverage": 0.18,
        "weight_cluster": 0.10,
        "weight_hash": 0.05,
        "weight_roi": 0.07,
    },
    "EXPLORADOR": {      # Jogos 8-9 → Padrões pouco utilizados
        "range": range(7, 9),
        "weight_ensemble": 0.25,
        "weight_diversity": 0.35,
        "weight_tens_coverage": 0.20,
        "weight_cluster": 0.10,
        "weight_hash": 0.05,
        "weight_roi": 0.05,
    },
    "EXTREMO": {         # Jogo 10 → Máxima cobertura + baixa sobreposição
        "range": range(9, 999),
        "weight_ensemble": 0.15,
        "weight_diversity": 0.50,
        "weight_tens_coverage": 0.25,
        "weight_cluster": 0.05,
        "weight_hash": 0.05,
        "weight_roi": 0.00,
    }
}


# ==========================================================
# ENGINE PRINCIPAL
# ==========================================================
class PortfolioEngine:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.papeis = tuple(self.config.items())
        
        self.set_cache: Dict[int, set[int]] = {}
        self.overlap_cache: Dict[tuple, int] = {}
        self.random = random.Random()
        self.max_overlap = 11                    # Ajustado para bom equilíbrio

        self.telemetry = {
            "execution_time_ms": 0.0,
            "iterations": 0,
            "candidates_evaluated": 0,
            "score_medio": 0.0,
            "score_minimo": 0.0,
            "score_maximo": 0.0,
            "desvio_padrao_score": 0.0,
            "overlap_medio": 0.0,
            "clusters_usados": 0,
            "hashes_unicos": 0,
            "dezenas_cobertas": 0,
            "frequencia_maxima": 0,
            "frequencia_minima": 0,
            "portfolio_score": 0.0
        }

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
                    return -9999.0
                soma_distancias += (15 - overlap)
            score_diversidade = (soma_distancias / len(indices_portfolio_atual)) / 15.0

        # Cobertura de dezenas
        total_jogos = len(indices_portfolio_atual) + 1
        freq_ideal = (total_jogos * 15) / 25.0
        score_dezenas = 0.0
        for dezena in self.set_cache[idx_candidato]:
            freq = dezenas_counter[dezena]
            if freq < freq_ideal - 0.5:
                score_dezenas += 1.4
            elif freq < freq_ideal + 1.5:
                score_dezenas += 1.0
            else:
                score_dezenas += 0.5
        score_dezenas /= 15

        # Cluster e Hash
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
        tamanho_portfolio: int = 10,
        ultimos_palpites: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        
        start_time = time.perf_counter()
        logger.info(f"Iniciando seleção de portfólio ({len(candidatos)} candidatos)")

        if not candidatos or tamanho_portfolio <= 0:
            return []

        # Cache de sets
        self.overlap_cache.clear()
        self.set_cache.clear()
        for idx, cand in enumerate(candidatos):
            self.set_cache[idx] = set(cand["numeros"])

        estado = PortfolioState()
        indices_escolhidos = set()

        # ====================== INCLUI OS 2 ÚLTIMOS PALPITES ======================
        if ultimos_palpites:
            for i, palpite in enumerate(ultimos_palpites[:2]):
                if not palpite or "numeros" not in palpite:
                    continue
                for idx, cand in enumerate(candidatos):
                    if set(cand["numeros"]) == set(palpite["numeros"]):
                        estado.adicionar(cand)
                        indices_escolhidos.add(idx)
                        logger.info(f"Último palpite {i+1} incluído como âncora")
                        break

        # Preenche o restante respeitando os papéis
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
                    indices_portfolio_atual=list(indices_escolhidos),
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

        # Finaliza
        end_time = time.perf_counter()
        self.calcular_telemetria_final(estado, start_time, end_time)
        return estado.jogos

    def calcular_telemetria_final(self, estado: PortfolioState, inicio: float, fim: float):
        self.telemetry["execution_time_ms"] = (fim - inicio) * 1000

        if not estado.jogos:
            return

        scores = [j.get("score", 0.0) for j in estado.jogos]

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

        self.telemetry["overlap_medio"] = sum(overlaps) / len(overlaps) if overlaps else 0.0

        self.telemetry["portfolio_score"] = (
            self.telemetry["score_medio"] * 0.40 +
            ((15 - self.telemetry["overlap_medio"]) / 15) * 0.60
        )

        logger.info(
            "Portfólio concluído | %d jogos | Score Geral: %.4f | Overlap Médio: %.2f",
            len(estado.jogos), self.telemetry["portfolio_score"], self.telemetry["overlap_medio"]
        )


# ==========================================================
# TESTE / USO
# ==========================================================
if __name__ == "__main__":
    # Exemplo de uso
    engine = PortfolioEngine()

    # Seus candidatos vindos do modelo preditivo
    candidatos = [
        # ... seus jogos aqui
    ]

    ultimos_palpites = [
        # Coloque aqui seus 2 últimos palpites
        {"numeros": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], "score": 1.45, "cluster_id": 1, "hash_estrutura": "A"},
        {"numeros": [5,6,7,8,9,10,11,12,13,14,15,16,17,18,19], "score": 1.52, "cluster_id": 2, "hash_estrutura": "B"}
    ]

    portfolio = engine.selecao_greedy_inteligente(
        candidatos=candidatos,
        tamanho_portfolio=10,
        ultimos_palpites=ultimos_palpites
    )

    print("\n===== PORTFÓLIO FINAL =====")
    for i, jogo in enumerate(portfolio, 1):
        print(f"Jogo {i:2d} | Score {jogo.get('score', 0):.3f} | {sorted(jogo['numeros'])}")

    print("\n===== TELEMETRIA =====")
    for k, v in engine.telemetry.items():
        print(f"{k}: {v}")
