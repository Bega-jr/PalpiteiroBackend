from pydantic import BaseModel, conlist, Field
from typing import List, Optional
from datetime import datetime, date
from uuid import UUID
from enum import Enum

# --- ENUMS E SCHEMAS DE HISTÓRICO (Originais) ---

class TipoJogo(str, Enum):
    fixo = "fixo"
    estatistico = "estatistico"

class HistoricoCreate(BaseModel):
    numeros: conlist(int, min_length=15, max_length=18)  
    tipo: TipoJogo = TipoJogo.estatistico
    score_medio: Optional[float] = None
    score_final: Optional[float] = None
    penalidade_sequencia: Optional[float] = None
    concurso_alvo: Optional[int] = None
    valor_aposta: Optional[float] = 3.0

class HistoricoRead(BaseModel):
    id: str
    user_id: UUID
    numeros: List[int]
    tipo: TipoJogo
    data_aposta: datetime
    score_medio: Optional[float] = None
    score_final: Optional[float] = None
    penalidade_sequencia: Optional[float] = None
    concurso_referente: Optional[int] = None
    acertos: Optional[int] = None
    valor_aposta: float
    premio: float

# --- NOVOS SCHEMAS PARA ESTATÍSTICAS (Adicionados para o Frontend) ---

class EstatisticaNumero(BaseModel):
    numero: int
    frequencia: int = 0
    atraso: int = 0
    score: float = 0.0

class AnaliseDiaria(BaseModel):
    soma_media: float = 0.0
    pares_media: float = 0.0
    impares_media: float = 0.0
    primos_media: float = 0.0
    data_referencia: Optional[date] = None

class CicloInfo(BaseModel):
    faltam: List[int] = Field(default_factory=list)
    total_faltam: int = 0

class DashboardEstatisticas(BaseModel):
    """Este é o modelo que o frontend React espera receber"""
    estatisticas: List[EstatisticaNumero] = Field(default_factory=list)
    analise: Optional[AnaliseDiaria] = None
    ciclo: Optional[CicloInfo] = None
