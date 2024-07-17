from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import json
import math
# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
from schemas.input_schemas import SimulationInputPayload, Source
from schemas.output_schemas import SimulationOutputPayload, SimulationSummary, SummaryStatistics
from scipy.stats import laplace
from scipy.stats import norm
import uvicorn


# configure FastAPI 
app = FastAPI()
#app.add_middleware(HTTPSRedirectMiddleware)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# visualizes balances of percentiles over simulation
"""def visualize_percentile_balances(percentile_sets, balance_history):
    percentile_balance_history = {}
    for percentile in percentile_sets:
        percentile_balance_history[percentile] = {}
        for year in balance_history:
            percentile_balance_history[percentile][year] = balance_history[year][percentile_sets[percentile]["balance_index"]]

        plt.plot(list(percentile_balance_history[percentile].keys()), list(percentile_balance_history[percentile].values()), label=f"{percentile}%")

    plt.legend(loc='best')
    plt.xlabel("Age")
    plt.ylabel("Balance")
    plt.title("Percentile Balances")
    plt.ticklabel_format(style='plain', axis='y')
    plt.axhline(0, color='black', linewidth=0.5)
    plt.show()"""
    
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
def get_simulation_summary(balance_history, return_history, simulation_inputs):
    temp_balance_db = pd.Series(balance_history[simulation_inputs.life_expectancy - 1])
    temp_return_db = pd.Series(return_history[simulation_inputs.life_expectancy - 1])

    simulation_summary = {
        "balance_summary": {"min": temp_balance_db.min(), "max": temp_balance_db.max(), "mean": temp_balance_db.mean(), "std": temp_balance_db.std()},
        "return_summary": {"min": temp_return_db.min(), "max": temp_return_db.max(), "mean": temp_return_db.mean(), "std": temp_return_db.std()},
        "success_rate": sum(balance >= 0 for balance in balance_history[simulation_inputs.life_expectancy-1]) / len(balance_history[simulation_inputs.life_expectancy-1])}
    return simulation_summary


# visualizes balances given a year #TODO make better figures
def visualize_year_balance(balance_history, year):
    balance_history_adjusted = pd.Series(balance_history[year])
    balance_history_adjusted = balance_history_adjusted[balance_history_adjusted.between(balance_history_adjusted.quantile(.05), balance_history_adjusted.quantile(.95))]

    # plt.boxplot(balance_history_adjusted)
    # plt.ylabel("Balance")
    # plt.title("Final Year Balances")
    # plt.ticklabel_format(style='plain', axis='y')
    # plt.show()
    # plt.hist(balance_history_adjusted)
    # plt.xlabel("Balance")
    # plt.ylabel("Frequency")
    # plt.title("Final Year Balances")
    # plt.ticklabel_format(style='plain', axis='x')
    # plt.show()


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
    # generates all random states for return distributons
    random.seed(simulation_inputs.random_state)
    random_states = [random.randint(0, 2**32 - 1) for _ in range(simulation_inputs.num_simulations)]
    balance_history = {}
    return_history = {}
    current_balances = np.full(simulation_inputs.num_simulations, simulation_inputs.current_balance)
    for year_index, year in enumerate(range(simulation_inputs.current_age, simulation_inputs.life_expectancy)):
        if simulation_inputs.distribution_type == "normal":
            return_dist = norm.rvs(loc=simulation_inputs.annual_return,
                                   scale=simulation_inputs.return_std,
                                   size=simulation_inputs.num_simulations,
                                   random_state=random_states[year_index])
        elif simulation_inputs.distribution_type == "laplace":
            return_dist = laplace.rvs(loc=simulation_inputs.annual_return,
                                  scale=simulation_inputs.return_std/math.sqrt(2), #std = sqrt(var), var = 2b^2, std^2 = 2b^2, std = sqrt(2)*b, b = std/sqrt(2)
                                  size=simulation_inputs.num_simulations,
                                  random_state=random_states[year_index]) #TODO check with Dr. Nordmoe to make sure this makes sense
        else:
            raise Exception("Error invalid distribution type")

        current_balances = np.multiply(current_balances + net_income_by_year[year], return_dist + 1)  # TODO note this order of applying spending in docs (same as Empower order)
        balance_history[year] = current_balances.tolist()
        return_history[year] = return_dist.tolist()

    return balance_history, return_history


# gets simulation inputs from json
def get_simulation_inputs():
    with open("retirement_inputs.json", "r") as read_file:
        input_data = json.load(read_file)
    if not input_data:
        raise Exception("Error reading in retirement inputs.")
    
    #income_sources = []
    #for income_source in input_data["income_dict"]:
        #income_sources.append(Source())
   
    return input_data    


@app.post("/main/")
def main(simulation_inputs: SimulationInputPayload):
    print(f"Random state: {simulation_inputs.random_state}")
    input_data = get_simulation_inputs()

    income_by_year, spending_by_year, net_income_by_year = get_cashflows(simulation_inputs)

    balance_history, return_history = run_simulations(simulation_inputs, net_income_by_year)

    # visualize_year_balance(balance_history, simulation_inputs.life_expectancy-1)

    simulation_summary = get_simulation_summary(balance_history, return_history, simulation_inputs)
    print(simulation_summary)

    percentile_sets = get_balance_percentiles(simulation_inputs.percentiles, balance_history[simulation_inputs.life_expectancy-1])
    print(percentile_sets)

    # visualize_percentile_balances(percentile_sets, balance_history)
    percentile_balance_history = get_percentile_balances(percentile_sets, balance_history)

    return {"simulation_summary": simulation_summary, "percentile_sets:": percentile_sets, "balance_history": balance_history, "return_history": return_history, "percentile_balance_history": percentile_balance_history, "income_by_year": income_by_year, "spending_by_year": spending_by_year, "net_income_by_year": net_income_by_year}


if __name__ == "__main__":
    uvicorn.run(app)
