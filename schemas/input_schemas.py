from pydantic import BaseModel
from typing import List


class Source(BaseModel):
    title: str
    amount: float
    starting_age: int
    ending_age: int
    growth: float


class SimulationInputPayload(BaseModel):
    annual_return: float
    return_std: float
    current_balance: float
    current_age: int
    life_expectancy: int
    inflation: float
    num_simulations: int
    percentiles: List[float]
    distribution_type: str
    random_state: int | None = None
    income_sources: List[Source]
    spending_sources: List[Source]
    