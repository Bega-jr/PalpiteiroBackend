from pydantic import BaseModel
from typing import List, Optional

class Rateio(BaseModel):
    faixa: int
    ganhadores: int
    premio_individual: float
    total: float

class Concurso(BaseModel):
    concurso: int
    data_sorteio: str
    dezenas: List[str]
    premio_principal: float
    rateios: List[Rateio]
    arrecadacao: float
    estimativa_premio: Optional[float]
    observacao: Optional[str]
