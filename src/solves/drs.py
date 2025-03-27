import pulp as lp
import json
import os
import yaml
import pandas as pd

def drs_solve(projections, show_prints=True, ask_to_save=True):
    """
    Perform a DRS solve for the Fantasy F1 team selection with weighted price change.
    
    This function sets up and solves a linear programming problem to select an optimal team
    of 5 drivers and 2 constructors, with both a 2x and 3x DRS boost. In the optimization 
    objective the expected points (xPts) are augmented by a bonus derived from each player's 
    projected price change weighted by a factor defined in the config file 
    (config/solver_config.yml, variable 'price_change_weight').
    
    When printing the results, the reported total expected points (xPts) exclude the price
    change bonus (i.e. they only reflect the base xPts value).
    
    Args:
        projections (pd.DataFrame): DataFrame containing projections with columns:
            'name', 'is_driver', 'is_constructor', 'price', 'xPts', 'price_change'.
        show_prints (bool): Whether to print output messages
        ask_to_save (bool): Whether to prompt to save the team
    
    Returns:
        dict: A dictionary containing the selected drivers, constructors, and other relevant details
              such as the total expected points and the type of solve performed.
    """
    def print_if_enabled(*args, **kwargs):
        if show_prints:
            print(*args, **kwargs)

    # Load the solver configuration from config/solver_config.yml
    config_file = os.path.join("config", "solver_config.yml")
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        price_change_weight = config.get('price_change_weight', 0)
        roll_transfer_weight = config.get('roll_transfer_weight', 0)
    else:
        print_if_enabled("Config file not found. Defaulting price_change_weight to 0.")
        price_change_weight = 0
        roll_transfer_weight = 0

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
                print_if_enabled("Invalid JSON data in 'data/team.json'. Using default values.")
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
    prob = lp.LpProblem("Fantasy_F1_DRS_Solve", lp.LpMaximize)

    # Define decision variables
    x = lp.LpVariable.dicts("driver", drivers.index, 0, 1, lp.LpBinary)           # Driver selection
    y = lp.LpVariable.dicts("constructor", constructors.index, 0, 1, lp.LpBinary)  # Constructor selection
    b2 = lp.LpVariable.dicts("boost2x", drivers.index, 0, 1, lp.LpBinary)         # 2x DRS boost assignment
    b3 = lp.LpVariable.dicts("boost3x", drivers.index, 0, 1, lp.LpBinary)         # 3x DRS boost assignment
    penalty_transfers = lp.LpVariable("penalty_transfers", 0, None, lp.LpContinuous) # Excess transfers
    roll_transfer = lp.LpVariable("roll_transfer", 0, 1, lp.LpBinary)  # Binary variable for rolling a transfer

    # Constraints
    prob += lp.lpSum([x[d] for d in drivers.index]) == 5, "Exactly_5_Drivers"
    prob += lp.lpSum([y[c] for c in constructors.index]) == 2, "Exactly_2_Constructors"
    prob += (
        lp.lpSum([drivers.loc[d, 'price'] * x[d] for d in drivers.index]) +
        lp.lpSum([constructors.loc[c, 'price'] * y[c] for c in constructors.index])
    ) <= cost_cap, "Cost_Cap"
    prob += lp.lpSum([b2[d] for d in drivers.index]) == 1, "One_2x_DRS_Boost"
    prob += lp.lpSum([b3[d] for d in drivers.index]) == 1, "One_3x_DRS_Boost"
    for d in drivers.index:
        prob += b2[d] <= x[d], f"2x_Boost_Only_If_Selected_{d}"
        prob += b3[d] <= x[d], f"3x_Boost_Only_If_Selected_{d}"
        prob += b2[d] + b3[d] <= 1, f"Not_Both_Boosts_{d}"  # Can't have both boosts on same driver

    # Transfer calculation and penalty constraint
    total_transfers = (
        lp.lpSum([x[d] for d in drivers.index if d not in previous_drivers]) +
        lp.lpSum([y[c] for c in constructors.index if c not in previous_constructors])
    )
    prob += penalty_transfers >= total_transfers - available_transfers, "Penalty_Transfers"
    
    # Roll transfer constraint - roll_transfer is 1 if transfers used < available
    if available_transfers > 1:  # Only consider rolling if we have transfers to roll
        prob += roll_transfer <= 1 - (total_transfers / available_transfers), "Roll_Transfer_Condition"

    # Build the objective function
    # Base expected points (without price change bonus)
    base_points = (
        lp.lpSum([constructors.loc[c, 'xPts'] * y[c] for c in constructors.index]) +
        lp.lpSum([drivers.loc[d, 'xPts'] * x[d] for d in drivers.index]) +
        lp.lpSum([drivers.loc[d, 'xPts'] * b2[d] for d in drivers.index]) +
        2 * lp.lpSum([drivers.loc[d, 'xPts'] * b3[d] for d in drivers.index])
    )
    # Weighted price change bonus term
    price_change_term = (
        lp.lpSum([constructors.loc[c, 'price_change'] * y[c] for c in constructors.index]) +
        lp.lpSum([drivers.loc[d, 'price_change'] * x[d] for d in drivers.index])
    )
    # Combine the two, subtracting the penalty for excess transfers and adding bonus for rolling transfers
    objective = base_points + price_change_weight * price_change_term - 10 * penalty_transfers + roll_transfer_weight * roll_transfer
    prob += objective, "Total_Expected_Points_With_PriceChange_And_RollTransfer"

    # Solve the problem with suppressed solver output
    status = prob.solve(lp.PULP_CBC_CMD(msg=False))
    if status != lp.LpStatusOptimal:
        print_if_enabled("No optimal solution found. Please check the constraints or input data.")
        return

    # Extract results
    selected_drivers = [d for d in drivers.index if lp.value(x[d]) == 1]
    selected_constructors = [c for c in constructors.index if lp.value(y[c]) == 1]
    boosted_driver_2x = [d for d in drivers.index if lp.value(b2[d]) == 1][0]
    boosted_driver_3x = [d for d in drivers.index if lp.value(b3[d]) == 1][0]
    transfers_used = (
        sum(1 for d in selected_drivers if d not in previous_drivers) +
        sum(1 for c in selected_constructors if c not in previous_constructors)
    )
    penalty = lp.value(penalty_transfers)
    
    # Calculate base expected points (without the price change bonus)
    base_xPts = (
        sum(constructors.loc[c, 'xPts'] for c in selected_constructors) +
        sum(drivers.loc[d, 'xPts'] for d in selected_drivers) +
        drivers.loc[boosted_driver_2x, 'xPts'] +
        2 * drivers.loc[boosted_driver_3x, 'xPts'] -
        10 * penalty
    )
    
    # Calculate cost details
    selected_drivers_prices = [drivers.loc[d, 'price'] for d in selected_drivers]
    selected_constructors_prices = [constructors.loc[c, 'price'] for c in selected_constructors]
    total_selected_cost = sum(selected_drivers_prices) + sum(selected_constructors_prices)
    new_remaining_budget = cost_cap - total_selected_cost
    
    # Calculate projected team price change
    projected_price_change = (
        sum(drivers.loc[d, 'price_change'] for d in selected_drivers) +
        sum(constructors.loc[c, 'price_change'] for c in selected_constructors)
    )

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
    print_if_enabled("\nTransfers to Make:")
    print_if_enabled("---------------------")
    if transfers:
        for transfer in transfers:
            print_if_enabled(transfer)
    else:
        print_if_enabled("No transfers needed. The optimal team is the same as the previous team.")

    # Display optimal team details
    print_if_enabled("\nOptimal Team Selection:")
    print_if_enabled("---------------------")
    print_if_enabled("Selected Drivers:", ", ".join(selected_drivers))
    print_if_enabled("Selected Constructors:", ", ".join(selected_constructors))
    print_if_enabled("2x DRS Boost Driver:", boosted_driver_2x)
    print_if_enabled("3x DRS Boost Driver:", boosted_driver_3x)
    print_if_enabled(f"Total Expected Points (Base): {base_xPts:.2f}")
    print_if_enabled(f"Projected Team Price Change: {projected_price_change:.2f}")
    print_if_enabled(f"Transfers Used: {transfers_used}")
    print_if_enabled(f"Penalty Transfers: {penalty}")
    print_if_enabled(f"Available Transfers: {available_transfers}")
    print_if_enabled(f"Cost Cap: {cost_cap:.2f}")
    print_if_enabled(f"Total Team Cost: {total_selected_cost:.2f}")
    print_if_enabled(f"Remaining Budget: {new_remaining_budget:.2f}")

    # Only prompt to save if ask_to_save is True
    if ask_to_save:
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
                "remaining_budget": round(new_remaining_budget, 1)
            }

            # Ensure the 'data' directory exists
            os.makedirs("data", exist_ok=True)
            with open('data/team.json', 'w') as f:
                json.dump(team_data, f, indent=4)
            print_if_enabled("Team saved successfully to 'data/team.json'.")
        else:
            print_if_enabled("Team not saved.")

    return_dic = {
        "solve_name": "DRS Boost",
        "selected_drivers": selected_drivers,
        "selected_constructors": selected_constructors,
        "boosted_driver_2x": boosted_driver_2x,
        "boosted_driver_3x": boosted_driver_3x,
        "transfers": transfers,
        "base_xPts": base_xPts,
        "projected_price_change": projected_price_change
    }

    return return_dic