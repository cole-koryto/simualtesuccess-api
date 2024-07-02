from pydantic import BaseModel
from typing import List


class SpendingSource(BaseModel):
    title: str
    amount: float
    starting_age: int
    ending_age: int
    growth: float


class IncomeSource(BaseModel):
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
    percentiles: List[int]
    distribution_type: str
    random_state: int = None
    income_sources: List[IncomeSource]
    spending_sources: List[SpendingSource]
    