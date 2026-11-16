"""
Pure metric and time-bucketing helpers shared by the REST analytics layer and the coach engine.

Nothing here may import the ORM, a database session, or perform I/O. Callers pass plain values or
dataclasses in and get plain values out, which keeps the metrics trivially unit-testable.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Literal, TypedDict

GroupBy = Literal["day", "week", "month", "year"]


class SetValues(TypedDict):
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


def workout_tonnage(sets: list[SetValues]) -> float:
    """
    Calculates the total tonnage for a workout.
    Args:
        sets (list[SetValues]): A list of sets, where each set
        is a dictionary with 'weight' and 'reps' keys.

    Returns:
        float: The total tonnage.
    """
    if not sets:
        return 0.0
    return sum(set_tonnage(set_["weight"], set_["reps"]) for set_ in sets)


def tonnage_by_exercise(
    entries: list[DatedTonnageByExercise],
    group_by: GroupBy | None = None,
) -> dict[str, list[tuple[str, float]]]:
    """
    Group tonnage entries by exercise and time bucket, returning total tonnage per bucket.

    Args:
        entries: A list of dated tonnage entries tagged with an exercise name.
        group_by: The bucket grain. Defaults to weeks.

    Returns:
        A dictionary mapping exercise name to a chronologically sorted list of
        (bucket_label, total_tonnage) tuples.
    """
    buckets: dict[tuple[str, tuple[int, int]], float] = defaultdict(float)
    label_for: dict[tuple[str, tuple[int, int]], str] = {}

    for entry in entries:
        key = (entry.exercise, sort_key(entry.date, group_by))
        buckets[key] += entry.tonnage
        label_for[key] = get_time_bucket_key(entry.date, group_by)

    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for key, tonnage in sorted(buckets.items()):
        grouped[key[0]].append((label_for[key], tonnage))

    return dict(grouped)


def e1rm_by_exercise(
    entries: list[DatedE1RMByExercise],
    group_by: GroupBy | None = None,
) -> dict[str, list[tuple[str, float]]]:
    """
    Group e1RM entries by exercise and time bucket, keeping the max per bucket.

    Args:
        entries: A list of dated e1RM entries tagged with an exercise name.
        group_by: The bucket grain. Defaults to weeks.

    Returns:
        A dictionary mapping exercise name to a chronologically sorted list of
        (bucket_label, maximum_e1rm) tuples.
    """
    buckets: dict[tuple[str, tuple[int, int]], float] = defaultdict(float)
    label_for: dict[tuple[str, tuple[int, int]], str] = {}

    for entry in entries:
        key = (entry.exercise, sort_key(entry.date, group_by))
        buckets[key] = max(buckets[key], entry.e1rm)
        label_for[key] = get_time_bucket_key(entry.date, group_by)

    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for key, e1rm in sorted(buckets.items()):
        grouped[key[0]].append((label_for[key], e1rm))

    return dict(grouped)


def sort_key(d: date, group_by: GroupBy | None = None) -> tuple[int, int]:
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


def get_time_bucket_key(d: date, group_by: GroupBy | None = None) -> str:
    """
    Returns a human-readable label for the time bucket `d` falls into, at the given grain.

    Note: these labels are for DISPLAY. Internally, sorting is still done on the
    (year, week)/(year, month)/etc. tuples before formatting — see tonnage_over_time, which sorts
    by the underlying key, not the string.
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
    group_by: GroupBy | None = None,
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
    group_by: GroupBy | None = None,
) -> list[tuple[str, float]]:
    buckets: dict[tuple[int, int], float] = defaultdict(float)
    label_for: dict[tuple[int, int], str] = {}

    for entry in entries:
        key = sort_key(entry.date, group_by)
        buckets[key] = max(buckets[key], entry.e1rm)
        label_for[key] = get_time_bucket_key(entry.date, group_by)

    return [(label_for[k], v) for k, v in sorted(buckets.items())]
