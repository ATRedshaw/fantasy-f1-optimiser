# Fantasy F1 Optimiser Requirements

## Overview
This document outlines the requirements for a Fantasy F1 Optimiser application designed to help users select the optimal team of drivers and constructors in Fantasy F1. The optimiser accounts for budget constraints, transfer limits, and special chips that modify team selection or scoring, maximizing expected points (xPts) for a single race.

## Data Structure
The optimiser uses data retrieved in the following format:

| Field           | Description                              |
|-----------------|------------------------------------------|
| `name`          | Name of the driver or constructor        |
| `is_driver`     | Boolean indicating if the entity is a driver |
| `is_constructor`| Boolean indicating if the entity is a constructor |
| `price`         | Cost to include the entity in the team   |
| `xPts`          | Expected points for the upcoming race    |

- The data includes both drivers and constructors, identified by `is_driver` and `is_constructor`.
- Prices are updated after each race based on performance, but the optimiser uses the current data for a given race.

## Team Storage
- **Storage Format**: The current team is stored in a JSON file.
- **Contents**: The JSON file contains:
  - The list of selected drivers and constructors (by name).
  - The number of available transfers for the next race (`available_transfers`).
- **First Race**: If the JSON file does not exist, assume no team has been selected (first race), with unlimited transfers.
- **Post-Optimisation**: After optimisation, the user is prompted to save the new team to the JSON file. If saved, the file is updated with the new team and the calculated available transfers for the next race.
- **Scope**: The optimiser manages one team at a time, though users can manage up to three teams in Fantasy F1. Multiple teams require separate JSON files or an extension to store multiple teams.

## Optimisation Tool
- The optimiser uses **PuLP**, a Python library for linear programming, to formulate and solve the team selection problem.

## User Interaction
- **Solve Type Selection**: Before optimisation, the user is asked to choose:
  - A normal solve.
  - A solve using one of the chips: Wildcard, Limitless, Extra DRS Boost, Autopilot, No Negative, or Final Fix.
- **Inputs**:
  - **Cost Cap**: User inputs the cost cap (unless using Limitless).
  - **Solve Choice**: User selects the solve type from the available options.
- **Chip Rules**:
  - Only one chip can be used per race.
  - Each chip can be used once per season.
  - Wildcard, Limitless, and Final Fix are available after the first race; others are available immediately.

## Team Composition
- **Standard Team**:
  - Exactly **5 drivers**.
  - Exactly **2 constructors**.
- **DRS Boost**:
  - One driver receives a 2x multiplier on their xPts (normal case).
  - Does not affect constructor points.

## Transfer Rules
- **First Race**: Unlimited transfers, staying within the cost cap.
- **Subsequent Races**:
  - Base allowance: **2 transfers** per race.
  - **Carry-Over**: If fewer than the available transfers are used, 1 unused transfer carries over, up to a maximum of **3 transfers** for the next race.
  - **Definition**: A transfer is replacing one driver or constructor.
  - **Penalty**: Each transfer beyond the available limit incurs a **-10 point penalty**.
- **Storage**: The JSON file tracks `available_transfers` for the next race, updated after each optimisation if saved.

## Chips
Chips modify the optimisation or scoring process:

- **Wildcard**:
  - Unlimited transfers.
  - Must stay within the cost cap.
  - Available after the first race.
- **Limitless**:
  - Unlimited transfers and no cost cap.
  - Team reverts to the original team after the race.
  - Available after the first race.
- **Extra DRS Boost**:
  - One driver receives a 3x multiplier instead of 2x.
  - User selects the driver during optimisation.
- **Autopilot**:
  - DRS Boost is automatically applied to the highest-scoring driver post-race.
  - Optimisation assumes the boost goes to the driver with the highest xPts in the selected team.
- **No Negative**:
  - Negative scores per scoring category are set to zero post-race.
  - Optimisation uses standard xPts (effect applied post-race).
- **Final Fix**:
  - Allows one penalty-free change between Qualifying and the Grand Prix.
  - Optimisation is for initial selection; effect is post-optimisation.

## Optimisation Scenarios
The optimiser adjusts constraints and objectives based on the selected solve type:

### Normal Solve
- **Constraints**:
  - 5 drivers, 2 constructors.
  - Total cost ≤ cost cap.
  - Transfers ≤ available transfers.
- **Objective**: Maximize:
  - Sum of xPts for constructors + Sum of xPts for drivers + Additional xPts for one driver with a 2x multiplier (boost = 2).
  - Minus 10 points per excess transfer.

### Wildcard Solve
- Same as normal, but unlimited transfers (no transfer penalty).

### Limitless Solve
- No cost cap, unlimited transfers.
- Objective same as normal solve.
- Note: Team reverts post-race; saving is optional.

### Extra DRS Boost Solve
- Same constraints as normal solve.
- Objective uses boost = 3 for one driver.
- Still another driver uses the regular boost = 2.

### Autopilot Solve
- Same constraints as normal solve.
- Objective maximizes xPts with the boost (2x) applied to the driver with the highest xPts in the team.

### No Negative and Final Fix Solves
- Identical to normal solve for optimisation.
- Effects (zeroing negatives, post-Qualifying change) are applied post-race.

## Optimisation Formulation
Using PuLP, the problem is defined as follows:

### Decision Variables
- \( x_d \): Binary, 1 if driver \( d \) is selected, 0 otherwise.
- \( y_c \): Binary, 1 if constructor \( c \) is selected, 0 otherwise.
- \( b_d \): Binary, 1 if driver \( d \) gets the DRS Boost, 0 otherwise (not used for Autopilot).
- \( m \): Continuous, maximum xPts among selected drivers (Autopilot only).
- \( \text{penalty_transfers} \): Continuous, number of transfers exceeding the limit.

### Constraints
- \( \sum_{d \in D} x_d = 5 \)
- \( \sum_{c \in C} y_c = 2 \)
- \( \sum_{d \in D} \text{price}_d \cdot x_d + \sum_{c \in C} \text{price}_c \cdot y_c \leq \text{cost_cap} \) (unless Limitless)
- **Normal, Extra DRS Boost, etc.**:
  - \( \sum_{d \in D} b_d = 1 \)
  - \( b_d \leq x_d \) for each \( d \)
- **Autopilot**:
  - \( m \leq \text{xPts}_d + M \cdot (1 - x_d) \) for each \( d \), where \( M \) is a large number (e.g., 1000).
- **Transfers**:
  - \( \text{total_transfers} = \sum_{d \notin \text{previous_drivers}} x_d + \sum_{c \notin \text{previous_constructors}} y_c \)
  - \( \text{penalty_transfers} \geq \text{total_transfers} - \text{available_transfers} \)
  - \( \text{penalty_transfers} \geq 0 \)

### Objective
- **Normal, Wildcard, Limitless, Extra DRS Boost, No Negative, Final Fix**:
  - Maximize:
    \[
    \sum_{c \in C} y_c \cdot \text{xPts}_c + \sum_{d \in D} x_d \cdot \text{xPts}_d + (\text{boost} - 1) \cdot \sum_{d \in D} b_d \cdot \text{xPts}_d - 10 \cdot \text{penalty_transfers}
    \]
  - Boost = 2 (normal), 3 (Extra DRS Boost).
- **Autopilot**:
  - Maximize:
    \[
    \sum_{c \in C} y_c \cdot \text{xPts}_c + \sum_{d \in D} x_d \cdot \text{xPts}_d + m - 10 \cdot \text{penalty_transfers}
    \]

## Program Flow
1. **Load Data**: Read the list of drivers and constructors with their attributes.
2. **Check JSON**:
   - If no JSON file, assume first race: `previous_team = []`, `available_transfers = 1000`.
   - If exists, load `previous_team` and `available_transfers`.
3. **User Inputs**:
   - Prompt for cost cap (unless Limitless).
   - Ask for solve type.
4. **Set Parameters**:
   - **Normal/No Negative/Final Fix**: Boost = 2, use loaded `available_transfers` and cost cap.
   - **Wildcard**: Boost = 2, `available_transfers = 1000`, use cost cap.
   - **Limitless**: Boost = 2, `available_transfers = 1000`, `cost_cap = 1000000`.
   - **Extra DRS Boost**: Boost = 3, use loaded values.
   - **Autopilot**: Use max formulation, loaded values.
5. **Solve**:
   - Formulate PuLP problem per the scenario.
   - Solve to get the optimal team.
6. **Output**:
   - Display selected drivers, constructors, DRS Boost recipient (if applicable), and expected points.
7. **Save Option**:
   - Ask user to save the team.
   - If yes:
     - Compute `transfers_used = total_transfers`.
     - If first race: `next_available_transfers = 2`.
     - Else: `next_available_transfers = 3` if `transfers_used < available_transfers`, else 2.
     - Save team and `next_available_transfers` to JSON.
   - For Limitless, inform user the team reverts post-race.

## Additional Notes
- **Price Changes**: Handled by updating the input data post-race.
- **Inactive Drivers**: Not directly addressed in optimisation; Final Fix or manual updates apply.
- **Multiple Teams**: Extendable by managing separate JSON files or a multi-team JSON structure.