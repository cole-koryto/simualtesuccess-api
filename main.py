from fastapi import FastAPI
import json
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random
from schemas import *
from scipy.stats import laplace
from scipy.stats import norm


app = FastAPI()


# visualizes balances of percentiles over simulation
def visualize_percentile_balances(percentile_sets, balance_history):
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
    plt.show()


# returns the final balances that fall in the given percentiles
def get_balance_percentiles(percentiles, final_balances):
    percentile_sets = {}
    for percentile in percentiles:
        found_balance = float(np.percentile(final_balances, percentile, method="closest_observation"))
        percentile_sets[percentile] = {"balance_amount": found_balance, "balance_index": int(np.where(np.isclose(final_balances, found_balance, rtol=0, atol=0.01))[0][0])}

    return percentile_sets


# prints summary of simulations results
def get_simulation_summary(balance_history, return_history, input_data):
    temp_balance_db = pd.Series(balance_history[input_data["life_expectancy"] - 1])
    temp_return_db = pd.Series(return_history[input_data["life_expectancy"] - 1])
    simulation_summary = {
        "balance_summary": {"min": temp_balance_db.min(), "max": temp_balance_db.max(), "mean": temp_balance_db.mean(), "std": temp_balance_db.std()},
        "return_summary": {"min": temp_return_db.min(), "max": temp_return_db.max(), "mean": temp_return_db.mean(), "std": temp_return_db.std()},
        "success_rate": np.count_nonzero(balance_history[input_data["life_expectancy"]-1] >= 0) / balance_history[input_data["life_expectancy"]-1].size}
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
    plt.hist(balance_history_adjusted)
    plt.xlabel("Balance")
    plt.ylabel("Frequency")
    plt.title("Final Year Balances")
    plt.ticklabel_format(style='plain', axis='x')
    plt.show()


# determines net income by year from income and expenses #TODO test growth and inflation
def get_net_income_by_year(input_data):
    net_income_by_year = {}
    for year_from_start, year in enumerate(range(input_data["current_age"], input_data["life_expectancy"])):
        new_net_income = 0

        # adds all incomes
        for income_dict in input_data["income_dict"].values():
            if income_dict["starting_age"] <= year < income_dict["ending_age"]:
                new_net_income += income_dict["amount"] * (1+income_dict["growth"])**(year-income_dict["starting_age"])

        # adds all expenses
        for expense_dict in input_data["spending_dict"].values():
            if expense_dict["starting_age"] <= year < expense_dict["ending_age"]:
                new_net_income -= expense_dict["amount"] * (1+expense_dict["growth"])**(year-expense_dict["starting_age"]) * (1+input_data["inflation"])**year_from_start

        net_income_by_year[year] = new_net_income

    return net_income_by_year


# runs simulations to get balance and return histories
def run_simulations(input_data, net_income_by_year):
    # generates all random states for return distributons
    random.seed(input_data["random_state"])
    random_states = [random.randint(0, 2**32 - 1) for _ in range(input_data["num_simulations"])]
    balance_history = {}
    return_history = {}
    current_balances = np.full(input_data["num_simulations"], input_data["current_balance"])
    for year_index, year in enumerate(range(input_data["current_age"], input_data["life_expectancy"])):
        if input_data["distribution_type"] == "normal":
            return_dist = norm.rvs(loc=input_data["annual_return"],
                                   scale=input_data["return_std"],
                                   size=input_data["num_simulations"],
                                   random_state=random_states[year_index])
        elif input_data["distribution_type"] == "laplace":
            return_dist = laplace.rvs(loc=input_data["annual_return"],
                                  scale=input_data["return_std"]/math.sqrt(2), #std = sqrt(var), var = 2b^2, std^2 = 2b^2, std = sqrt(2)*b, b = std/sqrt(2)
                                  size=input_data["num_simulations"],
                                  random_state=random_states[year_index]) #TODO check with Dr. Nordmoe to make sure this makes sense
        else:
            raise Exception("Error invalid distribution type")

        current_balances = np.multiply(current_balances + net_income_by_year[year], return_dist + 1)  # TODO note this order of applying spending in docs (same as Empower order)
        balance_history[year] = current_balances
        return_history[year] = return_dist

    return balance_history, return_history


# gets simulation inputs from json #TODO add error checking for inputs
def get_simulation_inputs():
    with open("retirement_inputs.json", "r") as read_file:
        input_data = json.load(read_file)
    if not input_data:
        raise Exception("Error reading in retirement inputs.")
   
    return input_data


@app.get("/main/")
def main():
    input_data = get_simulation_inputs()

    net_income_by_year = get_net_income_by_year(input_data)

    balance_history, return_history = run_simulations(input_data, net_income_by_year)

    # visualize_year_balance(balance_history, input_data["life_expectancy"]-1)

    simulation_summary = get_simulation_summary(balance_history, return_history, input_data)
    print(simulation_summary)

    percentile_sets = get_balance_percentiles(input_data["percentiles"], balance_history[input_data["life_expectancy"]-1])
    print(percentile_sets)

    visualize_percentile_balances(percentile_sets, balance_history)
    
    return {"simulation_summary": simulation_summary, "percentile_sets:": percentile_sets}
    

if __name__ == "__main__":
    main()
