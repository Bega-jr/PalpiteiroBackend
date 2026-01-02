from pydantic import BaseModel, conlist
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class TipoJogo(str, Enum):
    fixo = "fixo"
    estatistico = "estatistico"

class HistoricoCreate(BaseModel):
    numeros: conlist(int, min_items=15, max_items=18)  # Garante 15 a 18 números
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
