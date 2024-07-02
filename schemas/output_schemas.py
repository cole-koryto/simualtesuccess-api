from pydantic import BaseModel
from typing import List


class SummaryStatistics(BaseModel):
    title: str
    min: float
    max: float
    mean: float
    std: float
    

class SimulationSummary(BaseModel):
    summaries = List[SummaryStatistics]
    success_rate: float










class SimulationOutputPayload(BaseModel):
    summaries = List[SummaryStatistics]
    success_rate: float
    