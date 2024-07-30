# Simulate Success Backend API

## Purpose
The purpose of this project is to create an API backend that runs Monte Carlo simulations of a provided retirement portfolio and provide numerical insights into how the portfolio would perform given its characteristics.

## Inputs

See front [frontend documentation for variable descriptions](https://github.com/cole-koryto/simulatesuccess-frontend/tree/main).

For raw inputs, see [schemas/input_schemas.py](https://github.com/cole-koryto/simualtesuccess-api/blob/main/schemas/input_schemas.py).


## Outputs

simulation_summary: json with minimum, maximum, and standard deviation of both the balances and the returns. Also contains the success_rate which is the proportion of balances in the final year that are >= 0.

percentile_sets: json containing the balances and their index in the final year of balance_history with the the given percentiles.

balance_history: json with the balances at each age in each simulation.

return_history: json with the returns at each age in each simulation.

percentile_balance_history: json with the balances at each age for each of the provided percentiles.

income_by_year: json with the total income at each age.

spending_by_year: json with the total spending at each age.

net_income_by_year: json with the net income at each age.

## Usage

Send POST request to https://simulatesuccess.info/ with a request following the SimulationInputPayload schema.

## Setup

Simply run the main.py file to host locally.

## Notes
* num_simulations must <= 10,000.
* At the start of each age, net income is applied to the current balance at that age before the return is applied.
