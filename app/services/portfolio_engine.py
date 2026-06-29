import logging
import time
from collections import Counter
from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class PortfolioState:
    """
    Estado incremental do portfólio.

    Evita recalcular todas as métricas a cada iteração.
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

        self.score_total += candidato.get("score", 0)

# Configuração de logs profissional
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LotofacilPortfolioEngine")

DEFAULT_PORTFOLIO_CONFIG = {

    "ELITE": {
        "weight_ensemble":0.50,
        "weight_diversity":0.10,
        "weight_tens":0.10,
        "weight_cluster":0.10,
        "weight_hash":0.10,
        "weight_roi":0.10
    },

    "BALANCEADO": {
        "weight_ensemble":0.35,
        "weight_diversity":0.20,
        "weight_tens":0.15,
        "weight_cluster":0.10,
        "weight_hash":0.10,
        "weight_roi":0.10
    },

    "EXPLORADOR": {
        "weight_ensemble":0.20,
        "weight_diversity":0.30,
        "weight_tens":0.20,
        "weight_cluster":0.15,
        "weight_hash":0.10,
        "weight_roi":0.05
    },

    "EXTREMO": {
        "weight_ensemble":0.05,
        "weight_diversity":0.50,
        "weight_tens":0.30,
        "weight_cluster":0.05,
        "weight_hash":0.10,
        "weight_roi":0.00
    }

}
class PortfolioEngine:
    """
    Engine ultra-otimizada para seleção de portfólios da Lotofácil.
    Abordagem puramente baseada em conjuntos (sets), contadores e avaliação incremental marginal.
    """
    def __init__(self, config=None):

    self.config = config or DEFAULT_PORTFOLIO_CONFIG

    self.overlap_cache = {}

    self.set_cache = {}

    self.telemetry = {

        "execution_time_ms":0,

        "iterations":0,

        "candidates_evaluated":0,

        "score_medio":0,

        "score_minimo":0,

        "score_maximo":0,

        "desvio_padrao_score":0,

        "overlap_medio":0,

        "clusters_usados":0,

        "hashes_unicos":0,

        "dezenas_cobertas":0,

        "frequencia_maxima":0,

        "frequencia_minima":0,

        "portfolio_score":0

    }

    # Ajuste 1 e 4: Substituição do Jaccard e NumPy por operações nativas de Set e distância interpretável
    def calcular_distancia(self, a: set, b: set) -> int:
        """Retorna a distância pura baseada no overlap (15 - overlap)."""
        return 15 - len(a & b)

    def obter_pesos_papel(self, indice_atual: int) -> Dict[str, float]:
        """Identifica qual papel aplicar com base na posição atual de inserção no portfólio."""
        for papel, dados in self.config_papeis.items():
            if indice_atual in dados["range"]:
                return dados
        return self.config_papeis["EXTREMO"] # Fallback de segurança

    def calcular_ganho_marginal(self, 
                                candidato: Dict[str, Any], 
                                conjunto_cand: set,
                                portfolio_atual: List[Dict[str, Any]], 
                                dezenas_counter: Counter, 
                                cluster_counter: Counter, 
                                hash_counter: Counter, 
                                pesos: Dict[str, float]) -> float:
        """
        Ajuste 11: Calcula apenas o impacto marginal da adição do candidato.
        Evita recalcular o histórico completo, resultando em altíssima performance.
        """
        # --- 1. Score Ensemble & ROI (Ajuste 2, 8 e 9) ---
        score_ensemble = candidato.get("score", 0.0)
        # Simulando ou acessando o método do Palpiteiro solicitado no Ajuste 9
        score_roi = candidato.get("score_potencial", 0.0) 

        # --- 2. Diversidade Marginal (Ajuste 4) ---
        if not portfolio_atual:
            score_diversidade = 1.0
        else:
            # Distância interpretável média em relação aos já selecionados (normalizada de 0 a 1)
            distancia_acumulada = sum(15 - len(conjunto_cand & jogo["_set_numeros"]) for jogo in portfolio_atual)
            score_diversidade = (distancia_acumulada / len(portfolio_atual)) / 15.0

        # --- 3. Cobertura de Dezenas Marginal via Frequência (Ajuste 5) ---
        # Penaliza dezenas que já apareceram muito e bonifica dezenas sub-representadas
        total_jogos = len(portfolio_atual) + 1
        frequencia_alvo = (total_jogos * 15) / 25
        score_dezenas_acumulado = 0.0
        
        for num in conjunto_cand:
            freq_atual = dezenas_counter[num]
            # Se a dezena ainda não estourou a média estatística ideal do grupo, ganha bônus
            if freq_atual < frequencia_alvo:
                score_dezenas_acumulado += 1.0
            else:
                score_dezenas_acumulado += (1.0 / (freq_atual + 1)) # Penalidade suave por saturação
        score_dezenas = score_dezenas_acumulado / 15

        # --- 4. Cobertura de Cluster Marginal (Ajuste 6) ---
        cluster_id = candidato.get("cluster_id")
        freq_cluster = cluster_counter[cluster_id]
        score_cluster = 1.0 / (freq_cluster + 1) # Penaliza se o cluster já estiver saturado no grupo

        # --- 5. Hash Estrutural Marginal (Ajuste 7) ---
        hash_est = candidato.get("hash_structure")
        freq_hash = hash_counter[hash_est]
        score_hash = 1.0 / (freq_hash + 1) # Penaliza repetição do mesmo padrão estrito de desenho

        # --- Combinação Ponderada das Métricas Baseado no Papel Atual (Ajuste 8 e 10) ---
        score_marginal = (
            (score_ensemble * pesos["weight_ensemble"]) +
            (score_diversidade * pesos["weight_diversity"]) +
            (score_dezenas * pesos["weight_tens_coverage"]) +
            (score_cluster * pesos["weight_cluster"]) +
            (score_hash * pesos["weight_hash"]) +
            (score_roi * pesos["weight_roi"])
        )
        return score_marginal

    def selecao_greedy_inteligente(self, candidatos: List[Dict[str, Any]], tamanho_portfolio: int) -> List[Dict[str, Any]]:
        """
        Executa a montagem do portfólio aplicando as otimizações incrementais e papéis dinâmicos.
        """
        start_time = time.perf_counter()
        logger.info(f"Iniciando seleção para Lotofácil. Candidatos estruturados: {len(candidatos)}")

        if not candidatos or tamanho_portfolio <= 0:
            return []

        # Pré-processamento dos candidatos para injetar a estrutura de set de forma única
        self.set_cache.clear()

        for idx,c in enumerate(candidatos):
        
            self.set_cache[idx]=set(c["numeros"])

        portfolio_selecionado: List[Dict[str, Any]] = []
        indices_escolhidos = set()

        # Contadores de estado global para ganho marginal (Ajuste 5 e 7)
        global_dezenas_counter = Counter()
        global_cluster_counter = Counter()
        global_hash_counter = Counter()

        # Ajuste 3: O primeiro jogo é obrigatoriamente o de maior score vindo do Ensemble
        primeiro_candidato = max(candidatos, key=lambda x: x["score"])
        primeiro_idx = candidatos.index(primeiro_candidato)
        
        portfolio_selecionado.append(primeiro_candidato)
        indices_escolhidos.add(primeiro_idx)
        
        # Atualiza os contadores com o primeiro jogo inserido
        global_dezenas_counter.update(primeiro_candidato["numeros"])
        global_cluster_counter[primeiro_candidato["cluster_id"]] += 1
        global_hash_counter[primeiro_candidato["hash_structure"]] += 1

        logger.info(f"Jogo 1 [ELITE] fixado pelo maior Score Ensemble: {primeiro_candidato['score']:.4f}")

        # Laço Incremental (Ajuste 11)
        while len(portfolio_selecionado) < tamanho_portfolio and len(indices_escolhidos) < len(candidatos):
            self.telemetry["iterations"] += 1
            
            idx_posicao_atual = len(portfolio_selecionado)
            pesos_do_papel = self.obter_pesos_papel(idx_posicao_atual)
            
            melhor_ganho = -1.0
            melhor_idx = -1

            for idx, cand in enumerate(candidatos):
                if idx in indices_escolhidos:
                    continue
                
                self.telemetry["candidates_evaluated"] += 1
                
                # Avaliação marginal ultra veloz sem mexer no portfólio real
                ganho = self.calcular_ganho_marginal(
                    candidato=cand,
                    conjunto_cand=cand["_set_numeros"],
                    portfolio_atual=portfolio_selecionado,
                    dezenas_counter=global_dezenas_counter,
                    cluster_counter=global_cluster_counter,
                    hash_counter=global_hash_counter,
                    pesos=pesos_do_papel
                )

                if ganho > melhor_ganho:
                    melhor_ganho = ganho
                    melhor_idx = idx

            if melhor_idx != -1:
                escolhido = candidatos[melhor_idx]
                portfolio_selecionado.append(escolhido)
                indices_escolhidos.add(melhor_idx)

                # Atualização incremental dos estados dos contadores
                global_dezenas_counter.update(escolhido["numeros"])
                global_cluster_counter[escolhido["cluster_id"]] += 1
                global_hash_counter[escolhido["hash_structure"]] += 1
                
                logger.info(f"Jogo {len(portfolio_selecionado)} adicionado | Index: {melhor_idx} | Ganho Marginal: {melhor_ganho:.4f}")
            else:
                break

        # Processamento final da telemetria (Ajuste 12)
        end_time = time.perf_counter()
        self.calcular_telemetria_final(portfolio_selecionado, global_dezenas_counter, global_cluster_counter, global_hash_counter, start_time, end_time)

        return portfolio_selecionado

    def calcular_telemetria_final(self, portfolio, dezenas_counter, cluster_counter, hash_counter, start, end):
        """Preenche o dicionário completo de telemetria para análise de performance e distribuição."""
        self.telemetry["execution_time_ms"] = (end - start) * 1000
        if not portfolio:
            return

        total_jogos = len(portfolio)
        self.telemetry["score_medio"] = sum(j["score"] for j in portfolio) / total_jogos
        self.telemetry["clusters_usados"] = len([c for c, v in cluster_counter.items() if v > 0])
        self.telemetry["hashes_unicos"] = len([h for h, v in hash_counter.items() if v > 0])
        self.telemetry["dezenas_cobertas"] = len([d for d, v in dezenas_counter.items() if v > 0])
        self.telemetry["frequencia_maxima"] = max(dezenas_counter.values()) if dezenas_counter else 0
        self.telemetry["frequencia_minima"] = min(dezenas_counter.values()) if len(dezenas_counter) == 25 else 0
        
        # Overlap médio interno do portfólio
        overlaps = []
        for i in range(total_jogos):
            for j in range(i + 1, total_jogos):
                overlaps.append(len(portfolio[i]["_set_numeros"] & portfolio[j]["_set_numeros"]))
        self.telemetry["overlap_medio"] = sum(overlaps) / len(overlaps) if overlaps else 0.0
        
        # Nota simplificada agregada de eficiência do portfólio para fins de telemetria
        self.telemetry["portfolio_score"] = (self.telemetry["score_medio"] * 0.4) + ((15 - self.telemetry["overlap_medio"]) / 15 * 0.6)
        
        logger.info(f"Telemetria do Processamento Concluída com Sucesso.")


# --- SIMULAÇÃO DO AMBIENTE PALPITEIRO (Ajuste 2) ---
if __name__ == "__main__":
    # Dicionários complexos simulando a saída real do gerador do projeto
    palpites_palpiteiro = [
        {"numeros":, "score": 1.45, "score_potencial": 0.85, "cluster_id": 1, "hash_structure": "STRUC_A"},
        {"numeros":, "score": 1.10, "score_potencial": 0.60, "cluster_id": 1, "hash_structure": "STRUC_B"},
        {"numeros":, "score": 1.30, "score_potencial": 0.90, "cluster_id": 2, "hash_structure": "STRUC_A"},
        {"numeros":, "score": 1.25, "score_potencial": 0.75, "cluster_id": 3, "hash_structure": "STRUC_C"},
        {"numeros":, "score": 0.95, "score_potencial": 0.40, "cluster_id": 4, "hash_structure": "STRUC_D"},
        {"numeros":, "score": 1.05, "score_potencial": 0.55, "cluster_id": 2, "hash_structure": "STRUC_E"},
    ]

    engine = PortfolioEngine()
    
    # Criando um portfólio contendo os 4 melhores jogos estratégicos combinados
    portfolio_final = engine.selecao_greedy_inteligente(candidatos=palpites_palpiteiro, tamanho_portfolio=4)

    print("\n=============================================")
    print("      PORTFÓLIO ESTRUTURADO SELECIONADO      ")
    print("=============================================")
    for idx, jogo in enumerate(portfolio_final):
        papel_nome = "ELITE" if idx < 3 else "BALANCEADO"
        print(f"Jogo {idx+1} [{papel_nome}] -> {jogo['numeros']} | Score Ensemble: {jogo['score']}")

    print("\n=============================================")
    print("            DICIONÁRIO DE TELEMETRIA         ")
    print("=============================================")
    for k, v in engine.telemetry.items():
        print(f"{k}: {v}")


