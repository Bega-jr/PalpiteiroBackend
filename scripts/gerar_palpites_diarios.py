import sys
import json
import random
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
from app.services.recompensa_evolutiva_service import calcular_recompensa_evolutiva
from app.services.feature_store_service import gerar_features_jogo
from app.services.clusterizacao_service import identificar_cluster_jogo
from app.services.diversidade_service import diversidade_avancada_ok
from app.services.montecarlo_service import simular_probabilidade_jogo
from app.services.motores_ensemble_service import calcular_score_ensemble
from scripts.processamento_diario_lotofacil import carregar_historico, extrair_estrutura

VERSAO = "v19.7-perfis-cobertura-total"

# Quantidade de palpites selecionados por execução.
QTD_FINAL = 20
QTD_COMPARACAO = 20

MAX_TENTATIVAS = 180_000
MAX_CANDIDATOS = 600
MIN_CANDIDATOS_POOL = 250
CUSTO_POR_APOSTA = 3.50

MAX_OCORRENCIAS_GLOBAL = 8
PESO_PENALIDADE_SATURACAO = 0.020

# ---- Matriz + Cobertura (v19.6) ----
TAMANHO_MATRIZ = 18
PROPORCAO_MATRIZ = 0.78
COBERTURA_MINIMA_MATRIZ = 0.88

# Metas iniciais dos perfis; a classificação é calculada pelos indicadores.
METAS_PERFIS = {"conservador": 6, "equilibrado": 8, "agressivo": 6}

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}
MOLDURA = {1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25}

# ======================================================
# NOVO: Funções de Suporte (ROI + Modo de Variação)
# ======================================================
def calcular_roi(quantidade_palpites=None):
    """
    Calcula apenas o investimento estimado da geração.
    O ROI verdadeiro depende da premiação real após o concurso.
    """
    qty = (
        quantidade_palpites
        if quantidade_palpites is not None
        else QTD_FINAL
    )
    total_custo = qty * CUSTO_POR_APOSTA

    custo_base = min(qty, QTD_COMPARACAO) * CUSTO_POR_APOSTA
    custo_adicional = max(0, qty - QTD_COMPARACAO) * CUSTO_POR_APOSTA

    print(
        f"💰 Investimento estimado: R$ {total_custo:.2f} "
        f"({qty} jogos × R$ {CUSTO_POR_APOSTA:.2f})"
    )

    if qty > QTD_COMPARACAO:
        print(
            f"   Grupo-base ({QTD_COMPARACAO}): R$ {custo_base:.2f} | "
            f"Adicionais ({qty - QTD_COMPARACAO}): R$ {custo_adicional:.2f}"
        )

    return total_custo

def aplicar_entropia_modo(score_final, modo_variacao):
    """Aplica variação controlada. v19.5: entropia um pouco menor para preservar sinal de 13/14."""
    if modo_variacao == "agressivo":
        return score_final * random.uniform(0.85, 1.15)
    elif modo_variacao == "conservador":
        return score_final * random.uniform(0.98, 1.02)
    else:  # moderado
        return score_final * random.uniform(0.97, 1.03)

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

def classificar_dezenas_populares(historico):
    if len(historico) < 10:
        raise ValueError(
            "São necessários 10 concursos históricos para classificar as dezenas."
        )

    frequencias = {numero: 0 for numero in range(1, 26)}
    for concurso in historico[-10:]:
        numeros = concurso.get("numeros")
        if (
            not isinstance(numeros, list)
            or len(numeros) != 15
            or any(
                type(numero) is not int or not 1 <= numero <= 25
                for numero in numeros
            )
            or len(set(numeros)) != 15
        ):
            raise ValueError(
                f"Concurso {concurso.get('concurso')} não contém 15 dezenas válidas."
            )
        for numero in numeros:
            frequencias[numero] += 1

    ranking = sorted(
        frequencias,
        key=lambda numero: (-frequencias[numero], numero),
    )
    return set(ranking[:10]), set(ranking[-10:])

def calcular_flags_popularidade(numeros, mais_sorteados, menos_sorteados):
    return {
        "usa_mais_sorteados": any(numero in mais_sorteados for numero in numeros),
        "usa_menos_sorteados": any(numero in menos_sorteados for numero in numeros),
    }

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
    metricas = extrair_estrutura(jogo)
    chave = (
        round(sum(jogo) / 20) * 20,
        (metricas["pares"] // 2) * 2,
        (metricas["primos"] // 2) * 2,
        tuple(min(4, qtd) for qtd in metricas["linhas"]),
    )
    score = float(base.get(chave, 0.5))
    return score, score, score

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

def montar_msg_telegram(concurso_ref, linhas_palpites, matriz=None, cobertura=None):
    linhas = [
        "🟢 Pipeline Lotofácil v19.7-perfis-cobertura-total concluído!",
        "",
        f"🎯 Palpites gerados para o concurso {concurso_ref}",
        "📦 Geração por Matriz Reduzida + Cobertura inteligente",
        "📈 Foco em potencial real de 13/14 pontos",
        ""
    ]
    if matriz:
        linhas.append(f"🔢 Matriz ({len(matriz)}): {matriz}")
    if cobertura is not None:
        linhas.append(f"📊 Cobertura da matriz: {cobertura*100:.1f}%")
        linhas.append("")
    linhas.extend(linhas_palpites)
    return "\n".join(linhas)

def score_potencial_alto(jogo, historico, base_scores):
    """
    v19.5: Score focado em potencial real de 13/14 pontos.
    - Janela recente (40) com peso maior + janela longa (120)
    - Recompensa explícita por hits >= 13 e >= 14 no histórico
    - Penaliza jogos que raramente passam de 11-12
    - Mantém equilíbrio com quentes/frias e filtros estruturais
    """
    jogo_set = set(jogo)
    hits_recentes = []
    hits_longos = []
    hits_13_plus = 0
    hits_14_plus = 0
    total_avaliados = 0

    # Janela recente (mais relevante para regime atual)
    for concurso in historico[-40:]:
        resultado = set(concurso["numeros"])
        hits = len(jogo_set & resultado)
        total_avaliados += 1
        if hits >= 11:
            hits_recentes.append(hits)
        if hits >= 13:
            hits_13_plus += 1
        if hits >= 14:
            hits_14_plus += 1

    # Janela longa (estabilidade)
    for concurso in historico[-120:]:
        resultado = set(concurso["numeros"])
        hits = len(jogo_set & resultado)
        if hits >= 11:
            hits_longos.append(hits)

    # Fator histórico ponderado (recente tem mais peso)
    fator_recente = 1.0
    if hits_recentes:
        media_r = np.mean(hits_recentes)
        max_r = max(hits_recentes)
        # Bônus extra se já atingiu 13+ na janela recente
        bonus_alto = 0.15 if max_r >= 13 else (0.08 if max_r >= 12 else 0.0)
        fator_recente = (media_r * 0.55) + (max_r * 0.35) + bonus_alto

    fator_longo = 1.0
    if hits_longos:
        media_l = np.mean(hits_longos)
        max_l = max(hits_longos)
        fator_longo = (media_l * 0.6) + (max_l * 0.4)

    fator_historico = (fator_recente * 0.70) + (fator_longo * 0.30)

    # Taxa de hits altos (normalizada)
    taxa_13 = hits_13_plus / max(total_avaliados, 1)
    taxa_14 = hits_14_plus / max(total_avaliados, 1)
    bonus_taxa_alta = (taxa_13 * 1.8) + (taxa_14 * 3.5)  # 14 vale muito mais

    quentes = [n for n in jogo if base_scores.get((n,), 0) > 0.62]
    frias = [n for n in jogo if base_scores.get((n,), 0) < 0.42]
    filtros = calcular_filtros(jogo, historico[-1]["numeros"])

    # Soma ideal da Lotofácil costuma ficar entre ~170-210
    desvio_soma = abs(filtros["soma"] - 195) / 40.0
    score_soma = max(0.0, 1.0 - desvio_soma)

    score = (
        fator_historico * 0.42 +
        bonus_taxa_alta * 0.22 +
        (len(quentes) * 0.10 + len(frias) * 0.06) +
        score_soma * 0.12 +
        (10 - abs(filtros["pares"] - 7.5)) * 0.08
    )
    return float(score)


def score_historico_acertos(jogo, historico):
    """
    Novo em v19.5: mede diretamente quantos acertos altos
    o conjunto de dezenas já produziu no passado recente.
    Retorna um valor normalizado ~0.0 a ~2.5.
    """
    jogo_set = set(jogo)
    pontos = 0.0
    contagem = 0

    for concurso in historico[-60:]:
        hits = len(jogo_set & set(concurso["numeros"]))
        contagem += 1
        if hits >= 14:
            pontos += 4.0
        elif hits >= 13:
            pontos += 2.2
        elif hits >= 12:
            pontos += 1.0
        elif hits >= 11:
            pontos += 0.35

    if contagem == 0:
        return 0.8
    return float(pontos / contagem)


# ======================================================
# MATRIZ REDUZIDA + COBERTURA (v19.6)
# ======================================================
def calcular_atraso_dezenas(historico, janela=40):
    """Retorna dict {dezena: atraso} nos últimos 'janela' concursos."""
    atraso = {}
    for n in range(1, 26):
        cont = 0
        for concurso in reversed(historico[-janela:]):
            if n in concurso["numeros"]:
                break
            cont += 1
        atraso[n] = cont
    return atraso


def calcular_frequencia_ponderada(historico, janela=50):
    """Frequência com peso maior nos concursos mais recentes."""
    pesos = np.linspace(0.4, 1.0, min(janela, len(historico)))
    freq = Counter()
    for i, concurso in enumerate(historico[-janela:]):
        w = pesos[i] if i < len(pesos) else 1.0
        for n in concurso["numeros"]:
            freq[n] += w
    return freq


def construir_matriz_reduzida(historico, scores_dezenas, tamanho=TAMANHO_MATRIZ):
    """
    Constrói uma matriz de 18–21 dezenas priorizando:
    - Frequência ponderada recente
    - Atraso moderado (não extremo)
    - Frequência ponderada e score individual normalizado
    - Equilíbrio de paridade e moldura
    """
    freq = calcular_frequencia_ponderada(historico, janela=45)
    atraso = calcular_atraso_dezenas(historico, janela=35)

    scores_dezena = {}
    for n in range(1, 26):
        f = freq.get(n, 0)
        a = atraso.get(n, 0)
        s = scores_dezenas.get((n,), 0.5)

        # Atraso ideal: nem zero (muito quente) nem muito alto
        score_atraso = 1.0 - abs(a - 4.5) / 12.0
        score_atraso = max(0.15, score_atraso)

        scores_dezena[n] = (
            f * 0.38 +
            s * 0.32 +
            score_atraso * 0.22 +
            (0.08 if n in MOLDURA else 0.04)
        )

    # Ordena e pega as top + um pouco de exploração
    ordenadas = sorted(scores_dezena.items(), key=lambda x: -x[1])
    top = [n for n, _ in ordenadas[:tamanho - 3]]
    # Adiciona 2–3 dezenas de exploração (médio-atraso ou score médio)
    exploradoras = [n for n, _ in ordenadas[tamanho - 3: tamanho + 4]
                    if n not in top]
    random.shuffle(exploradoras)
    matriz = sorted(top + exploradoras[:3])[:tamanho]

    # Garante um mínimo de equilíbrio de paridade
    pares = sum(1 for n in matriz if n % 2 == 0)
    if pares < 7 or pares > 13:
        # troca a dezena mais fraca por uma do outro grupo
        candidatos_troca = [n for n in range(1, 26) if n not in matriz]
        random.shuffle(candidatos_troca)
        for cand in candidatos_troca:
            novo = sorted([x for x in matriz if x != matriz[-1]] + [cand])
            novos_pares = sum(1 for n in novo if n % 2 == 0)
            if 8 <= novos_pares <= 12:
                matriz = novo
                break

    return sorted(matriz)


def cobertura_matriz(jogos, matriz):
    """Retorna a fração de dezenas da matriz cobertas pelo conjunto de jogos."""
    if not jogos or not matriz:
        return 0.0
    usadas = set()
    for j in jogos:
        usadas.update(j)
    return len(usadas & set(matriz)) / len(matriz)


def score_cobertura_portfolio(candidato, finais, matriz):
    """
    Score auxiliar que favorece candidatos que trazem dezenas
    da matriz ainda pouco cobertas pelo portfolio atual.
    """
    if not matriz:
        return 0.0
    cobertas = set()
    for f in finais:
        cobertas.update(f["nums"] if isinstance(f, dict) else f)
    faltantes = set(matriz) - cobertas
    if not faltantes:
        return 0.15
    traz = len(set(candidato) & faltantes)
    return (traz / max(len(faltantes), 1)) * 1.4 + (traz * 0.08)



# ======================================================
# CLASSIFICAÇÃO OBJETIVA DOS PERFIS (v19.7)
# ======================================================
def _percentis(valores):
    """Normaliza valores em percentis [0, 1], preservando empates."""
    if not valores:
        return []
    ordenados = sorted(float(v) for v in valores)
    n = len(ordenados)
    if n == 1 or ordenados[0] == ordenados[-1]:
        return [0.5] * n
    saida = []
    for valor in valores:
        abaixo = sum(1 for x in ordenados if x < float(valor))
        iguais = sum(1 for x in ordenados if x == float(valor))
        saida.append((abaixo + (iguais - 1) / 2) / (n - 1))
    return saida


def calcular_indicadores_perfis(candidatos):
    """Calcula estabilidade, aderência, exploração e diversidade no pool."""
    if not candidatos:
        return

    # Frequência de estruturas e clusters no universo de candidatos.
    freq_hash = Counter(
        c.get("estrutura", {}).get("hash_estrutura") for c in candidatos
    )
    freq_cluster = Counter(str(c.get("cluster_id")) for c in candidatos)

    estabilidade_raw = [
        0.45 * float(c.get("score_contextual", 0))
        + 0.25 * float(c.get("score_previsibilidade", 0))
        + 0.30 * float(c.get("score_medio_real", 0))
        for c in candidatos
    ]
    aderencia_raw = [
        0.40 * float(c.get("score", 0))
        + 0.30 * float(c.get("score_potencial", 0))
        + 0.20 * float(c.get("score_hits_reais", 0))
        + 0.10 * float(c.get("score_mc", 0))
        for c in candidatos
    ]
    exploracao_raw = [
        1.0 / (1.0 + max(0, int(c.get("vezes_gerado", 0))))
        for c in candidatos
    ]
    diversidade_raw = [
        0.60 / max(1, freq_cluster[str(c.get("cluster_id"))])
        + 0.40 / max(1, freq_hash.get(c.get("estrutura", {}).get("hash_estrutura"), 1))
        for c in candidatos
    ]

    estabilidade = _percentis(estabilidade_raw)
    aderencia = _percentis(aderencia_raw)
    exploracao = _percentis(exploracao_raw)
    diversidade = _percentis(diversidade_raw)

    for i, c in enumerate(candidatos):
        est = estabilidade[i]
        ade = aderencia[i]
        exp = exploracao[i]
        div = diversidade[i]

        # Os perfis expressam prioridades diferentes, não probabilidades de acerto.
        centralidade = max(
            0.0,
            1.0 - (abs(est - 0.5) + abs(ade - 0.5)
                   + abs(exp - 0.5) + abs(div - 0.5)) / 2.0
        )
        scores = {
            "conservador": 0.45 * est + 0.40 * ade + 0.10 * div + 0.05 * exp,
            # Equilibrado premia desempenho intermediário e ausência de extremos.
            "equilibrado": (
                0.175 * est + 0.175 * ade + 0.175 * exp
                + 0.175 * div + 0.30 * centralidade
            ),
            "agressivo": 0.15 * est + 0.20 * ade + 0.35 * exp + 0.30 * div,
        }
        c["indicadores_perfil"] = {
            "estabilidade": round(est, 6),
            "aderencia": round(ade, 6),
            "exploracao": round(exp, 6),
            "diversidade": round(div, 6),
            "centralidade": round(centralidade, 6),
        }
        c["scores_perfil"] = {
            k: round(v, 6) for k, v in scores.items()
        }
        c["perfil"] = max(scores, key=scores.get)
        c["score_perfil"] = float(scores[c["perfil"]])


def selecionar_portfolio_perfis(candidatos, metas=None):
    """Seleciona os perfis pelas pontuações e exige cobertura das 25 dezenas."""
    metas = metas or METAS_PERFIS
    calcular_indicadores_perfis(candidatos)

    grupos = {
        perfil: [c for c in candidatos if c.get("perfil") == perfil]
        for perfil in metas
    }
    faltas = {
        perfil: meta - len(grupos.get(perfil, []))
        for perfil, meta in metas.items()
        if len(grupos.get(perfil, [])) < meta
    }
    if faltas:
        resumo = {k: len(v) for k, v in grupos.items()}
        raise RuntimeError(
            f"Pool insuficiente para cumprir as metas dos perfis. "
            f"Disponíveis={resumo}; metas={metas}; faltas={faltas}. "
            "Aumente o pool ou revise os filtros/limites de geração."
        )

    selecionados = []
    usados_ids = set()
    contagem = {perfil: 0 for perfil in metas}
    dezenas_universo = set(range(1, 26))

    # Seleção gulosa global: respeita a quota de cada perfil e dá prioridade
    # às dezenas ainda ausentes, sem abandonar a pontuação específica do perfil.
    while len(selecionados) < sum(metas.values()):
        faltantes = dezenas_universo - {
            n for item in selecionados for n in item["nums"]
        }
        melhor = None
        melhor_perfil = None
        melhor_score = float("-inf")

        for perfil, meta in metas.items():
            if contagem[perfil] >= meta:
                continue
            for cand in grupos[perfil]:
                ident = id(cand)
                if ident in usados_ids:
                    continue
                nums = set(cand["nums"])
                novas = len(nums & faltantes)
                overlap_max = max(
                    (len(nums & set(sel["nums"])) for sel in selecionados),
                    default=0
                )
                penalidade_overlap = max(0, overlap_max - 9) * 0.012
                # A cobertura tem peso suficiente para garantir representação
                # ampla, mas não substitui a avaliação de qualidade do perfil.
                score_selecao = (
                    float(cand["scores_perfil"][perfil])
                    + (novas / 15.0) * 0.30
                    - penalidade_overlap
                )
                if score_selecao > melhor_score:
                    melhor = cand
                    melhor_perfil = perfil
                    melhor_score = score_selecao

        if melhor is None:
            raise RuntimeError(
                f"Não foi possível completar {sum(metas.values())} seleções "
                "sem duplicar jogos."
            )

        melhor["perfil"] = melhor_perfil
        melhor["score_perfil"] = float(melhor["scores_perfil"][melhor_perfil])
        selecionados.append(melhor)
        usados_ids.add(id(melhor))
        contagem[melhor_perfil] += 1

    dezenas_usadas = {n for item in selecionados for n in item["nums"]}
    faltantes = sorted(dezenas_universo - dezenas_usadas)
    if faltantes:
        raise RuntimeError(
            f"Portfólio selecionado não cobre as 25 dezenas. Ausentes: {faltantes}. "
            "Nenhum palpite deve ser gravado."
        )

    # Ordena por perfil e depois pela pontuação específica, para facilitar auditoria.
    ordem = {"conservador": 0, "equilibrado": 1, "agressivo": 2}
    selecionados.sort(
        key=lambda c: (ordem.get(c.get("perfil"), 9), -c.get("score_perfil", 0))
    )
    return selecionados


def validar_portfolio_final(finais):
    """Validação final obrigatória imediatamente antes de montar o payload."""
    if len(finais) != QTD_FINAL:
        raise RuntimeError(
            f"Portfólio inválido: {len(finais)} jogos; esperado {QTD_FINAL}."
        )
    combinacoes = set()
    dezenas = set()
    for idx, item in enumerate(finais, 1):
        nums = item.get("nums", [])
        if len(nums) != 15 or len(set(nums)) != 15:
            raise RuntimeError(f"Jogo {idx} não possui 15 dezenas únicas.")
        if any(not isinstance(n, int) or n < 1 or n > 25 for n in nums):
            raise RuntimeError(f"Jogo {idx} contém dezena fora do intervalo 1..25.")
        chave = tuple(sorted(nums))
        if chave in combinacoes:
            raise RuntimeError(f"Jogo duplicado detectado na posição {idx}.")
        combinacoes.add(chave)
        dezenas.update(nums)
    ausentes = sorted(set(range(1, 26)) - dezenas)
    if ausentes:
        raise RuntimeError(f"Cobertura incompleta: dezenas ausentes {ausentes}.")
    contagem = Counter(item.get("perfil") for item in finais)
    if any(contagem.get(perfil, 0) != qtd for perfil, qtd in METAS_PERFIS.items()):
        raise RuntimeError(
            f"Distribuição de perfis inválida: {dict(contagem)}; metas={METAS_PERFIS}."
        )
    return contagem

# ======================================================
# MOTOR DE GERAÇÃO - Versão Modulada para o Meta-Validador
# ======================================================
def executar_motor_geracao(concurso_alvo=None, modo_variacao="moderado"):
    inicio_execucao = time.time()
    supabase = get_supabase()
    print(f"🚀 {VERSAO} - Modo: {modo_variacao.upper()} | Matriz + Cobertura + Foco 13/14")

    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()
    hist = carregar_historico()
    ultimo = hist[-1]["numeros"]
    dezenas_mais_sorteadas, dezenas_menos_sorteadas = (
        classificar_dezenas_populares(hist)
    )
    
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

    scores_padroes, _ = calcular_score_combinacoes_reais()
    if not scores_padroes:
        raise RuntimeError("Não foi possível carregar os scores de padrões.")

    score_min = min(scores_padroes.values())
    score_max = max(scores_padroes.values())
    score_range = score_max - score_min
    base_scores = {
        chave: (
            (float(score) - score_min) / score_range
            if score_range
            else 0.5
        )
        for chave, score in scores_padroes.items()
    }

    frequencias_dezenas = calcular_frequencia_ponderada(hist, janela=120)
    frequencia_min = min(frequencias_dezenas.get(n, 0) for n in range(1, 26))
    frequencia_max = max(frequencias_dezenas.get(n, 0) for n in range(1, 26))
    frequencia_range = frequencia_max - frequencia_min
    scores_dezenas = {
        (n,): (
            (frequencias_dezenas.get(n, 0) - frequencia_min) / frequencia_range
            if frequencia_range
            else 0.5
        )
        for n in range(1, 26)
    }
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
    
    print(
        f"✅ Estruturas carregadas: "
        f"{len(memoria_cache)}"
    )

    # =====================================================
    # MATRIZ REDUZIDA (v19.6)
    # =====================================================
    matriz = construir_matriz_reduzida(hist, scores_dezenas, tamanho=TAMANHO_MATRIZ)
    print(f"📦 Matriz reduzida ({len(matriz)} dezenas): {matriz}")

    # Geração
    candidatos = []
    usados = {tuple(sorted(h["numeros"])) for h in hist}
    contador_dezenas = Counter()
    
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

    tentativas_realizadas = 0
    for tentativa in range(MAX_TENTATIVAS):
        tentativas_realizadas = tentativa + 1
        if len(candidatos) >= MAX_CANDIDATOS:
            break
        # Verifica os perfis a partir do mínimo e depois em blocos de 100.
        if (
            len(candidatos) >= MIN_CANDIDATOS_POOL
            and (len(candidatos) - MIN_CANDIDATOS_POOL) % 100 == 0
        ):
            calcular_indicadores_perfis(candidatos)
            distribuicao_pool = Counter(c.get("perfil") for c in candidatos)
            if all(
                distribuicao_pool.get(perfil, 0) >= meta
                for perfil, meta in METAS_PERFIS.items()
            ):
                break
    
        # v19.6: maioria dos candidatos sai da matriz reduzida
        usar_matriz = random.random() < PROPORCAO_MATRIZ
        if usar_matriz and len(matriz) >= 15:
            jogo = sorted(random.sample(matriz, 15))
        else:
            jogo = sorted(random.sample(pool, 15))
    
        if tuple(jogo) in usados:
            continue
    
        filtros = calcular_filtros(jogo, ultimo)
    
        estrutura = extrair_estrutura(jogo)
    
        # As restrições estruturais passam a ser pontuadas, não bloqueios.
        # O único critério rígido aqui é a validade combinatória (15 dezenas únicas).
        if len(jogo) != 15 or len(set(jogo)) != 15 or any(n < 1 or n > 25 for n in jogo):
            continue
        dentro_limites = validar_autonomo(
            filtros,
            estrutura["linhas"],
            limites
        )
        penalidade_estrutura = 0.0 if dentro_limites else 0.035
    
        # =====================================
        # MEMÓRIA ESTRUTURAL
        # =====================================
    
        memoria_estrutura = memoria_cache.get(
            estrutura["hash_estrutura"]
        )
        # =====================================
        # FILTRO DE CONFIANÇA ESTRUTURAL
        # v19.3
        # =====================================

        if memoria_estrutura:

            score_ctx_tmp = float(
                memoria_estrutura.get(
                    "score_contextual",
                    0
                )
            )

            score_real_tmp = float(
                memoria_estrutura.get(
                    "score_medio_real",
                    0
                )
            )

            vezes_tmp = int(
                memoria_estrutura.get(
                    "vezes_gerado",
                    0
                )
            )

            # Estruturas historicamente fracas recebem penalidade adiante;
            # não são descartadas nesta etapa de geração.
    
        score_contextual = 0.0
        score_previsibilidade = 0.0
        score_medio_real = 0.0
        taxa_sobrevivencia = 0.0
        vezes_gerado = 0
    
        if memoria_estrutura:
    
            score_contextual = float(
                memoria_estrutura.get(
                    "score_contextual",
                    0
                )
            )
    
            score_previsibilidade = float(
                memoria_estrutura.get(
                    "score_previsibilidade",
                    0
                )
            )
    
            score_medio_real = float(
                memoria_estrutura.get(
                    "score_medio_real",
                    0
                )
            )
    
            taxa_sobrevivencia = float(
                memoria_estrutura.get(
                    "taxa_sobrevivencia",
                    0
                )
            )
    
            vezes_gerado = int(
                memoria_estrutura.get(
                    "vezes_gerado",
                    0
                )
            )

        # =====================================
        # FILTRO DE ESTRUTURAS RUINS
        # =====================================
        
        penalidade_memoria = 0.0
        if memoria_estrutura and score_medio_real < 5.5 and vezes_gerado >= 5:
            penalidade_memoria = 0.045
    
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
    
        score_mc = simular_probabilidade_jogo(
            jogo,
            historico=hist
        )
    
        cluster_id = identificar_cluster_jogo(
            features
        )
    
        diversidade_ok = diversidade_avancada_ok(
            jogo,
            candidatos[-40:],
            estrutura,
            cluster_id
        )
        penalidade_diversidade = 0.0 if diversidade_ok else 0.035
    
        overlap_medio_local = 0.0
        if candidatos:
            overlap_medio_local = float(np.mean([
                len(set(jogo) & set(c["nums"]))
                for c in candidatos[-50:]
            ]))
        penalidade_overlap_pool = max(0.0, overlap_medio_local - 9.2) * 0.012
    
        # =====================================
        # SCORE ESTATÍSTICO
        # =====================================
    
        s1, s2, s3 = score_base(
            jogo,
            base_scores
        )
    
        score_estatistico = (
            s1 * 0.30
            + s2 * 0.35
            + s3 * 0.35
        )
    
        # Esses componentes dependem apenas do jogo e do histórico desta execução.
        score_potencial = score_potencial_alto(jogo, hist, scores_dezenas)

        # Novo score explícito de acertos históricos (foco 13/14)
        score_hits_reais = score_historico_acertos(jogo, hist)
    
        score_final = calcular_score_ensemble(
            score_estatistico=score_estatistico,
            score_montecarlo=score_mc,
            score_potencial=score_potencial,  # agora passa explicitamente
            fator_global=fator_global,
            fator_feedback=1.0,
            fator_regime=1.0,
            bonus_estrutura=bonus_estrutura(
                memoria_estrutura
            ),
            bonus_fadiga=bonus_fadiga(
                memoria_estrutura
            ),
            bonus_recencia=bonus_recencia(
                memoria_estrutura
            ),
            bonus_moldura=bonus_moldura(
                filtros
            ),
            pesos=pesos,
            bonus_recompensa=calcular_recompensa_evolutiva(
                estrutura,
                filtros,
                cluster_id
            )
        )
    
        # =====================================
        # APRENDIZADO REAL - v19.5 (rebalanceado)
        # Mais peso em potencial + hits históricos reais
        # Menos peso em scores internos que não correlacionam bem com 13/14
        # =====================================
    
        score_final = (
            score_final * 0.28
            + score_potencial * 0.32
            + score_hits_reais * 0.18
            + score_contextual * 0.10
            + score_previsibilidade * 0.04
            + (score_medio_real / 15.0) * 0.08
        )
    
        # Estruturas comprovadas com histórico de hits altos ganham bônus forte
        if score_medio_real >= 10.0:
            score_final *= 1.15
        elif score_medio_real >= 9.5:
            score_final *= 1.11
        elif score_medio_real >= 9.0:
            score_final *= 1.07
        elif score_medio_real >= 8.5:
            score_final *= 1.04
        elif score_medio_real >= 8.0:
            score_final *= 1.02
    
        # Estruturas novas ou pouco testadas recebem bônus leve de exploração
        if vezes_gerado == 0:
            score_final *= 1.02
        elif vezes_gerado <= 4:
            score_final *= 1.035
        elif vezes_gerado <= 12:
            score_final *= 1.04
    
        # Sobrevivência real
        score_final *= (1 + taxa_sobrevivencia * 0.035)

        score_final *= bonus_confianca(memoria_estrutura)
    
        # Controle de saturação (mais suave)
        score_final -= sum(
            contador_dezenas[n] * 0.018
            for n in jogo
        )
        score_final -= (
            penalidade_estrutura
            + penalidade_memoria
            + penalidade_diversidade
            + penalidade_overlap_pool
        )
    
        score_final = aplicar_entropia_modo(
            score_final,
            modo_variacao
        )

        if len(candidatos) < 5:
            print(
                "DEBUG MEMORIA:",
                {
                    "cluster_id": cluster_id,
                    "score_contextual": score_contextual,
                    "score_previsibilidade": score_previsibilidade,
                    "score_medio_real": score_medio_real,
                    "hash_estrutura": estrutura.get("hash_estrutura")
                }
            )
    
        candidatos.append({
            "nums": jogo,
            "score": float(score_final),
            "score_potencial": float(score_potencial),
            "score_hits_reais": float(score_hits_reais),
            "score_mc": float(score_mc),
            "score_contextual": float(score_contextual),
            "score_previsibilidade": float(score_previsibilidade),
            "score_medio_real": float(score_medio_real),
            "filtros": filtros,
            "estrutura": estrutura,
            "features": features,
            "cluster_id": cluster_id,
            "vezes_gerado": int(vezes_gerado),
            "taxa_sobrevivencia": float(taxa_sobrevivencia),
            "penalidades_geracao": {
                "estrutura": float(penalidade_estrutura),
                "memoria": float(penalidade_memoria),
                "diversidade": float(penalidade_diversidade),
                "overlap_pool": float(penalidade_overlap_pool)
            }
        })

        # Impede duplicatas no conjunto de candidatos.
        usados.add(tuple(jogo))

        for n in jogo:
            contador_dezenas[n] += 1

    print(
        f"\n📦 Pool gerado: {len(candidatos)} candidatos válidos "
        f"em {tentativas_realizadas:,} tentativas."
    )

    if len(candidatos) < QTD_FINAL:
        raise RuntimeError(
            f"Pool insuficiente: apenas {len(candidatos)} candidatos válidos "
            f"para selecionar {QTD_FINAL} jogos. Nenhum dado será gravado."
        )

    # Penalidade global de saturação permanece como ajuste de score, sem descarte.
    contador_global = Counter()
    for cand in sorted(candidatos, key=lambda x: -x["score"]):
        penalidade = sum(
            PESO_PENALIDADE_SATURACAO
            for n in cand["nums"]
            if contador_global[n] >= MAX_OCORRENCIAS_GLOBAL
        )
        cand["score"] = float(cand["score"] - penalidade)
        for n in cand["nums"]:
            contador_global[n] += 1

    # Classificação objetiva e seleção com metas explícitas por perfil.
    finais = selecionar_portfolio_perfis(candidatos, METAS_PERFIS)
    distribuicao_perfis = validar_portfolio_final(finais)

    dezenas_usadas = {n for f in finais for n in f["nums"]}
    faltantes_geral = sorted(set(range(1, 26)) - dezenas_usadas)
    cob_matriz = cobertura_matriz([f["nums"] for f in finais], matriz)
    faltantes_matriz = sorted(set(matriz) - dezenas_usadas)

    print("\n===== AUDITORIA DO PORTFÓLIO =====")
    print(f"✅ Jogos finais: {len(finais)}/{QTD_FINAL}")
    print(f"✅ Perfis: {dict(distribuicao_perfis)}")
    print(f"✅ Cobertura geral: {len(dezenas_usadas)}/25 dezenas")
    print(f"📊 Cobertura da matriz de {len(matriz)} dezenas: {cob_matriz*100:.1f}%")
    if faltantes_geral:
        raise RuntimeError(f"Cobertura geral incompleta: {faltantes_geral}")
    if cob_matriz < COBERTURA_MINIMA_MATRIZ:
        raise RuntimeError(
            f"Cobertura da matriz insuficiente: {cob_matriz:.1%}; "
            f"mínimo={COBERTURA_MINIMA_MATRIZ:.0%}. Nenhum dado será gravado."
        )
    if faltantes_matriz:
        print(f"ℹ️ Dezenas da matriz não utilizadas: {faltantes_matriz}")

    # Frequência de cada dezena no portfólio final.
    frequencia_dezenas_final = Counter(
        n for jogo in finais for n in jogo["nums"]
    )
    print("📌 Frequência das dezenas no portfólio:", dict(sorted(frequencia_dezenas_final.items())))

    # Investimento estimado - baseado na quantidade real selecionada
    
    calcular_roi(len(finais))

    print("\n===== DEBUG FINAIS =====")

    if finais:
        print(
            json.dumps(
                {
                    "cluster_id": finais[0].get("cluster_id"),
                    "estrutura": finais[0].get("estrutura"),
                    "score_contextual": finais[0].get("score_contextual"),
                    "score_previsibilidade": finais[0].get("score_previsibilidade"),
                    "score_medio_real": finais[0].get("score_medio_real")
                },
                indent=2,
                default=str
            )
        )
    # =====================================================
    # ESTRUTURAÇÃO DOS DADOS DE RETORNO
    # =====================================================
    
    dados_palpites = []
    linhas_telegram = []
    
    for i, c in enumerate(finais, 1):
    
        tier = c["perfil"]
    
        score_estrutural = round(
            (
                c.get("score_contextual", 0) * 0.40
                + c.get("score_previsibilidade", 0) * 0.30
                + c.get("score_medio_real", 0) * 0.30
            ),
            8
        )
    
        ind = c.get("indicadores_perfil", {})
        texto_linha_telegram = (
            f"{i}º | {c['score']:.5f} | "
            f"Pot={c['score_potencial']:.3f} | "
            f"Hits={c.get('score_hits_reais', 0):.2f} | "
            f"Perfil={tier.upper()}({c.get('score_perfil', 0):.3f}) | "
            f"Est={ind.get('estabilidade', 0):.2f} "
            f"Ader={ind.get('aderencia', 0):.2f} "
            f"Exp={ind.get('exploracao', 0):.2f} "
            f"Div={ind.get('diversidade', 0):.2f} | "
            f"{c['nums']}"
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
            "origem": "sistema",
    
            "numeros": c["nums"],
    
            # =========================
            # SCORES PRINCIPAIS
            # =========================
    
            "score": round(
                float(c["score"]),
                8
            ),

            "score_modelo": round(
                float(c["score"]),
                8
            ),
    
            "score_potencial": round(
                float(c["score_potencial"]),
                8
            ),
    
            "score_montecarlo": round(
                float(c["score_mc"]),
                8
            ),
    
            "score_estrutural": score_estrutural,

            # =========================
            # CONTEXTO REAL DA ESTRUTURA
            # =========================

            "score_contextual_real": round(
                float(
                    c.get(
                        "score_contextual",
                        0
                    )
                ),
                8
            ),

            "score_previsibilidade_real": round(
                float(
                    c.get(
                        "score_previsibilidade",
                        0
                    )
                ),
                8
            ),

            "score_medio_real": round(
                float(
                    c.get(
                        "score_medio_real",
                        0
                    )
                ),
                8
            ),
    
            # =========================
            # ESTRUTURA
            # =========================
    
            "cluster_id": c.get(
                "cluster_id"
            ),
    
            "hash_estrutura": (
                c["estrutura"].get(
                    "hash_estrutura"
                )
                if c.get("estrutura")
                else None
            ),
    
            # =========================
            # ESTATÍSTICAS BÁSICAS
            # =========================
    
            "soma_total": c["filtros"]["soma"],
    
            "pares": c["filtros"]["pares"],
    
            "impares": (
                15 - c["filtros"]["pares"]
            ),
    
            "qtd_sequencias": c["filtros"][
                "seq_max"
            ],
    
            # =========================
            # FLAGS DE POPULARIDADE
            # =========================
    
            **calcular_flags_popularidade(
                c["nums"],
                dezenas_mais_sorteadas,
                dezenas_menos_sorteadas,
            ),
    
            # =========================
            # MÉTRICAS COMPLETAS
            # =========================
    
            "metricas": {
    
                "score_contextual": round(
                    float(
                        c.get(
                            "score_contextual",
                            0
                        )
                    ),
                    8
                ),
    
                "score_previsibilidade": round(
                    float(
                        c.get(
                            "score_previsibilidade",
                            0
                        )
                    ),
                    8
                ),
    
                "score_medio_real": round(
                    float(
                        c.get(
                            "score_medio_real",
                            0
                        )
                    ),
                    8
                ),
    
                "score_montecarlo": round(
                    float(
                        c["score_mc"]
                    ),
                    8
                ),
    
                "score_potencial": round(
                    float(
                        c["score_potencial"]
                    ),
                    8
                ),

                "score_hits_reais": round(
                    float(
                        c.get("score_hits_reais", 0)
                    ),
                    8
                ),

                "perfil": tier,
                "score_perfil": round(float(c.get("score_perfil", 0)), 8),
                "indicadores_perfil": c.get("indicadores_perfil", {}),
                "scores_perfil": c.get("scores_perfil", {}),
                "penalidades_geracao": c.get("penalidades_geracao", {}),
    
                "score_final": round(
                    float(
                        c["score"]
                    ),
                    8
                )
            },
    
            # =========================
            # FILTROS UTILIZADOS
            # =========================
    
            "filtros_aplicados": {
    
                "pares": c["filtros"][
                    "pares"
                ],
    
                "primos": c["filtros"][
                    "primos"
                ],
    
                "moldura": c["filtros"][
                    "moldura"
                ],
    
                "soma": c["filtros"][
                    "soma"
                ],
    
                "repetidos": c["filtros"][
                    "repetidos"
                ],
    
                "seq_max": c["filtros"][
                    "seq_max"
                ]
            },
    
            # =========================
            # CONTROLE
            # =========================
    
            "processado": False,
    
            "versao_gerador": VERSAO
        })
    
    print(
        f"⏱️ Tempo total da geração: "
        f"{time.time() - inicio_execucao:.1f} segundos"
    )
    
    return {
        "palpites": dados_palpites,
        "linhas_telegram": linhas_telegram,
        "concurso": concurso_ref,
        "matriz": matriz,
        "cobertura_matriz": cob_matriz,
        "cobertura_geral": len(dezenas_usadas) / 25.0,
        "distribuicao_perfis": dict(distribuicao_perfis),
        "frequencia_dezenas": dict(sorted(frequencia_dezenas_final.items())),
        "tentativas_realizadas": tentativas_realizadas,
        "candidatos_gerados": len(candidatos)
    }

# ======================================================
# ENTRYPOINT (Modo isolado para testes manuais no terminal)
# ======================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--modo",
        default="moderado",
        choices=[
            "conservador",
            "moderado",
            "agressivo"
        ]
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Força a regeneração ignorando travas de banco"
    )

    args = parser.parse_args()

    try:

        sb = get_supabase()

        from scripts.processamento_diario_lotofacil import (
            carregar_historico
        )

        hist = carregar_historico()

        concurso_ref = (
            int(hist[-1]["concurso"]) + 1
        )

        if (
            not args.force
            and concurso_ja_processado(
                sb,
                concurso_ref
            )
        ):
            print(
                f"ℹ️ Concurso {concurso_ref} "
                f"já processado no banco."
            )
            sys.exit(0)

        print(
            "⚙️ Executando engine "
            "em modo de teste isolado..."
        )

        resultado_teste = executar_motor_geracao(
            modo_variacao=args.modo
        )

        if resultado_teste:

            if len(resultado_teste.get("palpites", [])) != QTD_FINAL:
                raise RuntimeError("Resultado incompleto: gravação cancelada.")

            payload_teste = [
                p.copy()
                for p in resultado_teste["palpites"]
            ]
        
            print("\n===== DEBUG PAYLOAD =====")
            print(
                json.dumps(
                    payload_teste[0],
                    indent=2,
                    default=str
                )
            )

            res = sb.table(
                "palpites_validos"
            ).upsert(
                payload_teste,
                on_conflict="concurso_referencia,indice_palpite"
            ).execute()

            print("\n===== DEBUG UPSERT =====")
            print(res)

            print(
                f"✅ [TESTE BUCKET] "
                f"{len(payload_teste)} palpites gravados no banco. "
                f"Perfis: {resultado_teste.get('distribuicao_perfis')} | "
                f"Cobertura: {resultado_teste.get('cobertura_geral', 0)*100:.0f}%"
            )

            print(
                "\n📲 TELEGRAM_PAYLOAD_START"
            )

            print(
                montar_msg_telegram(
                    resultado_teste["concurso"],
                    resultado_teste["linhas_telegram"],
                    matriz=resultado_teste.get("matriz"),
                    cobertura=resultado_teste.get("cobertura_matriz")
                )
            )

            print(
                "📲 TELEGRAM_PAYLOAD_END"
            )

    except Exception:
        import traceback
        traceback.print_exc()
        raise
