from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JogoHistorico(BaseModel):
    concurso: int
    tipo: str  # fixo | estatistico
    numeros: List[int]
    acertos: int
    valor_aposta: float
    valor_premio: float
    roi: float

    score_medio: Optional[float] = None
    score_final: Optional[float] = None
    penalidade_sequencia: Optional[float] = None
    metricas: Optional[dict] = None

    data_registro: datetime = datetime.utcnow()
