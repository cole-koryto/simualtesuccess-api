import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

# returns the final balances that fall in the given percentiles
def get_balance_percentiles(percentiles, final_balances):
    percentile_sets = {}
    for percentile in percentiles:
        found_balance = np.percentile(final_balances, percentile)
        percentile_sets[percentile] = (found_balance, np.where(np.isclose(final_balances, found_balance)))

    return percentile_sets


# prints summary of simulations results
def simulation_summary(balance_history, return_history, input_data):
    # gives summary stats of balances and return in final year
    print(pd.DataFrame(balance_history[input_data["life_expectancy"]]).describe())
    print(pd.DataFrame(return_history[input_data["life_expectancy"]]).describe()) #40,000,000
    success_rate = np.count_nonzero(balance_history[input_data["life_expectancy"]] >= 0) / balance_history[input_data["life_expectancy"]].size
    print(f"Retirement success % = {success_rate * 100}%")


# visualizes balances given a year
def visualize_year_balance(balance_history, year):
    # plt.boxplot(balance_history[year])
    # plt.show()
    plt.hist(balance_history[year])
    plt.show()


# runs simulations to get balance and return histories
def run_simulations(input_data):
    balance_history = {}
    return_history = {}
    current_balances = np.full(input_data["num_simulations"], input_data["current_balance"])
    # print(current_balances)
    for year in range(input_data["current_age"], input_data["life_expectancy"] + 1):

        return_dist = norm.rvs(loc=input_data["annual_return"],
                               scale=input_data["return_std"],
                               size=input_data["num_simulations"],
                               random_state=input_data["random_state"])
        current_balances = np.multiply(current_balances - input_data["yearly_spending"], return_dist + 1)  # TODO note this order of applying spending in docs (same as Empower order)
        balance_history[year] = current_balances
        return_history[year] = return_dist
        # print(return_dist)
        # print(current_balances)

    return balance_history, return_history


# gets simulation inputs from json
def get_simulation_inputs():
    input_data = None
    with open("retirement_inputs.json", "r") as read_file:
        input_data = json.load(read_file)
    if not input_data:
        raise Exception("Error reading in retirement inputs.")
    return input_data


def main():
    input_data = get_simulation_inputs()

    balance_history, return_history = run_simulations(input_data)

    # visualize_year_balance(balance_history, life_expectancy)

    simulation_summary(balance_history, return_history, input_data)

    percentile_sets = get_balance_percentiles(input_data["percentiles"], balance_history[input_data["life_expectancy"]])
    print(percentile_sets)

if __name__ == "__main__":
    main()
