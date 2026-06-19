# 🏗️ ARQUITETURA DESEJADA v20 - SISTEMA EVOLUTIVO

**Data:** 2026-06-19  
**Versão:** Estratégica (pré-desenvolvimento)  
**Objetivo:** Transformar PalpiteiroBackend em máquina de aprendizado contínuo

---

## 🎯 VISÃO GERAL

Sistema que **aprende estruturas vencedoras** através de ciclo contínuo:

```
┌─────────────────────────────────────────────────────────────────┐
│                   CICLO EVOLUTIVO CONTÍNUO                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Resultado Oficial (API Caixa)                                 │
│         ↓                                                       │
│  Conferência (palpites_service vs resultado_real)              │
│         ↓                                                       │
│  Extração de Features (23+ features estruturais)               │
│         ↓                                                       │
│  Feedback Sistema (armazenar features + acertos)               │
│         ↓                                                       │
│  Backtest Automático (simular histórico completo)              │
│         ↓                                                       │
│  Recalibração Motores (meta_learning adapta pesos)             │
│         ↓                                                       │
│  Geração Novos Palpites (com pesos recalibrados)               │
│         ↓                                                       │
│  [Volta ao início - Ciclo diário]                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 CAMADAS DA ARQUITETURA

### Camada 1: DADOS (Feature Engineering)
```
raw_concursos (Supabase)
    ↓
feature_store (extrator central)
    ↓
historico_features (tabela: concurso, features[], acertos)
```

**Responsável:** `feature_store_service.py` + novo `historico_features_repo.py`

**Output:** Matriz de features para modelo supervisionado

---

### Camada 2: MOTORES (7 estratégias paralelas)

```
┌─────────────────┐
│ Motor 1: Freq   │ → score_frequencia
├─────────────────┤
│ Motor 2: Atraso │ → score_atraso
├─────────────────┤
│ Motor 3: Memória│ → score_memoria (elite_service)
├─────────────────┤
│ Motor 4: Cluster│ → score_cluster (clusterizacao_service)
├─────────────────┤
│ Motor 5: Genética│ → score_genetica (selecao_genetica_service)
├─────────────────┤
│ Motor 6: MonteCarlo│ → score_montecarlo
├─────────────────┤
│ Motor 7: Ensemble│ → score_ensemble (orquestrador)
└─────────────────┘
```

**Cada motor:**
- Gera candidatos
- Produz score [0, 10]
- Rastreia métrica de desempenho
- Recebe peso adaptativo do meta_learning

---

### Camada 3: MODELO SUPERVISIONADO (Novo)

```
Training Data (historico_features com acertos)
    ↓
┌──────────────────────────────────┐
│ RandomForest / XGBoost / LightGBM│ ← Treinar continuamente
├──────────────────────────────────┤
│ X = [23 features estruturais]   │
│ Y = [número de acertos]          │
└──────────────────────────────────┘
    ↓
score_supervisionado (por cada palpite)
    ↓
Incorporado ao ensemble final
```

**Responsável:** Novo `modelo_supervisionado_service.py`

**Treino:** Daily (após conferência)

**Output:** Previsão de acertos esperados + feature importance

---

### Camada 4: META LEARNING (Adaptação)

```
┌─────────────────────────────────────────────┐
│ Meta Learning Service v3.0                  │
├─────────────────────────────────────────────┤
│                                             │
│ Input: Performance de cada motor            │
│ ├─ frequencia: 8.7/10                       │
│ ├─ atraso: 9.2/10                           │
│ ├─ memoria: 8.5/10                          │
│ ├─ cluster: 8.9/10                          │
│ ├─ genetica: 9.5/10                         │
│ ├─ montecarlo: 8.3/10                       │
│ └─ ensemble: 9.1/10                         │
│                                             │
│ Processing: Calcular pesos adaptativos      │
│ ├─ Normalizar performances                  │
│ ├─ Aplicar exponencial (premia melhor)      │
│ ├─ Suavizar com histórico (evitar overfitting)│
│ └─ Armazenar em peso_motor_diario           │
│                                             │
│ Output: Pesos para ensemble [0.05-0.25]    │
│                                             │
└─────────────────────────────────────────────┘
```

**Input:** Backtest de cada motor

**Output:** `peso_motor_diario` para gerar_palpites

**Atualização:** Daily

---

### Camada 5: DETECÇÃO DE COLAPSO (Monitoramento)

```
┌──────────────────────────────────────┐
│ Colapso Service v1.0                 │
├──────────────────────────────────────┤
│                                      │
│ Detectar COLAPSO se:                 │
│ ├─ Convergência excessiva            │
│ ├─ Repetição de estruturas           │
│ ├─ Baixa entropia                    │
│ ├─ Baixa dispersão                   │
│ ├─ Excesso de overlap                │
│ └─ Desempenho < 5 acertos por 3 dias │
│                                      │
│ Se colapso detectado:                │
│ ├─ Sinalizar em meta_validacao       │
│ └─ Acionar regeneração (nova seed)   │
│                                      │
└──────────────────────────────────────┘
```

**Responsável:** `colapso_service.py` (integrado)

**Acionamento:** meta_validacao_final.py

**Output:** Flag de regeneração necessária

---

### Camada 6: MEMÓRIA ELITE (Reutilização)

```
┌──────────────────────────────────────────┐
│ Elite Service v2.0                       │
├──────────────────────────────────────────┤
│                                          │
│ Armazenar em elite_structures:           │
│ ├─ structure_id                          │
│ ├─ features_array                        │
│ ├─ acertos_media                         │
│ ├─ estabilidade                          │
│ ├─ frequencia_sucesso                    │
│ ├─ período (data_inicio, data_fim)       │
│ └─ score_consolidado                     │
│                                          │
│ Usar em geração:                         │
│ ├─ Reutilizar estruturas com score > 8.5│
│ ├─ Adicionar variação (10% mutação)      │
│ └─ Incorporar ao ensemble                │
│                                          │
└──────────────────────────────────────────┘
```

**Responsável:** `elite_service.py` (expandido)

**Output:** 2-3 palpites candidatos por geração

---

### Camada 7: VALIDAÇÃO E RETROALIMENTAÇÃO

```
Gerar Palpites (com pesos recalibrados)
    ↓
Armazenar em palpites_validos
    ↓
Depois do sorteio: resultado_oficial
    ↓
Conferência (calculando acertos)
    ↓
Armazenar em palpites_resultados_reais
    ├─ acertos_11
    ├─ acertos_12
    ├─ acertos_13
    ├─ acertos_14
    └─ acertos_15
    ↓
Feedback ao Sistema
├─ Atualizar peso_motor_diario
├─ Treinar modelo_supervisionado
├─ Atualizar elite_structures
└─ Verificar colapso
    ↓
[Próxima iteração]
```

---

## 📊 TABELAS SUPABASE - NOVO ESQUEMA

### Tabelas Novas Obrigatórias

#### 1. `historico_features` (Core)
```sql
CREATE TABLE historico_features (
  id SERIAL PRIMARY KEY,
  concurso INTEGER NOT NULL,
  indice_palpite INTEGER,
  
  -- 23 Features Estruturais
  soma INTEGER,
  pares INTEGER,
  impares INTEGER,
  primos INTEGER,
  fibonacci INTEGER,
  moldura INTEGER,
  centro INTEGER,
  linhas JSONB,
  colunas JSONB,
  quadrantes JSONB,
  finais JSONB,
  consecutivos INTEGER,
  repetidos INTEGER,
  dispersao DECIMAL,
  entropia DECIMAL,
  cluster_id INTEGER,
  atraso_medio DECIMAL,
  frequencia_media DECIMAL,
  densidade DECIMAL,
  dist_horizontal JSONB,
  dist_vertical JSONB,
  estabilidade DECIMAL,
  
  -- Target (Conferência)
  acertos_reais INTEGER,
  acertos_11 BOOLEAN,
  acertos_12 BOOLEAN,
  acertos_13 BOOLEAN,
  acertos_14 BOOLEAN,
  acertos_15 BOOLEAN,
  
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(concurso, indice_palpite)
);

CREATE INDEX idx_historico_features_concurso ON historico_features(concurso);
CREATE INDEX idx_historico_features_acertos ON historico_features(acertos_reais);
```

#### 2. `elite_structures` (Memória)
```sql
CREATE TABLE elite_structures (
  id SERIAL PRIMARY KEY,
  structure_hash VARCHAR(64) UNIQUE,
  numeros JSONB,
  
  features JSONB, -- as 23 features
  acertos_media DECIMAL,
  estabilidade DECIMAL,
  frequencia_sucesso DECIMAL,
  
  primeira_ocorrencia DATE,
  ultima_ocorrencia DATE,
  ocorrencias_totais INTEGER,
  score_consolidado DECIMAL,
  
  ativa BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### 3. `peso_motor_diario` (Meta Learning)
```sql
CREATE TABLE peso_motor_diario (
  id SERIAL PRIMARY KEY,
  data DATE,
  
  motor_frequencia DECIMAL(3,2),
  motor_atraso DECIMAL(3,2),
  motor_memoria DECIMAL(3,2),
  motor_cluster DECIMAL(3,2),
  motor_genetica DECIMAL(3,2),
  motor_montecarlo DECIMAL(3,2),
  motor_ensemble DECIMAL(3,2),
  
  soma_pesos DECIMAL(4,2),
  normalizado BOOLEAN,
  
  created_at TIMESTAMP,
  UNIQUE(data)
);
```

#### 4. `performance_motores_diario` (Tracking)
```sql
CREATE TABLE performance_motores_diario (
  id SERIAL PRIMARY KEY,
  data DATE,
  
  motor VARCHAR(50),
  acertos_11 INTEGER,
  acertos_12 INTEGER,
  acertos_13 INTEGER,
  acertos_14 INTEGER,
  acertos_15 INTEGER,
  score_medio DECIMAL,
  volatilidade DECIMAL,
  
  created_at TIMESTAMP
);
```

#### 5. `modelo_supervisionado_metricas` (ML)
```sql
CREATE TABLE modelo_supervisionado_metricas (
  id SERIAL PRIMARY KEY,
  data_treino DATE,
  
  r2_score DECIMAL,
  rmse DECIMAL,
  mae DECIMAL,
  feature_importance JSONB,
  
  amostra_tamanho INTEGER,
  dias_historico INTEGER,
  
  modelo_versao VARCHAR(20),
  
  created_at TIMESTAMP
);
```

#### 6. `backtest_resultado` (Validação)
```sql
CREATE TABLE backtest_resultado (
  id SERIAL PRIMARY KEY,
  concurso_inicio INTEGER,
  concurso_fim INTEGER,
  
  media_acertos DECIMAL,
  estabilidade DECIMAL,
  drawdown DECIMAL,
  
  acertos_11_pct DECIMAL,
  acertos_12_pct DECIMAL,
  acertos_13_pct DECIMAL,
  acertos_14_pct DECIMAL,
  acertos_15_pct DECIMAL,
  
  versao_gerador VARCHAR(20),
  motores_ativos JSONB,
  pesos_utilizados JSONB,
  
  data_execucao TIMESTAMP
);
```

---

## 🔄 FLUXO DIÁRIO COMPLETO

```
00:00 - CRON BATCH START
  │
  ├─→ 01) atualizar_lotofacil.py
  │   └─ Sincroniza API Caixa com lotofacil_concursos
  │
  ├─→ 02) processamento_diario_lotofacil.py
  │   └─ Extrai contexto (últimas tendências)
  │
  ├─→ 03) gerar_palpites_diarios.py (v19.2)
  │   ├─ Obtém pesos_motor_diario (meta_learning)
  │   ├─ Executa 7 motores com pesos adaptativos
  │   ├─ Incorpora score_supervisionado
  │   ├─ Consulta elite_structures (2-3 candidatos)
  │   ├─ Aplica clusterização (diversidade)
  │   ├─ Detecta colapso (colapso_service)
  │   └─ Salva 10 palpites em palpites_validos
  │
  ├─→ 04) meta_validacao_final.py (v2.0)
  │   ├─ Valida convergência
  │   ├─ Verifica colapso
  │   └─ Regenera se necessário
  │
  └─ FIM (palpites prontos para amanhã)

AA:BB (Após sorteio - idealmente 15min depois)
  │
  ├─→ 05) atualizar_lotofacil.py (nova verificação)
  │   └─ Sincroniza resultado oficial
  │
  ├─→ 06) conferir_resultados.py
  │   ├─ Calcula acertos de cada palpite
  │   ├─ Armazena em palpites_resultados_reais
  │   └─ Gera feedback
  │
  └─→ 07) FEEDBACK LOOP (novo script)
      ├─ Extração features (feature_store)
      │  └─ Armazena em historico_features
      │
      ├─ Treinar modelo supervisionado
      │  └─ Atualizar performance_metricas
      │
      ├─ Recalibrar meta_learning
      │  └─ Calcular novos pesos_motor_diario
      │
      ├─ Atualizar elite_structures
      │  └─ Adicionar estruturas bem-sucedidas
      │
      ├─ Executar backtest automático
      │  └─ Validar histórico completo
      │
      └─ Registrar performance
         └─ performance_motores_diario

Próximo ciclo: volta ao passo 01
```

---

## 🗂️ REORGANIZAÇÃO DE SERVIÇOS (Integração, NÃO Remoção)

### ✅ CORE (Manter, expandir se necessário)

| Serviço | Status | Ação |
|---------|--------|------|
| `supabase_service.py` | Core | Manter |
| `feature_store_service.py` | Core | **EXPANDIR** (23 features) |
| `palpites_service.py` | Core | Manter (integrar scores) |
| `meta_learning_service.py` | Core | **EXPANDIR** (7 motores + modelo) |
| `conferencia_service.py` | Core | Manter |

---

### 🧠 IA/ML (Integrar completamente)

| Serviço | Status Atual | Novo Status | Alteração |
|---------|-------------|-------------|-----------|
| `aprendizado_service_v3.py` | Ativo | Motor | Motor 1 (frequência) |
| `motores_ensemble_service.py` | Ativo | Motor | Motor 7 (ensemble) |
| `selecao_genetica_service.py` | Ativo | Motor | Motor 5 (genética) |
| `montecarlo_service.py` | Ativo | Motor | Motor 6 (Monte Carlo) |
| `clusterizacao_service.py` | Ativo | Motor | Motor 4 (cluster) |
| `memoria_service.py` | Ativo | Integrado | Base para elite_service |
| `diversidade_service.py` | Ativo | Utilitário | Verificar colapso |

---

### 🔗 SERVIÇOS ÓRFÃOS → INTEGRADOS

| Serviço | Era | Novo Papel |
|---------|-----|-----------|
| `backtest_service.py` | Órfão | **Motor de Validação** - expandir para histórico completo |
| `elite_service.py` | Órfão | **Elite Memory** - reutilizar estruturas bem-sucedidas |
| `colapso_service.py` | Órfão | **Monitoramento** - detectar convergência/colapso |
| `repeticao_service.py` | Órfão | **Feature Engineering** - integrar em historico_features |
| `roi_service.py` | Órfão | **Métrica de Desempenho** - avaliar eficiência dos motores |

---

### ⚠️ PROBLEMÁTICOS → CORRIGIDOS

| Serviço | Problema | Solução |
|---------|----------|---------|
| `home_service.py` | Import inválido | **CORRIGIR** import e integrar com dashboard |
| `lotofacil_service.py` | TODO comentado | **REMOVER** (funcionalidade integrada em atualizar_lotofacil.py) |

---

### 🗑️ ESTRUTURA LEGACY → CONSOLIDADA

| Item | Ação |
|------|------|
| `api/repositories/palpites_repo.py` | Remover (duplicado com app/) |
| `api/routers/palpites.py` | Remover (legacy, funcionalidade em app/) |
| `api/core/config.py` | Remover (duplica supabase_service) |
| `api/` estrutura | Deixar apenas `api/index.py` para Vercel |

---

## 📈 NOVOS SERVIÇOS A CRIAR

### 1. `modelo_supervisionado_service.py`

**Responsabilidade:**
- Treinar RandomForest/XGBoost/LightGBM
- Gerar score_supervisionado para cada palpite
- Atualizar feature_importance
- Salvar métricas em modelo_supervisionado_metricas

**Input:** historico_features (X, Y)

**Output:** score_supervisionado + métricas

---

### 2. `feedback_loop_service.py`

**Responsabilidade:**
- Orquestrador do ciclo de feedback
- Executar em sequência:
  1. Extração de features
  2. Treino de modelo
  3. Recalibração meta_learning
  4. Atualização elite_structures
  5. Backtest automático

---

### 3. `historico_features_repo.py`

**Responsabilidade:**
- CRUD da tabela historico_features
- Métodos para query features por período
- Exportar dataset para ML

---

### 4. `elite_structures_repo.py`

**Responsabilidade:**
- CRUD da tabela elite_structures
- Buscar estruturas por score
- Atualizar estabilidade

---

---

## 🎯 RESUMO INTEGRAÇÕES AUSENTES

| Integração | Onde | Por Que | Prioridade |
|------------|------|---------|-----------|
| Feature Store centralizado | feature_store + historico_features_repo | Base para modelo supervisionado | 🔴 CRÍTICA |
| Modelo Supervisionado | novo modelo_supervisionado_service | Adicionar dimensão ML ao ensemble | 🔴 CRÍTICA |
| Meta Learning (7 motores) | meta_learning_service | Adaptar pesos dinamicamente | 🔴 CRÍTICA |
| Backtest Histórico | backtest_service (expandir) | Validar cada motor | 🔴 CRÍTICA |
| Elite Memory | elite_service (expandir) | Reutilizar estruturas | 🟠 IMPORTANTE |
| Colapso Detection | colapso_service (integrar) | Regenerar automaticamente | 🟠 IMPORTANTE |
| ROI Tracking | roi_service (integrar) | Métrica de eficiência | 🟠 IMPORTANTE |
| Feedback Loop | novo feedback_loop_service | Orquestrador do ciclo | 🟠 IMPORTANTE |

---

## ✨ PRINCÍPIOS DE IMPLEMENTAÇÃO

### 1. Reutilização
- ✅ Expandir, não remover
- ✅ Integrar órfãos ao ecossistema
- ✅ Cada serviço com métrica clara

### 2. Aprendizado Contínuo
- ✅ Features estruturais (não números)
- ✅ Ciclo diário automático
- ✅ Calibração adaptativa

### 3. Monitoramento
- ✅ Todo motor produz métrica
- ✅ Backtest valida hipóteses
- ✅ Desempenho rastreado

### 4. Estabilidade
- ✅ Detecção de colapso
- ✅ Regeneração automática
- ✅ Pesos limitados [0.05-0.25]

---

**Documento:** Arquitetura Desejada v20  
**Status:** Estratégico (pronto para implementação)  
**Próximo:** Plano de Migração Detalhado
