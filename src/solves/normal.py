import pulp as lp
import pandas as pd
import json
import os
import yaml

def normal_solve(projections):
    """
    Perform a normal solve for the Fantasy F1 team selection with weighted price change.
    
    This function sets up and solves a linear programming problem to select an optimal team
    of 5 drivers and 2 constructors. In the optimization objective the expected points (xPts)
    are augmented by a bonus derived from each player’s projected price change weighted by
    a factor defined in the config file (config/solver_config.yml, variable 'price_change_weight').
    
    When printing the results, the reported total expected points (xPts) exclude the price
    change bonus (i.e. they only reflect the base xPts value).
    
    Args:
        projections (pd.DataFrame): DataFrame containing projections with columns:
            'name', 'is_driver', 'is_constructor', 'price', 'xPts', 'price_change'.
    
    Returns:
        None: The function prints out the team details, transfers, and optionally saves the team
        to 'data/team.json' with the remaining budget.
    """
    # Load the solver configuration from config/solver_config.yml
    config_file = os.path.join("config", "solver_config.yml")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        price_change_weight = config.get('price_change_weight', 0)
    else:
        print("Config file not found. Defaulting price_change_weight to 0.")
        price_change_weight = 0

    # Load previous team from 'data/team.json' if it exists
    if os.path.exists('data/team.json'):
        with open('data/team.json', 'r') as f:
            try:
                data = json.load(f)
                previous_drivers = data['drivers']
                previous_constructors = data['constructors']
                available_transfers = data['available_transfers']
                remaining_budget = data['remaining_budget']
            except json.JSONDecodeError:
                print("Invalid JSON data in 'data/team.json'. Using default values.")
                previous_drivers = []
                previous_constructors = []
                available_transfers = 1000
                remaining_budget = 100.0

        # Separate drivers and constructors from projections
        drivers = projections[projections['is_driver'] == True].set_index('name')
        constructors = projections[projections['is_constructor'] == True].set_index('name')

        # Calculate current team value based on current prices
        previous_drivers_prices = [drivers.loc[d, 'price'] for d in previous_drivers if d in drivers.index]
        previous_constructors_prices = [constructors.loc[c, 'price'] for c in previous_constructors if c in constructors.index]
        current_team_value = sum(previous_drivers_prices) + sum(previous_constructors_prices)

        # Set cost cap as current team value plus remaining budget
        cost_cap = current_team_value + remaining_budget
    else:
        previous_drivers = []
        previous_constructors = []
        available_transfers = 1000  # Unlimited transfers for the first race
        cost_cap = 100.0  # Default budget if no saved team

    # In case drivers/constructors were not defined above
    if 'drivers' not in locals():
        drivers = projections[projections['is_driver'] == True].set_index('name')
        constructors = projections[projections['is_constructor'] == True].set_index('name')

    # Initialize the PuLP problem
    prob = lp.LpProblem("Fantasy_F1_Normal_Solve", lp.LpMaximize)

    # Define decision variables
    x = lp.LpVariable.dicts("driver", drivers.index, 0, 1, lp.LpBinary)           # Driver selection
    y = lp.LpVariable.dicts("constructor", constructors.index, 0, 1, lp.LpBinary)  # Constructor selection
    b = lp.LpVariable.dicts("boost", drivers.index, 0, 1, lp.LpBinary)             # DRS boost assignment
    penalty_transfers = lp.LpVariable("penalty_transfers", 0, None, lp.LpContinuous) # Excess transfers

    # Constraints
    prob += lp.lpSum([x[d] for d in drivers.index]) == 5, "Exactly_5_Drivers"
    prob += lp.lpSum([y[c] for c in constructors.index]) == 2, "Exactly_2_Constructors"
    prob += (
        lp.lpSum([drivers.loc[d, 'price'] * x[d] for d in drivers.index]) +
        lp.lpSum([constructors.loc[c, 'price'] * y[c] for c in constructors.index])
    ) <= cost_cap, "Cost_Cap"
    prob += lp.lpSum([b[d] for d in drivers.index]) == 1, "One_DRS_Boost"
    for d in drivers.index:
        prob += b[d] <= x[d], f"Boost_Only_If_Selected_{d}"

    # Transfer calculation and penalty constraint
    total_transfers = (
        lp.lpSum([x[d] for d in drivers.index if d not in previous_drivers]) +
        lp.lpSum([y[c] for c in constructors.index if c not in previous_constructors])
    )
    prob += penalty_transfers >= total_transfers - available_transfers, "Penalty_Transfers"

    # Build the objective function
    # Base expected points (without price change bonus)
    base_points = (
        lp.lpSum([constructors.loc[c, 'xPts'] * y[c] for c in constructors.index]) +
        lp.lpSum([drivers.loc[d, 'xPts'] * x[d] for d in drivers.index]) +
        lp.lpSum([drivers.loc[d, 'xPts'] * b[d] for d in drivers.index])
    )
    # Weighted price change bonus term
    price_change_term = (
        lp.lpSum([constructors.loc[c, 'price_change'] * y[c] for c in constructors.index]) +
        lp.lpSum([drivers.loc[d, 'price_change'] * x[d] for d in drivers.index])
    )
    # Combine the two, subtracting the penalty for excess transfers
    objective = base_points + price_change_weight * price_change_term - 10 * penalty_transfers
    prob += objective, "Total_Expected_Points_With_PriceChange"

    # Solve the problem with suppressed solver output
    status = prob.solve(lp.PULP_CBC_CMD(msg=False))
    if status != lp.LpStatusOptimal:
        print("No optimal solution found. Please check the constraints or input data.")
        return

    # Extract results
    selected_drivers = [d for d in drivers.index if lp.value(x[d]) == 1]
    selected_constructors = [c for c in constructors.index if lp.value(y[c]) == 1]
    boosted_driver = [d for d in drivers.index if lp.value(b[d]) == 1][0]
    transfers_used = (
        sum(1 for d in selected_drivers if d not in previous_drivers) +
        sum(1 for c in selected_constructors if c not in previous_constructors)
    )
    penalty = lp.value(penalty_transfers)
    
    # Calculate base expected points (without the price change bonus)
    base_xPts = (
        sum(constructors.loc[c, 'xPts'] for c in selected_constructors) +
        sum(drivers.loc[d, 'xPts'] for d in selected_drivers) +
        drivers.loc[boosted_driver, 'xPts'] -
        10 * penalty
    )
    
    # Calculate cost details
    selected_drivers_prices = [drivers.loc[d, 'price'] for d in selected_drivers]
    selected_constructors_prices = [constructors.loc[c, 'price'] for c in selected_constructors]
    total_selected_cost = sum(selected_drivers_prices) + sum(selected_constructors_prices)
    new_remaining_budget = cost_cap - total_selected_cost

    # Determine transfers to make
    drivers_to_add = [d for d in selected_drivers if d not in previous_drivers]
    drivers_to_remove = [d for d in previous_drivers if d not in selected_drivers]
    constructors_to_add = [c for c in selected_constructors if c not in previous_constructors]
    constructors_to_remove = [c for c in previous_constructors if c not in selected_constructors]

    transfers = []
    for i in range(min(len(drivers_to_remove), len(drivers_to_add))):
        transfers.append(f"{drivers_to_remove[i]} > {drivers_to_add[i]}")
    for i in range(min(len(constructors_to_remove), len(constructors_to_add))):
        transfers.append(f"{constructors_to_remove[i]} > {constructors_to_add[i]}")

    # Display transfers
    print("\nTransfers to Make:")
    print("---------------------")
    if transfers:
        for transfer in transfers:
            print(transfer)
    else:
        print("No transfers needed. The optimal team is the same as the previous team.")

    # Display optimal team details
    print("\nOptimal Team Selection:")
    print("---------------------")
    print("Selected Drivers:", ", ".join(selected_drivers))
    print("Selected Constructors:", ", ".join(selected_constructors))
    print("DRS Boost Driver:", boosted_driver)
    # Print the base expected points (without price change weighting)
    print(f"Total Expected Points (Base): {base_xPts:.2f}")
    print(f"Transfers Used: {transfers_used}")
    print(f"Penalty Transfers: {penalty}")
    print(f"Available Transfers: {available_transfers}")
    print(f"Cost Cap: {cost_cap:.2f}")
    print(f"Total Team Cost: {total_selected_cost:.2f}")
    print(f"Remaining Budget: {new_remaining_budget:.2f}")

    # Prompt to save the team
    save = input("\nDo you want to save this team? (y/n): ").lower().strip()
    if save == 'y':
        if not previous_drivers and not previous_constructors:  # First race
            next_available_transfers = 2
        else:
            next_available_transfers = 3 if transfers_used < available_transfers else 2

        team_data = {
            "drivers": selected_drivers,
            "constructors": selected_constructors,
            "available_transfers": next_available_transfers,
            "remaining_budget": new_remaining_budget
        }
        # Ensure the 'data' directory exists
        os.makedirs("data", exist_ok=True)
        with open('data/team.json', 'w') as f:
            json.dump(team_data, f, indent=4)
        print("Team saved successfully to 'data/team.json'.")
    else:
        print("Team not saved.")
