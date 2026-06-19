# 🔗 MAPA DE INTEGRAÇÕES v20 - CONEXÕES DO SISTEMA

**Data:** 2026-06-19  
**Objetivo:** Documentar cada ponto de integração entre serviços  

---

## 📊 GRAFO DE INTEGRAÇÕES COMPLETO

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAMADA DE ENTRADA                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  supabase_service (SINGLETON - TUDO depende)                           │
│      ↓                                                                  │
│  [6 tabelas novas]                                                     │
│      ├─ historico_features                                            │
│      ├─ elite_structures                                              │
│      ├─ peso_motor_diario                                             │
│      ├─ performance_motores_diario                                    │
│      ├─ modelo_supervisionado_metricas                                │
│      └─ backtest_resultado                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
   
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  CORE SERVICES   │  │  IA/ML SERVICES  │  │  UTILITÁRIOS     │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│ palpites_service │  │ feature_store    │  │ conferencia      │
│ historico_service│  │ modelo_supervis. │  │ desempenho      │
│ estatisticas_srv │  │ meta_learning    │  │ elite_service   │
│ resultados_srv   │  │ 7 motores        │  │ colapso_service │
│                  │  │ backtest_service │  │ repeticao_srv   │
│                  │  │ elite_memory     │  │ roi_service     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                ┌───────────▼───────────┐
                │ FEEDBACK_LOOP_SERVICE │ (orquestrador)
                └───────────┬───────────┘
                            │
                    [Ciclo completo]
```

---

## 🔄 CICLO DIÁRIO DETALHADO COM INTEGRAÇÕES

### 1️⃣ FASE BATCH (23:59 - antes do sorteio)

```
INÍCIO DO BATCH
  ↓
01. atualizar_lotofacil.py
  │
  ├─ Chama: supabase_service.table("lotofacil_concursos")
  ├─ Output: Dados oficiais atualizados
  └─ Próximo: procesamento_diario_lotofacil.py
  
02. processamento_diario_lotofacil.py
  │
  ├─ Chama: supabase_service + estatisticas_service
  ├─ Extrai: contexto (tendências últimos 30 dias)
  └─ Próximo: gerar_palpites_diarios.py
  
03. gerar_palpites_diarios.py (v19.4)
  │
  ├─ Chama: peso_motor_repo.obter_pesos_hoje() 
  │          └─ [pesos adaptativos do meta-learning]
  │
  ├─ Para cada motor (7):
  │  ├─ Motor 1 (frequência): aprendizado_service_v3.gerar()
  │  ├─ Motor 2 (atraso): [via estatisticas_service]
  │  ├─ Motor 3 (memória): elite_service.reutilizar_elite()
  │  ├─ Motor 4 (cluster): clusterizacao_service.gerar()
  │  ├─ Motor 5 (genética): selecao_genetica_service.gerar()
  │  ├─ Motor 6 (montecarlo): montecarlo_service.gerar()
  │  └─ Motor 7 (ensemble): motores_ensemble_service.gerar()
  │
  ├─ Chama: feature_store_service.extrair_23_features()
  │          └─ Para cada candidato (extrai features)
  │
  ├─ Chama: modelo_supervisionado_service.predizer()
  │          └─ score_supervisionado para cada candidato
  │
  ├─ Ensemble final:
  │  score = 0.7 * score_motores + 0.3 * score_supervisionado
  │
  ├─ Chama: diversidade_service (validar cobertura)
  │
  ├─ Chama: colapso_service.detectar_colapso_estrategico()
  │          ├─ Detecta convergência
  │          ├─ Verifica entropia
  │          └─ Valida dispersão
  │
  └─ Output: 10 palpites + scores
  
04. meta_validacao_final.py (v2.0)
  │
  ├─ Recebe: 10 palpites + colapso_flag
  ├─ Valida: convergência, redundância, overlaps
  ├─ Se colapso OU validação falha:
  │  ├─ Chama: elite_service.regeneracao()
  │  └─ Gera 10 novos palpites com seed diferente
  │
  └─ Output: palpites_validos (confirmados)

[Palpites prontos para amanhã]
```

---

### 2️⃣ FASE PÓS-SORTEIO (quelquer hora após sorteio - idealmente 15min depois)

```
SORTEIO REALIZADO
  ↓
05. atualizar_lotofacil.py (verificar resultado)
  │
  ├─ Chama: API Caixa
  └─ Output: resultado_oficial
  
06. conferir_resultados.py (v2.0)
  │
  ├─ Chama: palpites_repo.listar_palpites_hoje()
  ├─ Para cada palpite:
  │  ├─ Confere vs resultado_oficial
  │  ├─ Calcula: acertos_11, acertos_12, ..., acertos_15
  │  ├─ Chama: feature_store_service.extrair_23_features(palpite)
  │  └─ Armazena em historico_features (com acertos reais)
  │
  └─ Output: palpites_resultados_reais (BD)
  
07. feedback_loop_service.py (NOVO - orquestrador)
  │
  ├─ PASSO 1: Treinar Modelo Supervisionado
  │  ├─ Chama: modelo_supervisionado_service.treinar()
  │  │  ├─ Input: historico_features (últimos 180 dias)
  │  │  ├─ Training: RandomForest/XGBoost/LightGBM
  │  │  └─ Output: modelo treinado + métricas
  │  └─ Salva: modelo_supervisionado_metricas (r2, rmse, feature_importance)
  │
  ├─ PASSO 2: Calcular Performance dos Motores
  │  ├─ Para cada motor:
  │  │  ├─ Analisa: acertos_11, acertos_12, ..., acertos_15
  │  │  ├─ Calcula: score_medio, volatilidade
  │  │  └─ Armazena em performance_motores_diario
  │  └─ Output: métricas por motor
  │
  ├─ PASSO 3: Recalibrar Meta Learning
  │  ├─ Chama: meta_learning_service.atualizar_pesos_7_motores()
  │  │  ├─ Input: performance_motores_diario (últimos 30 dias)
  │  │  ├─ Processing: normalizar, suavizar, aplicar softmax
  │  │  └─ Output: novos pesos [0.05-0.25]
  │  └─ Salva: peso_motor_diario (pesos para amanhã)
  │
  ├─ PASSO 4: Atualizar Elite Memory
  │  ├─ Chama: elite_service.gerenciar_elite_structures()
  │  │  ├─ Busca: palpites com acertos > 12
  │  │  ├─ Armazena: features + performance em elite_structures
  │  │  └─ Mantém: histórico de 365 dias
  │  └─ Output: elite_structures (BD)
  │
  ├─ PASSO 5: Executar Backtest (offline)
  │  ├─ Chama: backtest_service.backtest_historico()
  │  │  ├─ Simula: gerar palpites para 100 últimos concursos
  │  │  ├─ Usa: dados até cada concurso (sem future leak)
  │  │  └─ Compara: vs resultado real
  │  └─ Salva: backtest_resultado (validação)
  │
  ├─ PASSO 6: Alertar se Regressão
  │  ├─ Se: backtest_resultado < threshold:
  │  │  ├─ Registra: alerta
  │  │  └─ Notifica: dashboard/log
  │  └─ Não falha: apenas monitora
  │
  └─ OUTPUT: Sistema recalibrado e pronto para próximo ciclo

[Volta ao Passo 01 - próximo dia]
```

---

## 🔀 MATRIZ DE INTEGRAÇÕES POR ARQUIVO

### CORE SERVICES

#### `supabase_service.py`
```
Entrada:    -
Saída para: TODOS (é o singleton central)
Tabelas:    Lê/escreve todas as 6 novas
Chama:      Nenhum
Chamado por: Todos
```

#### `palpites_service.py`
```
Entrada:    palpites_repo, peso_motor_repo
Saída para: gerar_palpites_diarios.py
Tabelas:    palpites_validos (lê/escreve)
Chama:      feature_store_service (extrair features)
Chamado por: gerar_palpites_diarios.py
```

#### `feature_store_service.py` (EXPANDIDO)
```
Entrada:    numeros (List[int])
Saída para: modelo_supervisionado_service, historico_features_repo
Tabelas:    -
Chama:      math, numpy
Chamado por: gerar_palpites_diarios.py, conferir_resultados.py
Novo:       extrair_23_features(numeros) → Dict[23]
```

#### `conferencia_service.py` (INTEGRADO)
```
Entrada:    palpites, resultado_oficial
Saída para: feedback_loop_service
Tabelas:    palpites_resultados_reais (lê/escreve)
Chama:      supabase_service
Chamado por: conferir_resultados.py
Novo:       Retornar também features extraídas
```

---

### IA/ML SERVICES - OS 7 MOTORES

```
┌─────────────────────────────────────────┐
│ Cada Motor Segue Este Padrão            │
├─────────────────────────────────────────┤
│ gerar() → List[10 palpites]             │
│ score() → List[score 0-10]              │
│ recebe: peso adaptativo (meta_learning) │
│ produz: métrica de performance          │
└─────────────────────────────────────────┘

Motor 1 (frequência):
  ├─ Arquivo: aprendizado_service_v3.py
  ├─ Entrada: peso * v3_fator_anual
  ├─ Output: score_frequencia
  ├─ Performance: acertos_média
  └─ Tabela: performance_motores_diario (frequência)

Motor 2 (atraso):
  ├─ Arquivo: [via estatisticas_service]
  ├─ Entrada: peso * atraso_fator
  └─ Output: score_atraso
  
Motor 3 (memória):
  ├─ Arquivo: elite_service.py (expandido)
  ├─ Entrada: peso * elite_score
  ├─ Output: score_memoria
  ├─ Reutiliza: elite_structures
  └─ Atualiza: elite_structures (com sucesso)

Motor 4 (cluster):
  ├─ Arquivo: clusterizacao_service.py
  ├─ Entrada: peso * cluster_score
  └─ Output: score_cluster
  
Motor 5 (genética):
  ├─ Arquivo: selecao_genetica_service.py
  ├─ Entrada: peso * genetica_score
  └─ Output: score_genetica
  
Motor 6 (monte carlo):
  ├─ Arquivo: montecarlo_service.py
  ├─ Entrada: peso * mc_score
  └─ Output: score_montecarlo
  
Motor 7 (ensemble):
  ├─ Arquivo: motores_ensemble_service.py
  ├─ Entrada: scores dos 6 anteriores
  ├─ Output: score_ensemble
  └─ Combina: weighted average
```

---

### MODELO SUPERVISIONADO (NOVO)

#### `modelo_supervisionado_service.py`
```
Entrada:    historico_features (última 180 dias)
Saída para: gerar_palpites_diarios.py, feedback_loop_service
Tabelas:    historico_features (lê), modelo_supervisionado_metricas (escreve)
Chama:      sklearn/xgboost, pandas, numpy
Chamado por: 
  - gerar_palpites_diarios.py (predizer score)
  - feedback_loop_service.py (treinar diário)
Novo:       treinar(), predizer(features), salvar_metricas()
```

---

### REPOSITÓRIOS (NOVOS)

#### `historico_features_repo.py`
```
Entrada:    supabase_service
Saída para: modelo_supervisionado_service, conferir_resultados.py
Tabelas:    historico_features (CRUD)
Chama:      supabase_service
Chamado por: conferir_resultados.py (insert), feedback_loop_service (query)
Métodos:    inserir_features, buscar_dataset_ml, atualizar_acertos
```

#### `elite_structures_repo.py`
```
Entrada:    supabase_service
Saída para: elite_service, gerar_palpites_diarios.py
Tabelas:    elite_structures (CRUD)
Chama:      supabase_service
Chamado por: elite_service (gerenciar), gerar_palpites_diarios (reutilizar)
Métodos:    inserir_structure, buscar_elite, atualizar_score
```

#### `peso_motor_repo.py`
```
Entrada:    supabase_service
Saída para: gerar_palpites_diarios.py
Tabelas:    peso_motor_diario (CRUD)
Chama:      supabase_service
Chamado by: gerar_palpites_diarios (obter_hoje), feedback_loop (inserir_novo)
Métodos:    obter_pesos_hoje, inserir_pesos, historico_pesos
```

#### `performance_motores_repo.py`
```
Entrada:    supabase_service
Saída para: meta_learning_service, feedback_loop_service
Tabelas:    performance_motores_diario (CRUD)
Chama:      supabase_service
Chamado by: feedback_loop_service (inserir, query)
Métodos:    inserir_performance, buscar_últimos_30_dias, calcular_média
```

---

### FEEDBACK LOOP (NOVO - Orquestrador)

#### `feedback_loop_service.py`
```
Entrada:    palpites_resultados_reais, historico_features
Saída para: peso_motor_diario, elite_structures, modelo_metricas

Chamadas em sequência:
  1. modelo_supervisionado_service.treinar()
  2. [calcular performance de cada motor]
  3. meta_learning_service.atualizar_pesos_7_motores()
  4. elite_service.gerenciar_elite_structures()
  5. backtest_service.backtest_historico()
  6. [registrar alertas se necessário]

Salva em:
  - modelo_supervisionado_metricas
  - peso_motor_diario
  - elite_structures
  - performance_motores_diario
  - backtest_resultado

Chamado por: [script externo] feedback_loop_handler.py
```

---

### VALIDAÇÃO E MONITORAMENTO

#### `colapso_service.py` (INTEGRADO)
```
Entrada:    meta_validacao_execucoes (histórico)
Saída para: meta_validacao_final.py
Tabelas:    meta_validacao_execucoes (lê)
Chama:      supabase_service
Chamado by: meta_validacao_final.py
Novo:       Integrado com regeneração automática
```

#### `backtest_service.py` (EXPANDIDO)
```
Entrada:    historico_resultados, palpites_históricos
Saída para: feedback_loop_service
Tabelas:    backtest_resultado (escreve)
Chama:      supabase_service, gerar_palpites_diarios (simular)
Chamado by: feedback_loop_service
Novo:       backtest_historico(), validar vs versão anterior
```

#### `elite_service.py` (EXPANDIDO)
```
Entrada:    palpites_resultados_reais, elite_structures_repo
Saída para: gerar_palpites_diarios, feedback_loop_service
Tabelas:    elite_structures (lê/escreve)
Chama:      elite_structures_repo, supabase_service
Chamado by: 
  - gerar_palpites_diarios (reutilizar_elite)
  - feedback_loop_service (gerenciar_elite_structures)
Novo:       gerenciar_elite, reutilizar_elite, regeneracao
```

---

### TRANSFORMAÇÕES EM FEATURES (Órfãos → Integrados)

#### `repeticao_service.py`
```
Antes: Órfão (nunca chamado)
Depois: Feature calculada

Integração:
  ├─ score_repeticao (numeros) → float
  ├─ Chamado por: feature_store_service (como feature #24)
  ├─ Armazenado em: historico_features.repeticoes
  └─ Usado em: modelo_supervisionado (como input)
```

#### `roi_service.py`
```
Antes: Órfão (nunca chamado)
Depois: Métrica de performance

Integração:
  ├─ calcular_roi(acertos, custo) → float
  ├─ Chamado por: feedback_loop_service
  ├─ Armazenado em: performance_motores_diario.roi
  └─ Usado em: meta_learning (calibração)
```

---

## 📍 INTEGRAÇÕES POR SCRIPT

### Scripts Batch

#### `gerar_palpites_diarios.py` (v19.4)
```
Chama:
  ├─ peso_motor_repo.obter_pesos_hoje()
  ├─ 7 motors (com pesos aplicados)
  ├─ feature_store_service.extrair_23_features()
  ├─ modelo_supervisionado_service.predizer()
  ├─ diversidade_service.validar()
  ├─ colapso_service.detectar_colapso_estrategico()
  └─ palpites_repo.salvar_palpites_validos()

Chamado por: vercel.json (23:59)
```

#### `conferir_resultados.py` (v2.0)
```
Chama:
  ├─ palpites_repo.listar_palpites_hoje()
  ├─ resultados_repo.obter_resultado_oficial()
  ├─ conferencia_service.conferir()
  ├─ feature_store_service.extrair_23_features()
  └─ historico_features_repo.inserir_features()

Chamado by: vercel.json (após sorteio)
```

#### `feedback_loop_handler.py` (NOVO - WRAPPER)
```
Chama:
  └─ feedback_loop_service.executar_ciclo_completo()

Chamado by: vercel.json (após conferir_resultados)
Responsabilidade: Orquestração + error handling
```

---

## 🧪 TESTES DE INTEGRAÇÃO

### Teste 1: Feature Store → Modelo
```
1. Extrair features de palpite
2. Passar para modelo
3. Validar score ∈ [0, 10]
```

### Teste 2: Gerar → Conferir → Feedback
```
1. Gerar 10 palpites
2. Simular resultado
3. Conferir e extrair features
4. Treinar modelo
5. Validar novo peso
```

### Teste 3: Elite Memory
```
1. Buscar elite structures
2. Reutilizar em palpite
3. Conferir performance
4. Atualizar score elite
```

### Teste 4: Colapso → Regeneração
```
1. Detectar colapso
2. Acionar regeneração
3. Validar novos palpites
```

### Teste 5: Backtest → Validação
```
1. Executar backtest 100 concursos
2. Comparar v19 vs v20
3. Validar melhoria
```

---

## 📊 DEPENDÊNCIAS EXTERNAS

```
Novo para instalar:
├─ xgboost (modelo supervisionado)
├─ lightgbm (alternativa XGBoost)
├─ scikit-learn (RandomForest)
├─ pandas (manipulação dados)
├─ numpy (cálculos)
└─ scipy (estatísticas)

Já tem:
├─ supabase-py
├─ fastapi
└─ Others no requirements.txt
```

---

**Documento:** Mapa de Integrações v20  
**Status:** Referência completa  
**Próximo:** Código novo + Alterações nos serviços
