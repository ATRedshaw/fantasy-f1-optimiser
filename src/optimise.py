from projections import generate_projections
from solves.normal import normal_solve

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

def menu():
    """
    Prints a menu for the user to select a solve type.

    The options are listed and the user is prompted to enter a number
    between 1 and 4. If the input is not valid, the user is asked again
    until a valid choice is entered.

    Returns:
        str: The user's choice as a string, one of the following:
            "1", "2", "3", "4"
    """
    print("Welcome to the Fantasy F1 Optimiser!")
    print("Please select a solve type:")
    print("1. Normal solve")
    print("2. Wildcard solve")
    print("3. Limitless solve")
    print("4. Extra DRS Boost solve")
    choice = input("Enter your choice (1-4): ")

    while choice not in ["1", "2", "3", "4"]:
        print("Invalid choice. Please enter a number between 1 and 4.")
        choice = input("Enter your choice (1-4): ")

    solve_map = {
        "1": "Normal solve",
        "2": "Wildcard solve",
        "3": "Limitless solve",
        "4": "Extra DRS Boost solve",
    }
    
    print(f"You have selected: {solve_map[choice]}")
    return choice

def call_chosen_solve(projections, choice):
    """
    Calls the chosen solve function based on the user's choice.

    Args:
        projections (pd.DataFrame): The DataFrame containing the projections.
        choice (str): The user's choice as a string, one of the following:
            "1", "2", "3", "4", "5", "6", "7"
    """
    if choice == "1":
        normal_solve(projections)
    elif choice == "2":
        normal_solve(projections, is_wildcard=True)
    elif choice == "3":
        normal_solve(projections, is_limitless=True)
    elif choice == "4":
        # extra_drs_boost_solve(projections)
        pass
    else:
        print("Could not launch a solve for invalid solve type.")

if __name__ == "__main__":
    projections = fetch_projections()
    choice = menu()
    call_chosen_solve(projections, choice)
