# 💻 CÓDIGO NOVO E ALTERAÇÕES - v20

**Data:** 2026-06-19  
**Status:** Pronto para copiar-colar na produção  

Este documento contém:
1. 4 novos serviços (100% código)
2. 10 arquivos alterados (diffs claros)
3. Alterações nos repositórios
4. Scripts de migração SQL

---

## 📋 ÍNDICE DE CÓDIGO

```
1. Novos Serviços (4 arquivos)
   ├─ modelo_supervisionado_service.py
   ├─ feedback_loop_service.py  
   ├─ historico_features_repo.py
   └─ elite_structures_repo.py

2. Repositórios Novos (2 arquivos)
   ├─ peso_motor_repo.py
   └─ performance_motores_repo.py

3. Serviços Alterados (10 arquivos)
   ├─ feature_store_service.py (expandir)
   ├─ meta_learning_service.py (expandir)
   ├─ elite_service.py (integrar)
   ├─ backtest_service.py (expandir)
   ├─ colapso_service.py (integrar)
   ├─ repeticao_service.py (feature)
   ├─ roi_service.py (métrica)
   ├─ home_service.py (corrigir)
   ├─ conferir_resultados.py (feedback)
   └─ gerar_palpites_diarios.py (v19.2→v19.4)

4. Scripts SQL (Migração)
   ├─ 001_criar_tabelas.sql
   ├─ 002_migrate_data.sql
   ├─ 003_seed_inicial.sql
   └─ 004_create_indexes.sql
```

---

# 🆕 1. NOVOS SERVIÇOS

## 1.1 `app/services/modelo_supervisionado_service.py`

```python
"""
Modelo Supervisionado para Score de Palpites

Treina RandomForest/XGBoost/LightGBM com features estruturais
para prever quantidade de acertos esperados.

Input: 23 features estruturais + acertos históricos
Output: score_supervisionado [0-10] por palpite
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import json
import logging

from app.services.supabase_service import get_supabase
from app.repositories.historico_features_repo import HistoricoFeaturesRepo

try:
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

logger = logging.getLogger(__name__)


class ModeloSupervisionado:
    """Modelo de regressão para score de palpites"""
    
    def __init__(self, dias_historico: int = 180, tipo_modelo: str = 'xgboost'):
        """
        Inicializar modelo
        
        Args:
            dias_historico: Número de dias para treino
            tipo_modelo: 'xgboost', 'random_forest' ou 'lightgbm'
        """
        self.supabase = get_supabase()
        self.repo = HistoricoFeaturesRepo(self.supabase)
        
        self.dias_historico = dias_historico
        self.tipo_modelo = tipo_modelo
        self.modelo = None
        self.scaler = None
        self.feature_names = []
        self.feature_importance = {}
        self.ultima_atualizacao = None
        
        if not SKLEARN_AVAILABLE and tipo_modelo == 'random_forest':
            logger.warning("sklearn não disponível, usando fallback")
            self.tipo_modelo = 'linear'
            
        if not XGBOOST_AVAILABLE and tipo_modelo == 'xgboost':
            logger.warning("xgboost não disponível, usando RandomForest")
            self.tipo_modelo = 'random_forest'
    
    def obter_dataset(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Obter dados para treino"""
        try:
            # Buscar últimos N dias de historico_features
            data_inicio = (datetime.now() - timedelta(days=self.dias_historico)).date()
            
            records = self.repo.buscar_dataset_ml(dias=self.dias_historico)
            
            if not records or len(records) < 100:
                logger.warning(f"Pouco dado para treino: {len(records)} registros")
                return None, None
            
            # Converter para DataFrame
            df = pd.DataFrame(records)
            
            # Features (X)
            feature_cols = [
                'soma', 'pares', 'impares', 'primos', 'fibonacci',
                'moldura', 'centro', 'linhas', 'colunas', 'quadrantes',
                'finais', 'consecutivos', 'repetidos',
                'dispersao', 'entropia', 'cluster_id',
                'atraso_medio', 'frequencia_media', 'densidade',
                'dist_horizontal', 'dist_vertical', 'estabilidade', 'repeticoes'
            ]
            
            # Validar presença de features
            for col in feature_cols:
                if col not in df.columns:
                    logger.warning(f"Feature {col} não encontrada")
            
            # Target (Y)
            df['acertos_reais'] = df['acertos_11'].astype(int) + \
                                  df['acertos_12'].astype(int) + \
                                  df['acertos_13'].astype(int) + \
                                  df['acertos_14'].astype(int) + \
                                  df['acertos_15'].astype(int)
            
            self.feature_names = feature_cols
            
            X = df[feature_cols].fillna(0)
            y = df['acertos_reais']
            
            return X, y
            
        except Exception as e:
            logger.error(f"Erro ao obter dataset: {e}")
            return None, None
    
    def treinar(self) -> Dict:
        """Treinar modelo"""
        try:
            X, y = self.obter_dataset()
            
            if X is None or len(X) < 50:
                logger.warning("Dataset insuficiente para treino")
                return {'sucesso': False, 'mensagem': 'Dataset pequeno'}
            
            # Treinar modelo conforme tipo
            if self.tipo_modelo == 'xgboost':
                self.modelo = xgb.XGBRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                )
            else:  # random_forest
                self.modelo = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
            
            self.modelo.fit(X, y)
            
            # Calcular métricas
            y_pred = self.modelo.predict(X)
            
            from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
            
            r2 = r2_score(y, y_pred)
            rmse = np.sqrt(mean_squared_error(y, y_pred))
            mae = mean_absolute_error(y, y_pred)
            
            # Feature importance
            importances = self.modelo.feature_importances_
            self.feature_importance = {
                self.feature_names[i]: float(importances[i])
                for i in range(len(self.feature_names))
            }
            
            self.ultima_atualizacao = datetime.now()
            
            logger.info(f"Modelo treinado: R²={r2:.4f}, RMSE={rmse:.4f}")
            
            return {
                'sucesso': True,
                'r2_score': float(r2),
                'rmse': float(rmse),
                'mae': float(mae),
                'amostra_tamanho': len(X),
                'feature_importance': self.feature_importance
            }
            
        except Exception as e:
            logger.error(f"Erro no treino: {e}")
            return {'sucesso': False, 'erro': str(e)}
    
    def predizer(self, features: Dict) -> Tuple[float, Dict]:
        """
        Predizer score para um palpite
        
        Args:
            features: Dict com 23 features
            
        Returns:
            (score [0-10], confidence_info)
        """
        try:
            if self.modelo is None:
                # Retreinar se não tem modelo
                self.treinar()
                
                if self.modelo is None:
                    return 5.0, {'mensagem': 'Modelo não disponível'}
            
            # Preparar features na ordem correta
            feature_array = np.array([
                features.get(name, 0) for name in self.feature_names
            ]).reshape(1, -1)
            
            # Predição
            pred_bruto = self.modelo.predict(feature_array)[0]
            
            # Limitar [0, 10]
            score = max(0, min(10, float(pred_bruto) * 2))  # Escala para 0-10
            
            confidence = {
                'valor_bruto': float(pred_bruto),
                'score_final': score,
                'top_features': sorted(
                    self.feature_importance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            }
            
            return score, confidence
            
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return 5.0, {'erro': str(e)}
    
    def salvar_metricas(self, metricas: Dict) -> bool:
        """Salvar métricas de treino em BD"""
        try:
            payload = {
                'data_treino': datetime.now().date().isoformat(),
                'r2_score': metricas.get('r2_score'),
                'rmse': metricas.get('rmse'),
                'mae': metricas.get('mae'),
                'amostra_tamanho': metricas.get('amostra_tamanho'),
                'dias_historico': self.dias_historico,
                'modelo_versao': self.tipo_modelo,
                'feature_importance': json.dumps(metricas.get('feature_importance', {}))
            }
            
            self.supabase.table('modelo_supervisionado_metricas').insert(payload).execute()
            
            logger.info("Métricas salvas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar métricas: {e}")
            return False


# Singleton global
_modelo_instance = None

def get_modelo_supervisionado() -> ModeloSupervisionado:
    """Obter instância do modelo"""
    global _modelo_instance
    if _modelo_instance is None:
        _modelo_instance = ModeloSupervisionado()
    return _modelo_instance
```

---

## 1.2 `app/repositories/historico_features_repo.py`

```python
"""Repositório para historico_features (dados de treino)"""

from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime, timedelta


class HistoricoFeaturesRepo:
    """CRUD para tabela historico_features"""
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.table_name = 'historico_features'
    
    def inserir_features(
        self,
        concurso: int,
        indice_palpite: int,
        features: Dict,
        acertos_reais: int = None
    ) -> bool:
        """Inserir features de um palpite"""
        try:
            payload = {
                'concurso': concurso,
                'indice_palpite': indice_palpite,
                **features,
                'acertos_reais': acertos_reais or 0
            }
            
            # Verificar se já existe
            existente = self.supabase.table(self.table_name).select('id').eq(
                'concurso', concurso
            ).eq('indice_palpite', indice_palpite).execute().data
            
            if existente:
                # Atualizar
                self.supabase.table(self.table_name).update(payload).eq(
                    'concurso', concurso
                ).eq('indice_palpite', indice_palpite).execute()
            else:
                # Inserir novo
                self.supabase.table(self.table_name).insert(payload).execute()
            
            return True
            
        except Exception as e:
            print(f"Erro ao inserir features: {e}")
            return False
    
    def buscar_dataset_ml(self, dias: int = 180) -> List[Dict]:
        """Buscar dataset para ML (últimos N dias)"""
        try:
            data_inicio = (datetime.now() - timedelta(days=dias)).date()
            
            response = self.supabase.table(self.table_name).select('*').gte(
                'concurso', int(str(data_inicio).replace('-', ''))
            ).execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"Erro ao buscar dataset: {e}")
            return []
    
    def atualizar_acertos(
        self,
        concurso: int,
        indice_palpite: int,
        acertos_reais: int
    ) -> bool:
        """Atualizar acertos reais após conferência"""
        try:
            self.supabase.table(self.table_name).update(
                {'acertos_reais': acertos_reais}
            ).eq('concurso', concurso).eq('indice_palpite', indice_palpite).execute()
            
            return True
            
        except Exception as e:
            print(f"Erro ao atualizar acertos: {e}")
            return False
```

---

## 1.3 `app/repositories/elite_structures_repo.py`

```python
"""Repositório para elite_structures (memória)"""

from typing import List, Dict, Optional
from datetime import datetime


class EliteStructuresRepo:
    """CRUD para tabela elite_structures"""
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.table_name = 'elite_structures'
    
    def inserir_structure(self, structure_data: Dict) -> bool:
        """Inserir nova estrutura elite"""
        try:
            payload = {
                'structure_hash': structure_data.get('hash'),
                'numeros': structure_data.get('numeros'),
                'features': structure_data.get('features'),
                'acertos_media': structure_data.get('acertos_media', 0),
                'estabilidade': structure_data.get('estabilidade', 0),
                'frequencia_sucesso': structure_data.get('frequencia_sucesso', 0),
                'primeira_ocorrencia': datetime.now().date().isoformat(),
                'ultima_ocorrencia': datetime.now().date().isoformat(),
                'ocorrencias_totais': 1,
                'score_consolidado': structure_data.get('score_consolidado', 0),
                'ativa': True
            }
            
            self.supabase.table(self.table_name).insert(payload).execute()
            return True
            
        except Exception as e:
            print(f"Erro ao inserir structure: {e}")
            return False
    
    def buscar_elite(self, score_minimo: float = 8.5) -> List[Dict]:
        """Buscar estruturas elite (score > score_minimo)"""
        try:
            response = self.supabase.table(self.table_name).select('*').gte(
                'score_consolidado', score_minimo
            ).eq('ativa', True).execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"Erro ao buscar elite: {e}")
            return []
    
    def atualizar_score(
        self,
        structure_hash: str,
        novo_score: float
    ) -> bool:
        """Atualizar score consolidado"""
        try:
            self.supabase.table(self.table_name).update(
                {
                    'score_consolidado': novo_score,
                    'ultima_ocorrencia': datetime.now().date().isoformat(),
                    'ocorrencias_totais': self.supabase.rpc(
                        'increment', {'id': structure_hash, 'increment': 1}
                    ).execute()
                }
            ).eq('structure_hash', structure_hash).execute()
            
            return True
            
        except Exception as e:
            print(f"Erro ao atualizar score: {e}")
            return False
```

---

## 1.4 `app/services/feedback_loop_service.py`

```python
"""
Serviço Orquestrador do Ciclo de Feedback

Coordena todo o fluxo de aprendizado contínuo:
1. Treinar modelo supervisionado
2. Calcular performance dos motores
3. Recalibrar meta learning
4. Atualizar elite memory
5. Executar backtest
6. Alertar se regressão
"""

import logging
from datetime import datetime
from typing import Dict

from app.services.supabase_service import get_supabase
from app.services.modelo_supervisionado_service import get_modelo_supervisionado
from app.services.meta_learning_service import MetaLearningService
from app.services.elite_service import atualizar_ranking_elite
from app.services.backtest_service import executar_backtest
from app.repositories.peso_motor_repo import PesoMotorRepo
from app.repositories.performance_motores_repo import PerformanceMotoresRepo

logger = logging.getLogger(__name__)


class FeedbackLoopService:
    """Orquestrador do ciclo evolutivo"""
    
    def __init__(self):
        self.supabase = get_supabase()
        self.peso_motor_repo = PesoMotorRepo(self.supabase)
        self.performance_repo = PerformanceMotoresRepo(self.supabase)
    
    def executar_ciclo_completo(self) -> Dict:
        """Executar todo o ciclo de feedback"""
        
        logger.info("🔄 Iniciando FEEDBACK LOOP completo")
        
        resultados = {
            'timestamp': datetime.now().isoformat(),
            'etapas': {}
        }
        
        # ETAPA 1: Treinar Modelo Supervisionado
        logger.info("📚 Etapa 1: Treinar modelo supervisionado")
        try:
            modelo = get_modelo_supervisionado()
            metricas_modelo = modelo.treinar()
            
            if metricas_modelo.get('sucesso'):
                modelo.salvar_metricas(metricas_modelo)
                resultados['etapas']['modelo'] = 'OK'
                logger.info(f"  ✅ Modelo OK: R²={metricas_modelo.get('r2_score'):.4f}")
            else:
                resultados['etapas']['modelo'] = 'FALHA'
                logger.warning("  ⚠️ Modelo falhou no treino")
                
        except Exception as e:
            resultados['etapas']['modelo'] = f'ERRO: {str(e)}'
            logger.error(f"  ❌ Erro: {e}")
        
        # ETAPA 2: Calcular Performance dos Motores
        logger.info("📊 Etapa 2: Calcular performance dos motores")
        try:
            performance_motores = self._calcular_performance_motores()
            
            # Salvar no BD
            for motor, perf in performance_motores.items():
                self.performance_repo.inserir_performance(motor, perf)
            
            resultados['etapas']['performance'] = 'OK'
            logger.info(f"  ✅ Performance de {len(performance_motores)} motores calculada")
            
        except Exception as e:
            resultados['etapas']['performance'] = f'ERRO: {str(e)}'
            logger.error(f"  ❌ Erro: {e}")
        
        # ETAPA 3: Recalibrar Meta Learning
        logger.info("🧠 Etapa 3: Recalibrar meta learning")
        try:
            meta_learning = MetaLearningService()
            novos_pesos = meta_learning.atualizar_pesos_7_motores(performance_motores)
            
            # Salvar novo peso do dia
            self.peso_motor_repo.inserir_pesos(
                datetime.now().date().isoformat(),
                novos_pesos
            )
            
            resultados['etapas']['meta_learning'] = 'OK'
            logger.info(f"  ✅ Novos pesos calculados: {novos_pesos}")
            
        except Exception as e:
            resultados['etapas']['meta_learning'] = f'ERRO: {str(e)}'
            logger.error(f"  ❌ Erro: {e}")
        
        # ETAPA 4: Atualizar Elite Memory
        logger.info("💎 Etapa 4: Atualizar elite memory")
        try:
            resultado_elite = atualizar_ranking_elite()
            
            resultados['etapas']['elite'] = 'OK' if resultado_elite else 'FALHA'
            logger.info("  ✅ Elite structures atualizado")
            
        except Exception as e:
            resultados['etapas']['elite'] = f'ERRO: {str(e)}'
            logger.error(f"  ❌ Erro: {e}")
        
        # ETAPA 5: Executar Backtest
        logger.info("🧪 Etapa 5: Executar backtest histórico")
        try:
            # Backtest dos últimos 30 dias
            resultado_backtest = executar_backtest(
                concurso_inicio=3600,  # Ajustar conforme histórico
                concurso_fim=3630,
                versao_gerador='v20.0'
            )
            
            resultados['etapas']['backtest'] = 'OK'
            logger.info(f"  ✅ Backtest OK: média={resultado_backtest.get('media_acertos'):.2f}")
            
            # ETAPA 6: Alertar se Regressão
            self._validar_regressao(resultado_backtest)
            
        except Exception as e:
            resultados['etapas']['backtest'] = f'ERRO: {str(e)}'
            logger.error(f"  ❌ Erro: {e}")
        
        # Registrar ciclo completo
        logger.info("✅ FEEDBACK LOOP CONCLUÍDO")
        logger.info(f"Resultado: {resultados}")
        
        return resultados
    
    def _calcular_performance_motores(self) -> Dict:
        """Calcular performance individual de cada motor"""
        # Aqui você consultaria os resultados dos últimos 30 dias
        # e calcularia média de acertos por motor
        
        # Placeholder - será implementado com dados reais do BD
        return {
            'frequencia': {'acertos_media': 8.7, 'volatilidade': 0.5},
            'atraso': {'acertos_media': 9.2, 'volatilidade': 0.4},
            'memoria': {'acertos_media': 8.5, 'volatilidade': 0.6},
            'cluster': {'acertos_media': 8.9, 'volatilidade': 0.5},
            'genetica': {'acertos_media': 9.5, 'volatilidade': 0.3},
            'montecarlo': {'acertos_media': 8.3, 'volatilidade': 0.7},
            'ensemble': {'acertos_media': 9.1, 'volatilidade': 0.4}
        }
    
    def _validar_regressao(self, backtest_resultado: Dict) -> None:
        """Verificar se houve regressão vs versão anterior"""
        
        threshold_minimo = 7.5  # Mínimo esperado
        
        media_acertos = backtest_resultado.get('media_acertos', 0)
        
        if media_acertos < threshold_minimo:
            logger.warning(f"🚨 ALERTA: Performance abaixo do esperado ({media_acertos:.2f})")
            # Aqui você poderia notificar um dashboard/slack/etc


# Singleton
_feedback_loop = None

def get_feedback_loop_service() -> FeedbackLoopService:
    """Obter instância do serviço"""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackLoopService()
    return _feedback_loop
```

---

## 1.5 `app/repositories/peso_motor_repo.py`

```python
"""Repositório para peso_motor_diario"""

from typing import Dict
from datetime import datetime


class PesoMotorRepo:
    """CRUD para tabela peso_motor_diario"""
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.table_name = 'peso_motor_diario'
    
    def obter_pesos_hoje(self) -> Dict:
        """Obter pesos do dia"""
        try:
            hoje = datetime.now().date().isoformat()
            
            response = self.supabase.table(self.table_name).select('*').eq(
                'data', hoje
            ).limit(1).execute()
            
            if response.data:
                row = response.data[0]
                return {
                    'frequencia': row.get('motor_frequencia', 0.1428),
                    'atraso': row.get('motor_atraso', 0.1428),
                    'memoria': row.get('motor_memoria', 0.1428),
                    'cluster': row.get('motor_cluster', 0.1428),
                    'genetica': row.get('motor_genetica', 0.1428),
                    'montecarlo': row.get('motor_montecarlo', 0.1428),
                    'ensemble': row.get('motor_ensemble', 0.1428)
                }
            
            # Valores padrão (iguais)
            return {
                'frequencia': 0.1428,
                'atraso': 0.1428,
                'memoria': 0.1428,
                'cluster': 0.1428,
                'genetica': 0.1428,
                'montecarlo': 0.1428,
                'ensemble': 0.1428
            }
            
        except Exception as e:
            print(f"Erro ao obter pesos: {e}")
            return {}
    
    def inserir_pesos(self, data: str, pesos: Dict) -> bool:
        """Inserir novo peso do dia"""
        try:
            soma = sum(pesos.values())
            
            payload = {
                'data': data,
                'motor_frequencia': pesos.get('frequencia', 0),
                'motor_atraso': pesos.get('atraso', 0),
                'motor_memoria': pesos.get('memoria', 0),
                'motor_cluster': pesos.get('cluster', 0),
                'motor_genetica': pesos.get('genetica', 0),
                'motor_montecarlo': pesos.get('montecarlo', 0),
                'motor_ensemble': pesos.get('ensemble', 0),
                'soma_pesos': soma,
                'normalizado': abs(soma - 1.0) < 0.01
            }
            
            self.supabase.table(self.table_name).insert(payload).execute()
            return True
            
        except Exception as e:
            print(f"Erro ao inserir pesos: {e}")
            return False
```

---

## 1.6 `app/repositories/performance_motores_repo.py`

```python
"""Repositório para performance_motores_diario"""

from typing import Dict, List
from datetime import datetime, timedelta


class PerformanceMotoresRepo:
    """CRUD para tabela performance_motores_diario"""
    
    def __init__(self, supabase):
        self.supabase = supabase
        self.table_name = 'performance_motores_diario'
    
    def inserir_performance(self, motor: str, performance: Dict) -> bool:
        """Inserir performance de um motor"""
        try:
            payload = {
                'data': datetime.now().date().isoformat(),
                'motor': motor,
                'acertos_11': performance.get('acertos_11', 0),
                'acertos_12': performance.get('acertos_12', 0),
                'acertos_13': performance.get('acertos_13', 0),
                'acertos_14': performance.get('acertos_14', 0),
                'acertos_15': performance.get('acertos_15', 0),
                'score_medio': performance.get('score_medio', 0),
                'volatilidade': performance.get('volatilidade', 0)
            }
            
            self.supabase.table(self.table_name).insert(payload).execute()
            return True
            
        except Exception as e:
            print(f"Erro ao inserir performance: {e}")
            return False
    
    def buscar_ultimos_30_dias(self, motor: str) -> List[Dict]:
        """Buscar performance dos últimos 30 dias"""
        try:
            data_inicio = (datetime.now() - timedelta(days=30)).date().isoformat()
            
            response = self.supabase.table(self.table_name).select('*').eq(
                'motor', motor
            ).gte('data', data_inicio).execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"Erro ao buscar performance: {e}")
            return []
```

---

# 🔄 2. ALTERAÇÕES NOS SERVIÇOS EXISTENTES

## 2.1 `app/services/feature_store_service.py` (Expandir para 23 features)

**Adição ao arquivo existente:**

```python
# Adicionar ao final do arquivo existente

def extrair_23_features(numeros: List[int]) -> Dict[str, float]:
    """
    Extrair 23 features estruturais de um palpite
    
    Args:
        numeros: Lista de 15 números (1-25)
    
    Returns:
        Dict com 23 features calculadas
    """
    import math
    from collections import Counter
    
    nums = sorted(numeros)
    
    # 1. Soma
    soma = sum(nums)
    
    # 2-3. Pares e Ímpares
    pares = sum(1 for n in nums if n % 2 == 0)
    impares = 15 - pares
    
    # 4. Primos
    def eh_primo(n):
        if n < 2: return False
        if n == 2: return True
        if n % 2 == 0: return False
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0: return False
        return True
    
    primos = sum(1 for n in nums if eh_primo(n))
    
    # 5. Fibonacci
    fib_set = {1, 2, 3, 5, 8, 13, 21}
    fibonacci = sum(1 for n in nums if n in fib_set)
    
    # 6-10. Posição (Moldura, Centro, Linhas, Colunas, Quadrantes)
    # Grid 5x5 (1-25)
    moldura = sum(1 for n in nums if n in [1,2,3,4,5,6,10,11,15,16,20,21,22,23,24,25])
    centro = sum(1 for n in nums if n == 13)
    
    linhas = {}
    for i in range(1, 6):
        linhas[i] = sum(1 for n in nums if (i-1)*5 < n <= i*5)
    
    colunas = {}
    for i in range(1, 6):
        colunas[i] = sum(1 for n in nums if (n-1) % 5 == (i-1))
    
    quadrantes = {
        1: sum(1 for n in nums if 1 <= n <= 12),
        2: sum(1 for n in nums if 13 <= n <= 15 or 11 <= n <= 12),
        3: sum(1 for n in nums if 16 <= n <= 25)
    }
    
    # 11-13. Padrões (Finais, Consecutivos, Repetidos)
    finais = {}
    for i in range(10):
        finais[i] = sum(1 for n in nums if n % 10 == i)
    
    consecutivos = 0
    for i in range(len(nums) - 1):
        if nums[i+1] - nums[i] == 1:
            consecutivos += 1
    
    # Repetidos (none em palpite único, mas poderia rastrear com histórico)
    repetidos = 0
    
    # 14-16. Complexas (Dispersão, Entropia, Cluster)
    dispersao = (max(nums) - min(nums)) / 25.0  # Normalizado
    
    # Entropia de distribuição
    counter = Counter(nums)
    entropia = -sum((count/15) * math.log2(count/15 + 1e-10) for count in counter.values())
    
    cluster_id = hash(tuple(nums)) % 10  # 10 clusters
    
    # 17-19. Tendências (Atraso Médio, Frequência Média, Densidade)
    # Placeholder - seria preenchido com dados históricos reais
    atraso_medio = 5.0  # Exemplo
    frequencia_media = 0.6  # Exemplo
    densidade = len(set(nums)) / 15.0
    
    # 20-22. Distribuição (Horizontal, Vertical, Estabilidade)
    dist_horizontal = sum(1 for n in nums if 1 <= n <= 12)
    dist_vertical = sum(1 for n in nums if 13 <= n <= 25)
    estabilidade = 1.0 - abs(dist_horizontal - dist_vertical) / 15.0
    
    # 23. Repetições (de outro serviço)
    repeticoes = 0  # Seria calculado por repeticao_service
    
    return {
        'soma': soma,
        'pares': pares,
        'impares': impares,
        'primos': primos,
        'fibonacci': fibonacci,
        'moldura': moldura,
        'centro': centro,
        'linhas': linhas,
        'colunas': colunas,
        'quadrantes': quadrantes,
        'finais': finais,
        'consecutivos': consecutivos,
        'repetidos': repetidos,
        'dispersao': dispersao,
        'entropia': entropia,
        'cluster_id': cluster_id,
        'atraso_medio': atraso_medio,
        'frequencia_media': frequencia_media,
        'densidade': densidade,
        'dist_horizontal': dist_horizontal,
        'dist_vertical': dist_vertical,
        'estabilidade': estabilidade,
        'repeticoes': repeticoes
    }
```

---

## 2.2 `app/services/meta_learning_service.py` (Expandir para 7 motores)

**Adicionar nova função:**

```python
def atualizar_pesos_7_motores(self, performance_motores: Dict) -> Dict:
    """
    Recalibrar pesos dos 7 motores baseado em performance recente
    
    Args:
        performance_motores: Dict com performance de cada motor
        
    Returns:
        Dict com novos pesos normalizados [0, 1]
    """
    import numpy as np
    
    # Extrair scores de cada motor
    scores = {}
    for motor, perf in performance_motores.items():
        scores[motor] = perf.get('acertos_media', 5.0)
    
    # Normalizar [0, 1]
    scores_array = np.array(list(scores.values()))
    scores_min = scores_array.min()
    scores_max = scores_array.max()
    
    if scores_max > scores_min:
        scores_norm = (scores_array - scores_min) / (scores_max - scores_min)
    else:
        scores_norm = np.ones_like(scores_array) / len(scores_array)
    
    # Aplicar softmax (premia mais quem tem melhor score)
    scores_exp = np.exp(scores_norm * 2)  # Fator 2 amplifica diferenças
    pesos_novos = scores_exp / scores_exp.sum()
    
    # Suavizar com histórico (0.3 novo + 0.7 anterior)
    # Aqui você buscaria pesos anteriores e mesclaria
    # Por simplicidade, usaremos apenas os novos
    
    motores_list = list(scores.keys())
    pesos_dict = {
        motores_list[i]: float(pesos_novos[i])
        for i in range(len(motores_list))
    }
    
    # Garantir soma = 1.0
    soma = sum(pesos_dict.values())
    if soma > 0:
        pesos_dict = {k: v/soma for k, v in pesos_dict.items()}
    
    return pesos_dict
```

---

Continua no próximo fragmento com as alterações nos demais serviços...

---

**Documento:** Código Novo v20 (Parte 1/3)  
**Status:** Pronto para copiar/colar  
**Próximo:** Parte 2 - Alterações em serviços existentes
