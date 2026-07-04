from typing import TypedDict


class Set(TypedDict):
    weight: float
    reps: int


def estimated_one_rep_max(weight: float, reps: int) -> float:
    """
    Estimates the one rep max weight for a given weight and number of reps.
    Formula: e1RM = weight * (1 + reps / 30)
    Args:
        weight (float): The weight lifted in kilograms.
        reps (int): The number of repetitions.

    Returns:
        float: The estimated one rep max weight.
    """

    if reps <= 0:
        return 0.00
    if reps == 1:
        return round(weight, 2)
    return round(weight * (1 + reps / 30), 2)


def set_tonnage(weight: float, reps: int) -> float:
    """
    Sets the tonnage for a given weight and number of reps.
    Formula: tonnage = weight * reps
    Args:
        weight (float): The weight lifted in kilograms.
        reps (int): The number of repetitions.

    Returns:
        float: The tonnage.
    """
    return round(weight * reps, 2)


def workout_tonnage(sets: list[Set]) -> float:
    """
    Calculates the total tonnage for a workout.
    Args:
        sets (list[dict[Set]]): A list of sets, where each set
        is a dictionary with 'weight' and 'reps' keys.

    Returns:
        float: The total tonnage.
    """
    if not sets:
        return 0.0
    return sum(set_tonnage(set_["weight"], set_["reps"]) for set_ in sets)
