from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JogoHistorico(BaseModel):
    id: str
    data: datetime
    tipo: str  # fixo | estatistico
    numeros: List[int]

    score_medio: Optional[float] = None
    score_final: Optional[float] = None
    penalidade_sequencia: Optional[float] = None

    concurso_referente: Optional[int] = None
    acertos: Optional[int] = None

    valor_aposta: float = 3.0
    premio: float = 0.0
