import logging
import time
from collections import Counter
from typing import List, Dict, Any
from dataclasses import dataclass, field

# ==========================================================
# ESTADO DO PORTFÓLIO
# ==========================================================

@dataclass
class PortfolioState:
    """
    Estado incremental do portfólio.
    Mantém todos os acumuladores para evitar
    recálculos durante a seleção Greedy.
    """
    jogos: List[Dict] = field(default_factory=list)
    dezenas_counter: Counter = field(default_factory=Counter)
    cluster_counter: Counter = field(default_factory=Counter)
    hash_counter: Counter = field(default_factory=Counter)
    score_total: float = 0.0

    def adicionar(self, candidato: Dict):
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
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("LotofacilPortfolioEngine")

# ==========================================================
# CONFIGURAÇÃO DOS PAPÉIS DO PORTFÓLIO
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
    def __init__(self, config=None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG

        # cache dos conjuntos
        self.set_cache = {}

        # cache dos overlaps
        self.overlap_cache = {}

        # telemetria
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
    # ======================================================
    def obter_overlap(self, idx_a: int, idx_b: int) -> int:
        """
        Retorna o overlap utilizando cache.
        """
        chave = (idx_a, idx_b) if idx_a < idx_b else (idx_b, idx_a)
        if chave in self.overlap_cache:
            return self.overlap_cache[chave]
        overlap = len(self.set_cache[idx_a] & self.set_cache[idx_b])
        self.overlap_cache[chave] = overlap
        return overlap
    # ======================================================
    def calcular_distancia(self, a: set, b: set) -> int:
        """
        Distância baseada no overlap.
        15 = totalmente diferentes
         0 = iguais
        """
        return 15 - len(a & b)
    # ==========================================================
    # PAPEL DO JOGO NO PORTFÓLIO
    # ==========================================================
    
    def obter_pesos_papel(self, indice: int) -> Dict[str, float]:
        """
        Retorna o conjunto de pesos conforme a posição
        do jogo dentro do portfólio.
        """
    
        for _, dados in self.config.items():
    
            if indice in dados["range"]:
                return dados
    
        return self.config["EXTREMO"]
      
    # ==========================================================
    # SCORE MARGINAL
    # ==========================================================
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
    
        # --------------------------------------------------
        # SCORE BASE
        # --------------------------------------------------
        score_ensemble = candidato.get("score", 0.0)
    
        score_roi = candidato.get(
            "roi_estimado",
            candidato.get("score_potencial", 0.0)
        )
    
        # --------------------------------------------------
        # DIVERSIDADE
        # --------------------------------------------------
    
        if not indices_portfolio_atual:
    
            score_diversidade = 1.0
    
        else:
    
            soma_distancias = 0
    
            for idx_existente in indices_portfolio_atual:
    
                overlap = self.obter_overlap(
                    idx_candidato,
                    idx_existente
                )
    
                soma_distancias += (15 - overlap)
    
            score_diversidade = (
                soma_distancias /
                len(indices_portfolio_atual)
            ) / 15.0
    
        # --------------------------------------------------
        # COBERTURA DAS 25 DEZENAS
        # --------------------------------------------------
    
        total_jogos = len(indices_portfolio_atual) + 1
        frequencia_ideal = (total_jogos * 15) / 25
        score_dezenas = 0.0
    
        for dezena in self.set_cache[idx_candidato]:
    
            freq = dezenas_counter[dezena]
    
            if freq < frequencia_ideal:
    
                score_dezenas += 1.0
    
            else:
    
                score_dezenas += 1 / (freq + 1)
    
        score_dezenas /= 15
    
        # --------------------------------------------------
        # CLUSTER
        # --------------------------------------------------
    
        cluster = candidato.get("cluster_id")
    
        score_cluster = 1 / (
            cluster_counter[cluster] + 1
        )
    
        # --------------------------------------------------
        # HASH ESTRUTURAL
        # --------------------------------------------------
    
        hash_estrutura = candidato.get("hash_estrutura")
    
        score_hash = 1 / (
            hash_counter[hash_estrutura] + 1
        )
    
        # --------------------------------------------------
        # SCORE FINAL
        # --------------------------------------------------
    
        return (
    
            score_ensemble * pesos["weight_ensemble"]
    
            +
    
            score_diversidade * pesos["weight_diversity"]
    
            +
    
            score_dezenas * pesos["weight_tens_coverage"]
    
            +
    
            score_cluster * pesos["weight_cluster"]
    
            +
    
            score_hash * pesos["weight_hash"]
    
            +
    
            score_roi * pesos["weight_roi"]
    
        )


        def selecao_greedy_inteligente(
        self,
        candidatos: List[Dict[str, Any]],
        tamanho_portfolio: int
    ) -> List[Dict[str, Any]]:

        start_time = time.perf_counter()

        logger.info(
            "Iniciando seleção de portfólio (%d candidatos)",
            len(candidatos)
        )

        if not candidatos or tamanho_portfolio <= 0:
            return []

        # -------------------------------------------------------
        # Pré-processamento
        # -------------------------------------------------------

        self.overlap_cache.clear()
        self.set_cache.clear()

        for idx, candidato in enumerate(candidatos):
            self.set_cache[idx] = set(candidato["numeros"])

        estado = PortfolioState()

        indices_escolhidos = set()
        indices_portfolio = []

        # -------------------------------------------------------
        # Primeiro jogo = maior score do Ensemble
        # -------------------------------------------------------

        primeiro_idx = max(
            range(len(candidatos)),
            key=lambda i: candidatos[i]["score"]
        )

        primeiro = candidatos[primeiro_idx]

        estado.adicionar(primeiro)

        indices_escolhidos.add(primeiro_idx)
        indices_portfolio.append(primeiro_idx)

        logger.info(
            "Primeiro jogo escolhido | Score %.4f",
            primeiro["score"]
        )

        # -------------------------------------------------------
        # Seleção Greedy
        # -------------------------------------------------------

        while (
            len(estado.jogos) < tamanho_portfolio
            and len(indices_escolhidos) < len(candidatos)
        ):

            self.telemetry["iterations"] += 1

            pesos = self.obter_pesos_papel(len(estado.jogos))

            melhor_idx = None
            melhor_score = -1

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
                self.telemetry["iterations"],
                melhor_idx,
                melhor_score
            )

        # -------------------------------------------------------
        # Telemetria
        # -------------------------------------------------------

        end_time = time.perf_counter()

        self.calcular_telemetria_final(
            estado,
            start_time,
            end_time
        )

        return estado.jogos

    # ==========================================================
    # TELEMETRIA
    # ==========================================================

    def calcular_telemetria_final(
        self,
        estado: PortfolioState,
        inicio: float,
        fim: float
    ):

        self.telemetry["execution_time_ms"] = (fim - inicio) * 1000

        if not estado.jogos:
            return

        scores = [j["score"] for j in estado.jogos]

        self.telemetry["score_medio"] = sum(scores) / len(scores)
        self.telemetry["score_minimo"] = min(scores)
        self.telemetry["score_maximo"] = max(scores)

        self.telemetry["clusters_usados"] = len(estado.cluster_counter)
        self.telemetry["hashes_unicos"] = len(estado.hash_counter)
        self.telemetry["dezenas_cobertas"] = len(estado.dezenas_counter)

        self.telemetry["frequencia_maxima"] = (
            max(estado.dezenas_counter.values())
            if estado.dezenas_counter
            else 0
        )

        self.telemetry["frequencia_minima"] = (
            min(estado.dezenas_counter.values())
            if estado.dezenas_counter
            else 0
        )

        # Overlap médio
        overlaps = []

        for i in range(len(estado.jogos)):
            for j in range(i + 1, len(estado.jogos)):

                a = set(estado.jogos[i]["numeros"])
                b = set(estado.jogos[j]["numeros"])

                overlaps.append(len(a & b))

        self.telemetry["overlap_medio"] = (
            sum(overlaps) / len(overlaps)
            if overlaps
            else 0
        )

        self.telemetry["portfolio_score"] = (
            self.telemetry["score_medio"] * 0.40
            + ((15 - self.telemetry["overlap_medio"]) / 15) * 0.60
        )

        logger.info(
            "Portfólio concluído | %d jogos | Score %.4f",
            len(estado.jogos),
            self.telemetry["portfolio_score"]
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
