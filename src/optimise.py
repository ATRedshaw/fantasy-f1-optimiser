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

def run_all_solves(projections):
    """
    Runs all solve types and returns a list of results.

    Args:
        projections (pd.DataFrame): The projections DataFrame.

    Returns:
        list: A list of dictionaries containing the results of different solve types.
    """
    return [normal_solve(projections), normal_solve(projections, is_wildcard=True), normal_solve(projections, is_limitless=True), drs_solve(projections)]

def compare_solves(solves = []):
    """
    Compare the results of different solve types.

    Args:
        solves (list): A list of dictionaries containing the results of different solve types.

    Returns:
        None
    """
    # For each solve type, print the expected points
    for solve in solves:
        print(f"{solve['solve_name']}: {solve['base_xPts']}")

def menu():
    """
    Prints a menu for the user to select a solve type.

    The options are listed and the user is prompted to enter a number
    between 1 and 6. If the input is not valid, the user is asked again
    until a valid choice is entered.

    Returns:
        str: The user's choice as a string, one of the following:
            "1", "2", "3", "4", "5", "6"
    """
    print("Welcome to the Fantasy F1 Optimiser!")
    print("Please select a solve type:")
    print("1. Normal solve")
    print("2. Wildcard solve")
    print("3. Limitless solve")
    print("4. Extra DRS Boost solve")
    print("5. Run all solves")
    print("6. Exit")
    choice = input("Enter your choice (1-6): ")

    while choice not in ["1", "2", "3", "4", "5", "6"]:
        print("Invalid choice. Please enter a number between 1 and 6.")
        choice = input("Enter your choice (1-6): ")

    solve_map = {
        "1": "Normal solve",
        "2": "Wildcard solve",
        "3": "Limitless solve",
        "4": "Extra DRS Boost solve",
        "5": "Run all solves",
        "6": "Exit"
    }
    
    print(f"You have selected: {solve_map[choice]}")
    return choice

def call_chosen_solve(projections, choice):
    """
    Calls the chosen solve function based on the user's choice.

    Args:
        projections (pd.DataFrame): The DataFrame containing the projections.
        choice (str): The user's choice as a string, one of the following:
            "1", "2", "3", "4", "5", "6"
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
        all_solve_results = run_all_solves(projections)
        compare_solves(all_solve_results)
    elif choice == "6":
        print("Exiting the program.")
        exit()
    else:
        print("Could not launch a solve for invalid solve type.")

def main():
    projections = fetch_projections()
    choice = menu()
    call_chosen_solve(projections, choice)

if __name__ == "__main__":
    main()
