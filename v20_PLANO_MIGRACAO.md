# 📋 PLANO DE MIGRAÇÃO v20 - SISTEMA EVOLUTIVO

**Data:** 2026-06-19  
**Duração Estimada:** 2-3 semanas de desenvolvimento  
**Complexidade:** Alta (múltiplas integrações)  
**Risco:** Médio (pode ser feito incrementalmente)  

---

## 📑 ÍNDICE

1. [Fases de Implementação](#fases)
2. [Tabelas Supabase](#tabelas)
3. [Serviços Novos](#novos)
4. [Alterações de Serviços](#alteracoes)
5. [Scripts de Migração](#scripts)
6. [Rollback Plan](#rollback)

---

## 🎯 FASES DE IMPLEMENTAÇÃO {#fases}

### FASE 1: INFRAESTRUTURA (Semana 1)
**Objetivo:** Criar base de dados e repos para suportar arquitetura

#### 1.1 Criar Tabelas Supabase
```
🎯 Criar 6 tabelas novas:
├─ historico_features (matriz de features)
├─ elite_structures (memória de estruturas)
├─ peso_motor_diario (pesos adaptativos)
├─ performance_motores_diario (tracking)
├─ modelo_supervisionado_metricas (métricas ML)
└─ backtest_resultado (validação)

Scripts: migrations/001_criar_tabelas_historico.sql
Tempo: 1h (criação) + 4h (testes)
```

**Checklist:**
- [ ] Executar script SQL
- [ ] Criar índices
- [ ] Validar constraints
- [ ] Seed com dados iniciais (se necessário)

#### 1.2 Criar Repositórios
```
Novos arquivos:
├─ app/repositories/historico_features_repo.py (CRUD)
├─ app/repositories/elite_structures_repo.py (CRUD)
├─ app/repositories/peso_motor_repo.py (CRUD)
├─ app/repositories/performance_motores_repo.py (CRUD)
└─ app/repositories/modelo_metricas_repo.py (CRUD)

Tempo: 2h (5 arquivos × 24 min cada)
```

**Checklist:**
- [ ] Criar 5 repositórios
- [ ] Testar cada método CRUD
- [ ] Integrar com supabase_service

#### 1.3 Corrigir Imports Inválidos
```
Arquivo: app/services/home_service.py
Erro: from app.core.supabase import supabase (não existe)
Solução: from app.services.supabase_service import get_supabase

Tempo: 30min
```

**Checklist:**
- [ ] Corrigir home_service.py
- [ ] Testar rota GET /home
- [ ] Validar sem erro de import

#### 1.4 Remover Legacy Code
```
Arquivo: app/services/lotofacil_service.py
Razão: Todo comentado, funcionalidade integrada

Arquivo: api/repositories/palpites_repo.py
Razão: Duplicado com app/repositories/

Tempo: 15min
```

**Checklist:**
- [ ] Backup de lotofacil_service.py
- [ ] Remover arquivo
- [ ] Verificar nenhuma referência
- [ ] Mesmo com api/repositories/palpites_repo.py

---

### FASE 2: FEATURE ENGINEERING (Semana 1-2)
**Objetivo:** Implementar extração centralizada de 23 features

#### 2.1 Expandir feature_store_service.py
```python
# Novo: app/services/feature_store_service.py (expandido)

Adicionar 23 features:
├─ Básicas: soma, pares, ímpares, primos, fibonacci
├─ Posição: moldura, centro, linhas, colunas, quadrantes
├─ Padrão: finais, consecutivos, repetidos
├─ Complexas: dispersão, entropia, cluster, atraso_médio, frequência_média
└─ Distribuição: densidade, dist_horizontal, dist_vertical, estabilidade

Função nova:
  extrair_23_features(numeros: List[int]) → Dict[str, float]

Tempo: 4h
```

**Checklist:**
- [ ] Expandir feature_store_service.py
- [ ] Implementar 23 features
- [ ] Validar cada feature com dados conhecidos
- [ ] Testar performance (< 100ms por palpite)

#### 2.2 Criar historico_features_repo.py
```python
# Novo: app/repositories/historico_features_repo.py

Métodos:
- inserir_features(concurso, indice, features_dict, acertos)
- buscar_por_concurso(concurso) → List
- buscar_dataset_ml(dias=180) → (X, y)
- atualizar_acertos(concurso, indice, acertos_reais)

Tempo: 2h
```

**Checklist:**
- [ ] Criar repo
- [ ] Testar insert/update
- [ ] Validar dataset export para ML

#### 2.3 Integrar em conferir_resultados.py
```python
# Alteração: scripts/conferir_resultados.py

Adicionar após conferência:
1. Extrair features do palpite
2. Armazenar em historico_features
3. Registrar acertos reais

Novo fluxo:
  conferir_resultados() 
    ├─ [existente] confere palpites vs oficial
    ├─ [novo] extrai features
    └─ [novo] persiste em historico_features

Tempo: 1h
```

**Checklist:**
- [ ] Modificar conferir_resultados.py
- [ ] Testar fluxo completo
- [ ] Validar dados em historico_features

---

### FASE 3: MODELO SUPERVISIONADO (Semana 2)
**Objetivo:** Implementar ML para score supervisionado

#### 3.1 Criar modelo_supervisionado_service.py
```python
# Novo: app/services/modelo_supervisionado_service.py

Classe: ModeloSupervisionado
  __init__(dias_historico=180, tipo_modelo='xgboost')
  treinar() → metricas
  predizer(features) → Dict[score, feature_importance]
  salvar_metricas() → void

Dependências:
  - pandas, numpy
  - sklearn ou xgboost/lightgbm
  - supabase_service

Tempo: 6h
```

**Checklist:**
- [ ] Implementar classe
- [ ] Treinar com dados históricos
- [ ] Validar R² > 0.4
- [ ] Implementar fallback se falhar

#### 3.2 Integrar em gerar_palpites_diarios.py
```python
# Alteração: scripts/gerar_palpites_diarios.py (v19.2 → v19.3)

Adição:
  modelo = ModeloSupervisionado()
  score_supervisionado = modelo.predizer(features_palpite)
  
Ensemble final:
  score_final = (
    0.7 * score_motores +
    0.3 * score_supervisionado
  )

Tempo: 2h
```

**Checklist:**
- [ ] Integrar modelo em gerar_palpites
- [ ] Validar scores [0, 10]
- [ ] Testar com dados conhecidos

#### 3.3 Criar script de treino diário
```bash
# Novo: scripts/treinar_modelo_diario.py

Executar após conferencia:
  1. Buscar últimos 180 dias de features
  2. Treinar modelo
  3. Salvar métricas
  4. Salvar modelo em disco

Tempo: 1h
```

**Checklist:**
- [ ] Criar script
- [ ] Agendar em vercel.json
- [ ] Testar execução

---

### FASE 4: META LEARNING (Semana 2-3)
**Objetivo:** Adaptar pesos dos 7 motores dinamicamente

#### 4.1 Expandir meta_learning_service.py
```python
# Alteração: app/services/meta_learning_service.py (v3 → v4)

Novo: atualizar_pesos_7_motores()
  Input:
    - performance_frequencia (última semana)
    - performance_atraso
    - performance_memoria
    - performance_cluster
    - performance_genetica
    - performance_montecarlo
    - performance_ensemble
  
  Processing:
    1. Normalizar [0, 1]
    2. Aplicar softmax (premia melhor)
    3. Suavizar com histórico (0.3 * novo + 0.7 * anterior)
    4. Garantir soma = 1.0
  
  Output:
    - peso_motor_diario (7 valores)

Tempo: 3h
```

**Checklist:**
- [ ] Implementar atualizar_pesos_7_motores
- [ ] Testar normalização
- [ ] Validar suma de pesos ≈ 1.0

#### 4.2 Criar peso_motor_diario_repo.py
```python
# Novo: app/repositories/peso_motor_repo.py

Métodos:
- inserir_pesos(data, pesos_dict)
- obter_pesos_hoje() → Dict
- obter_pesos_por_data(data) → Dict
- historico_pesos(dias=30) → List

Tempo: 1h
```

**Checklist:**
- [ ] Criar repo
- [ ] Testar insert/select
- [ ] Validar formato

#### 4.3 Integrar em gerar_palpites_diarios.py
```python
# Alteração: scripts/gerar_palpites_diarios.py (v19.3 → v19.4)

Adição:
  pesos_motores = peso_motor_repo.obter_pesos_hoje()
  
  score_motor_1 = aprendizado_service.gerar() * pesos_motores['frequencia']
  score_motor_2 = atraso_service.gerar() * pesos_motores['atraso']
  ...
  
  score_ponderado = sum(scores)

Tempo: 1h
```

**Checklist:**
- [ ] Carregar pesos do BD
- [ ] Aplicar pesos aos motores
- [ ] Testar ponderação

#### 4.4 Integrar em feedback_loop
```bash
# Scripts/feedback_loop_service.py (novo)

Após conferência:
  1. Calcular performance de cada motor
  2. Atualizar meta_learning
  3. Salvar novos pesos em peso_motor_diario
  4. Registrar em performance_motores_diario

Tempo: 2h
```

**Checklist:**
- [ ] Criar script
- [ ] Testar fluxo completo
- [ ] Validar métricas salvas

---

### FASE 5: INTEGRAÇÃO DE SERVIÇOS ÓRFÃOS (Semana 3)
**Objetivo:** Incorporar backtest, elite, colapso

#### 5.1 Expandir elite_service.py
```python
# Alteração: app/services/elite_service.py (v1 → v2)

Novo: gerenciar_elite_structures()
  ├─ Buscar estruturas bem-sucedidas recentes
  ├─ Armazenar em elite_structures (BD)
  ├─ Manter histórico de 365 dias
  └─ Permitir reutilização

Novo: reutilizar_elite()
  ├─ Buscar estruturas com score > 8.5
  ├─ Adicionar 10% mutação
  ├─ Incorporar ao ensemble
  └─ Rastrear origem

Tempo: 3h
```

**Checklist:**
- [ ] Expandir elite_service
- [ ] Implementar gerenciamento
- [ ] Testar reutilização

#### 5.2 Expandir backtest_service.py
```python
# Alteração: app/services/backtest_service.py (v1 → v2)

Novo: backtest_historico()
  Simular gerar palpites para cada concurso:
  
  for concurso in range(3300, hoje):
    dados_ate_concurso = historico[:concurso]
    palpites = gerar_com_dados(dados_ate_concurso)
    resultado_real = buscar_resultado(concurso)
    acertos = conferir(palpites, resultado_real)
    salvar_em_backtest_resultado()

Tempo: 4h (com otimizações)
```

**Checklist:**
- [ ] Implementar loop histórico
- [ ] Otimizar performance
- [ ] Validar dados

#### 5.3 Integração em feedback_loop
```python
# Scripts/feedback_loop_service.py

Adicionar:
  1. Executar backtest (últimos 30 dias)
  2. Registrar resultados
  3. Validar melhoria vs versão anterior
  4. Alertar se piora > 5%

Tempo: 2h
```

**Checklist:**
- [ ] Integrar backtest no loop
- [ ] Testar alertas
- [ ] Validar comparação

#### 5.4 Expandir colapso_service.py
```python
# Alteração: app/services/colapso_service.py (v1 → v2)

Integrar em meta_validacao_final:
  ├─ Detectar convergência
  ├─ Verificar entropia
  ├─ Validar dispersão
  └─ Se colapso: acionar regeneração

Tempo: 1h
```

**Checklist:**
- [ ] Integrar detectores
- [ ] Testar regeneração
- [ ] Validar sem queda de performance

#### 5.5 Expandir repeticao_service.py
```python
# Alteração: app/services/repeticao_service.py (v1 → v2)

Transformar em feature:
  ├─ Calcular repetição estrutural
  ├─ Incorporar em historico_features
  ├─ Usar no modelo supervisionado
  └─ Validar importância

Tempo: 1h
```

**Checklist:**
- [ ] Transformar em feature
- [ ] Validar cálculo
- [ ] Testar importância

#### 5.6 Expandir roi_service.py
```python
# Alteração: app/services/roi_service.py (v1 → v2)

Transformar em métrica:
  ├─ Calcular ROI por motor
  ├─ Rastrear custo vs retorno
  ├─ Integrar em performance_motores_diario
  └─ Usar para calibração

Tempo: 1h
```

**Checklist:**
- [ ] Implementar cálculos
- [ ] Rastrear em tabela
- [ ] Testar integração

---

### FASE 6: TESTES E VALIDAÇÃO (Semana 3)
**Objetivo:** Garantir funcionamento do ciclo completo

#### 6.1 Testes Unitários
```
Para cada novo serviço/função:
├─ Teste de entrada válida
├─ Teste de entrada inválida
├─ Teste de performance
└─ Teste de integração

Cobertura esperada: > 80%
Tempo: 8h
```

**Checklist:**
- [ ] 50+ testes de unidade
- [ ] Todos passando
- [ ] Coverage > 80%

#### 6.2 Testes de Integração
```
Fluxos completos:
1. Feature Store → Modelo Supervisionado
2. Meta Learning → Gerar Palpites
3. Conferência → Feedback Loop
4. Backtest → Validação
5. Elite Memory → Reutilização
6. Colapso Detection → Regeneração

Tempo: 6h
```

**Checklist:**
- [ ] 6 fluxos testados
- [ ] Dados consistentes
- [ ] Sem erros

#### 6.3 Teste de Carga
```
Simulações:
├─ Gerar 100 palpites
├─ Extrair 1000 features
├─ Treinar modelo com 1 ano histórico
└─ Executar backtest de 100 concursos

Validar < 10 minutos total
Tempo: 4h
```

**Checklist:**
- [ ] Todos executáveis
- [ ] Performance aceitável
- [ ] Sem memory leaks

#### 6.4 Teste de Regressão
```
Comparar:
- v19.2 (atual) vs v20.0 (novo)
- Mesmos dados de entrada
- Validar scores são superiores
- Backtest mostra melhoria

Tempo: 2h
```

**Checklist:**
- [ ] v20 supera v19 em backtest
- [ ] Sem regressão
- [ ] Pronto para produção

---

### FASE 7: DEPLOY (Semana 4)
**Objetivo:** Migrar para produção de forma segura

#### 7.1 Migração de Dados
```bash
Script: migrations/002_migrate_data.sql

1. Exportar dados históricos
2. Extrair features (batch de historico_resultados)
3. Inserir em historico_features
4. Validar integridade

Tempo: 2h (pode rodar offline)
```

**Checklist:**
- [ ] Dados exportados
- [ ] Features extraídas
- [ ] Integridade validada

#### 7.2 Seed de Tabelas
```bash
Script: migrations/003_seed_inicial.sql

1. peso_motor_diario: pesos iguais [0.1428, 0.1428, ...]
2. elite_structures: estruturas históricas bem-sucedidas
3. performance_motores_diario: seed com versão anterior

Tempo: 1h
```

**Checklist:**
- [ ] Pesos inicializados
- [ ] Elite structures populadas
- [ ] Performance histórica preservada

#### 7.3 Blue-Green Deployment
```
1. Manter v19.2 em produção (Blue)
2. Deployar v20.0 em staging (Green)
3. Comparar 3 dias de palpites
4. Se OK → trocar rota de produção
5. Manter v19 como fallback por 1 semana

Tempo: 3 dias (monitoramento)
```

**Checklist:**
- [ ] Staging com v20 funcionando
- [ ] 3 dias comparação
- [ ] Metrics superiores vs v19
- [ ] Deploy em prod
- [ ] Monitoramento ativo

#### 7.4 Rollback Plan
```
Se algo der errado:
1. Voltar para v19.2 (10 min)
2. Restaurar dados backup (15 min)
3. Reiniciar ciclo
4. Investigar erro
5. Hotfix e retry

Tempo total: 25 min
```

**Checklist:**
- [ ] Backup diário automático
- [ ] Plano documentado
- [ ] Teste de rollback OK

---

## 🗄️ TABELAS SUPABASE {#tabelas}

### Criação de Tabelas
Ver `migrations/001_criar_tabelas_historico.sql`

Tabelas:
1. `historico_features` - Features de cada palpite
2. `elite_structures` - Memória de estruturas bem-sucedidas
3. `peso_motor_diario` - Pesos adaptativos
4. `performance_motores_diario` - Tracking de performance
5. `modelo_supervisionado_metricas` - Métricas do ML
6. `backtest_resultado` - Resultados de backtesting

---

## 🆕 SERVIÇOS NOVOS {#novos}

### 1. `modelo_supervisionado_service.py`
Ver: Implementação completa em CÓDIGO_NOVO.md

### 2. `feedback_loop_service.py`
Ver: Implementação completa em CÓDIGO_NOVO.md

### 3. `historico_features_repo.py`
Ver: Implementação completa em CÓDIGO_NOVO.md

### 4. `elite_structures_repo.py`
Ver: Implementação completa em CÓDIGO_NOVO.md

---

## 🔄 ALTERAÇÕES DE SERVIÇOS {#alteracoes}

### Matriz de Alterações

| Arquivo | Versão Atual | Nova Versão | Alterações |
|---------|--------------|-------------|-----------|
| `feature_store_service.py` | v1 | v2 | Adicionar 23 features |
| `meta_learning_service.py` | v3 | v4 | Pesos para 7 motores |
| `gerar_palpites_diarios.py` | v19.2 | v19.4 | Integrar pesos + modelo |
| `conferir_resultados.py` | v1 | v2 | Extrair features |
| `elite_service.py` | v1 | v2 | Gerenciamento elite |
| `backtest_service.py` | v1 | v2 | Backtest histórico |
| `colapso_service.py` | v1 | v2 | Integração com meta_validacao |
| `home_service.py` | v1 (quebrado) | v2 (corrigido) | Corrigir import |
| `repeticao_service.py` | v1 (órfão) | v2 (feature) | Integrar com features |
| `roi_service.py` | v1 (órfão) | v2 (métrica) | Integrar com performance |

---

## 🛠️ SCRIPTS DE MIGRAÇÃO {#scripts}

Ver: `scripts/migration_v19_to_v20/`

```
├─ 001_criar_tabelas_historico.sql
├─ 002_migrate_data.sql
├─ 003_seed_inicial.sql
├─ 004_create_indexes.sql
└─ test_migration.py
```

---

## 🔙 ROLLBACK PLAN {#rollback}

### Se algo der errado:

```bash
# Passo 1: Restaurar código
git revert HEAD~7:HEAD  # Desfazer últimas 7 commits

# Passo 2: Restaurar BD
psql -U postgres -d palpiteiro < backups/pre_v20.sql

# Passo 3: Reiniciar serviços
systemctl restart palpiteiro

# Passo 4: Validar
curl http://localhost/health
```

---

## 📊 TIMELINE TOTAL

```
Semana 1 (21h):
├─ Fase 1: Infraestrutura (8h)
└─ Fase 2: Feature Engineering (13h)

Semana 2 (20h):
├─ Fase 2: Feature Engineering (continuação) (2h)
├─ Fase 3: Modelo Supervisionado (9h)
└─ Fase 4: Meta Learning (9h)

Semana 3 (22h):
├─ Fase 4: Meta Learning (continuação) (2h)
├─ Fase 5: Integração de Órfãos (10h)
└─ Fase 6: Testes e Validação (10h)

Semana 4 (3 dias monitoramento + Deploy):
├─ Fase 7: Deploy (6h desenvolvimento)
└─ Blue-Green: 3 dias monitoramento

Total: ~70h desenvolvimento + 3 dias staging
```

---

## ✅ CHECKLIST FINAL

- [ ] Fase 1: Infraestrutura OK
- [ ] Fase 2: Features OK
- [ ] Fase 3: Modelo OK
- [ ] Fase 4: Meta Learning OK
- [ ] Fase 5: Integrações OK
- [ ] Fase 6: Testes OK
- [ ] Fase 7: Deploy Staging OK
- [ ] Blue-Green OK
- [ ] Production OK
- [ ] Rollback testado

---

**Documento:** Plano de Migração v20  
**Status:** Pronto para execução  
**Próxima:** Código novo + alterações nos serviços
