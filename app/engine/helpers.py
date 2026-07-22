"""
This file should only contain pure functions and
helper classes that will be used by the engine.tools.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Literal, TypedDict


class Set(TypedDict):
    weight: float
    reps: int


@dataclass
class DatedTonnage:
    date: date
    tonnage: float


@dataclass
class DatedE1RM:
    date: date
    e1rm: float


@dataclass
class DatedTonnageByExercise:
    exercise: str
    date: date
    tonnage: float


@dataclass
class DatedE1RMByExercise:
    exercise: str
    date: date
    e1rm: float


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


def sort_key(
    d: date, group_by: Literal["day", "week", "month", "year"] | None = None
) -> tuple[int, int]:
    match group_by:
        case "day":
            return (d.year, d.toordinal())
        case "week":
            iso_year, iso_week, _ = d.isocalendar()
            return (iso_year, iso_week)
        case "month":
            return (d.year, d.month)
        case "year":
            return (d.year, 0)
        case None:
            iso_year, iso_week, _ = d.isocalendar()
            return (iso_year, iso_week)


def get_time_bucket_key(
    d: date, group_by: Literal["day", "week", "month", "year"] | None = None
) -> str:
    """
    Returns a human-readable, chronologically-sortable-enough label for the
    time bucket `d` falls into, at the given grain.

    Note: these labels are for DISPLAY. Internally, sorting is still done
    on the (year, week)/(year, month)/etc. tuples before formatting — see
    tonnage_over_time, which sorts by the underlying key, not the string.
    """
    match group_by:
        case None:
            iso_year, iso_week, _ = d.isocalendar()
            monday = date.fromisocalendar(iso_year, iso_week, 1)
            return f"Week of {monday.strftime('%b %d, %Y')}"  # "Week of Jun 15, 2026"

        case "day":
            return d.strftime("%b %d, %Y")  # "Jun 20, 2026"

        case "week":
            iso_year, iso_week, _ = d.isocalendar()
            monday = date.fromisocalendar(iso_year, iso_week, 1)
            return f"Week of {monday.strftime('%b %d, %Y')}"  # "Week of Jun 15, 2026"

        case "month":
            return d.strftime("%b %Y")  # "Jun 2026"

        case "year":
            return str(d.year)  # "2026"


def tonnage_over_time(
    entries: list[DatedTonnage],
    group_by: Literal["day", "week", "month", "year"] | None = None,
) -> list[tuple[str, float]]:
    buckets: dict[tuple[int, int], float] = defaultdict(float)
    label_for: dict[tuple[int, int], str] = {}

    for entry in entries:
        key = sort_key(entry.date, group_by)
        buckets[key] += entry.tonnage
        label_for[key] = get_time_bucket_key(entry.date, group_by)

    return [(label_for[k], v) for k, v in sorted(buckets.items())]


def e1rm_over_time(
    entries: list[DatedE1RM],
    group_by: Literal["day", "week", "month", "year"] | None = None,
) -> list[tuple[str, float]]:
    buckets: dict[tuple[int, int], float] = defaultdict(float)
    label_for: dict[tuple[int, int], str] = {}

    for entry in entries:
        key = sort_key(entry.date, group_by)
        buckets[key] = max(buckets[key], entry.e1rm)
        label_for[key] = get_time_bucket_key(entry.date, group_by)

    return [(label_for[k], v) for k, v in sorted(buckets.items())]
