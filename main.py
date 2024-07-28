from fastapi import FastAPI, HTTPException
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import math
import numpy as np
import random
from schemas.input_schemas import SimulationInputPayload, Source
from scipy.stats import laplace, norm
import uvicorn


# configure FastAPI 
app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)

    
# gets balances of percentiles over simulation
def get_percentile_balances(percentile_sets, balance_history):
    percentile_balance_history = {}
    for percentile in percentile_sets:
        percentile_balance_history[percentile] = {}
        for year in balance_history:
            percentile_balance_history[percentile][year] = balance_history[year][percentile_sets[percentile]["balance_index"]]

    return percentile_balance_history


# returns the final balances that fall in the given percentiles
def get_balance_percentiles(percentiles, final_balances):
    percentile_sets = {}
    for percentile in percentiles:
        found_balance = float(np.percentile(final_balances, percentile, method="closest_observation"))
        percentile_sets[percentile] = {"balance_amount": found_balance, "balance_index": int(np.where(np.isclose(final_balances, found_balance, rtol=0, atol=0.01))[0][0])}

    return percentile_sets


# prints summary of simulations results
def get_simulation_summary(final_balance_history, final_return_history, simulation_inputs):
    simulation_summary = {
        "balance_summary": {"min": np.min(final_balance_history), "max": np.max(final_balance_history), "mean": np.mean(final_balance_history), "std": np.std(final_balance_history)},
        "return_summary": {"min": np.min(final_return_history), "max": np.max(final_return_history), "mean": np.mean(final_return_history), "std": np.std(final_return_history)},
        "success_rate": sum(balance >= 0 for balance in final_balance_history) / len(final_balance_history)}
    return simulation_summary


# determines total income, total spendign, and net income by year from income and expenses #TODO test growth and inflation
def get_cashflows(simulation_inputs):
    income_by_year = {}
    spending_by_year = {}
    net_income_by_year = {}
    for year_from_start, year in enumerate(range(simulation_inputs.current_age, simulation_inputs.life_expectancy)):
        total_income = 0
        total_spending = 0

        # adds all incomes
        for income_source in simulation_inputs.income_sources:
            if income_source.starting_age <= year < income_source.ending_age:
                total_income += income_source.amount * (1+income_source.growth)**(year-income_source.starting_age)

        # adds all expenses
        for spending_source in simulation_inputs.spending_sources:
            if spending_source.starting_age <= year < spending_source.ending_age:
                total_spending -= spending_source.amount * (1+spending_source.growth)**(year-spending_source.starting_age) * (1+simulation_inputs.inflation)**year_from_start

        income_by_year[year] = total_income
        spending_by_year[year] = total_spending
        net_income_by_year[year] = total_income + total_spending

    return income_by_year, spending_by_year, net_income_by_year 


# runs simulations to get balance and return histories
def run_simulations(simulation_inputs, net_income_by_year):
    # generates all random states for return distributions
    random.seed(simulation_inputs.random_state)
    balance_history = {}
    return_history = {}
    current_balances = np.full(simulation_inputs.num_simulations, simulation_inputs.current_balance)
    for year_index, year in enumerate(range(simulation_inputs.current_age, simulation_inputs.life_expectancy)):
        if simulation_inputs.distribution_type == "normal":
            return_dist = norm.rvs(loc=simulation_inputs.annual_return,
                                   scale=simulation_inputs.return_std,
                                   size=simulation_inputs.num_simulations,
                                   random_state=random.randint(0, 2**32 - 1))
        elif simulation_inputs.distribution_type == "laplace":
            return_dist = laplace.rvs(loc=simulation_inputs.annual_return,
                                  scale=simulation_inputs.return_std/math.sqrt(2),
                                  size=simulation_inputs.num_simulations,
                                  random_state=random.randint(0, 2**32 - 1))
        else:
            raise Exception("Error invalid distribution type")

        current_balances = np.multiply(current_balances + net_income_by_year[year], return_dist + 1)  # TODO note this order of applying spending in docs (same as Empower order)
        balance_history[year] = current_balances.tolist()
        return_history[year] = return_dist.tolist()

    return balance_history, return_history


@app.post("/")
def main(simulation_inputs: SimulationInputPayload):
    if simulation_inputs.num_simulations > 10000:
        raise HTTPException(status_code=400, detail="num_simulations cannot be greater than 10000")

    income_by_year, spending_by_year, net_income_by_year = get_cashflows(simulation_inputs)

    balance_history, return_history = run_simulations(simulation_inputs, net_income_by_year)

    simulation_summary = get_simulation_summary(balance_history[simulation_inputs.life_expectancy - 1], return_history[simulation_inputs.life_expectancy - 1], simulation_inputs)

    percentile_sets = get_balance_percentiles(simulation_inputs.percentiles, balance_history[simulation_inputs.life_expectancy-1])

    percentile_balance_history = get_percentile_balances(percentile_sets, balance_history)

    return {"simulation_summary": simulation_summary, "percentile_sets": percentile_sets, "balance_history": balance_history, "return_history": return_history, "percentile_balance_history": percentile_balance_history, "income_by_year": income_by_year, "spending_by_year": spending_by_year, "net_income_by_year": net_income_by_year}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, ssl_keyfile="/etc/letsencrypt/live/simulatesuccess.info/privkey.pem", ssl_certfile="/etc/letsencrypt/live/simulatesuccess.info/fullchain.pem")
