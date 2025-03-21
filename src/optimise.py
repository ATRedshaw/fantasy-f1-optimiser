from projections import generate_projections
from solves.normal import normal_solve
from solves.drs import drs_solve

def fetch_projections():
    """
    Fetch and return F1 team projections.

    This function generates projections for drivers and constructors
    by calling the `generate_projections` method, which scrapes data
    and processes it into a combined DataFrame format.

    Returns:
        pd.DataFrame: A DataFrame containing the projections with
        columns: name, is_driver, is_constructor, price, and xPts.
    """
    print("Fetching projections...")
    projections = generate_projections()
    return projections

def run_all_solves(projections, show_outputs=False, ask_save=False):
    """
    Runs all solve types and returns a list of results.

    Args:
        projections (pd.DataFrame): The projections DataFrame.

    Returns:
        list: A list of dictionaries containing the results of different solve types.
    """
    return [normal_solve(projections, show_prints=show_outputs, ask_to_save=ask_save), 
        normal_solve(projections, is_wildcard=True, show_prints=show_outputs, ask_to_save=ask_save), 
        normal_solve(projections, is_limitless=True, show_prints=show_outputs, ask_to_save=ask_save), 
        drs_solve(projections, show_prints=show_outputs, ask_to_save=ask_save)]

def compare_solves(solves = []):
    """
    Compare the results of different solve types.

    Args:
        solves (list): A list of dictionaries containing the results of different solve types.

    Returns:
        dict: A dictionary mapping solve types to their differences from normal solve
    """
    normal_xpts = solves[0]['base_xPts']
    differences = {}
    for solve in solves:
        differences[solve['solve_name']] = solve['base_xPts'] - normal_xpts
    return differences

def menu(differences):
    """
    Prints a menu for the user to select a solve type.

    The options are listed and the user is prompted to enter a number
    between 1 and 5. If the input is not valid, the user is asked again
    until a valid choice is entered.

    Args:
        differences (dict): Dictionary mapping solve types to their point differences

    Returns:
        str: The user's choice as a string, one of the following:
            "1", "2", "3", "4", "5"
    """
    print("Welcome to the Fantasy F1 Optimiser!")
    print("Please select a solve type:")
    print(f"1. Normal solve (+{differences['Normal']:.2f})")
    print(f"2. Wildcard solve (+{differences['Wildcard']:.2f})")
    print(f"3. Limitless solve (+{differences['Limitless']:.2f})")
    print(f"4. Extra DRS Boost solve (+{differences['DRS Boost']:.2f})")
    print("5. Exit")
    choice = input("Enter your choice (1-5): ")

    while choice not in ["1", "2", "3", "4", "5"]:
        print("Invalid choice. Please enter a number between 1 and 5.")
        choice = input("Enter your choice (1-5): ")

    solve_map = {
        "1": "Normal solve",
        "2": "Wildcard solve",
        "3": "Limitless solve",
        "4": "Extra DRS Boost solve",
        "5": "Exit"
    }
    
    print(f"You have selected: {solve_map[choice]}")
    return choice

def call_chosen_solve(projections, choice):
    """
    Calls the chosen solve function based on the user's choice.

    Args:
        projections (pd.DataFrame): The DataFrame containing the projections.
        choice (str): The user's choice as a string, one of the following:
            "1", "2", "3", "4", "5"
    """
    if choice == "1":
        normal_projections = normal_solve(projections)
    elif choice == "2":
        wildcard_projections = normal_solve(projections, is_wildcard=True)
    elif choice == "3":
        limitless_projections = normal_solve(projections, is_limitless=True)
    elif choice == "4":
        drs_projections = drs_solve(projections)  
    elif choice == "5":
        print("Exiting the program.")
        exit()
    else:
        print("Could not launch a solve for invalid solve type.")

    run_again = input("Would you like to run another solve? (y/n): ")
    if run_again == "y":
        return True
    else:
        return False


def main():
    projections = fetch_projections()
    # Get initial differences by running all solves silently
    differences = compare_solves(run_all_solves(projections, show_outputs=False, ask_save=False))
    run_again = True
    while run_again:
        choice = menu(differences)
        run_again = call_chosen_solve(projections, choice)

if __name__ == "__main__":
    main()
