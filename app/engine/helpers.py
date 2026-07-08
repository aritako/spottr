"""
This file should only contain pure functions and
helper classes that will be used by the engine.tools.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import TypedDict


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


def weekly_tonnage(entries: list[DatedTonnage]) -> list[tuple[str, float]]:
    """
    Groups per-workout tonnage into weekly buckets.
    Args:
        entries: A list of dates with their total tonnage lifted
    Returns:
        a list of (week_key, total_tonnage) sorted chronologically,
        where week_key is an ISO year-week string like "2026-W25".
    """
    weekly_bucket: dict[str, float] = defaultdict(float)

    for entry in entries:
        date = entry.date
        tonnage = entry.tonnage

        year, week = date.isocalendar()[0:2]

        weekly_bucket_key = f"{year}-W{week:02d}"
        weekly_bucket[weekly_bucket_key] += tonnage

    return sorted(weekly_bucket.items())


def weekly_tonnage_by_exercise(
    entries: list[DatedTonnageByExercise],
) -> dict[str, list[tuple[str, float]]]:
    final_bucket: dict[str, list[tuple[str, float]]] = {}
    exercise_bucket: dict[str, list[DatedTonnage]] = defaultdict(list)

    for entry in entries:
        date_tonnage = DatedTonnage(entry.date, entry.tonnage)
        exercise_bucket[entry.exercise].append(date_tonnage)

    for exercise, dated_tonnage in exercise_bucket.items():
        final_bucket[exercise] = weekly_tonnage(dated_tonnage)

    return final_bucket


def weekly_e1rm(entries: list[DatedE1RM]) -> list[tuple[str, float]]:
    weekly_bucket: dict[str, float] = defaultdict(float)

    for entry in entries:
        date = entry.date
        e1rm = entry.e1rm

        year, week = date.isocalendar()[0:2]
        weekly_bucket_key = f"{year}-W{week:02d}"
        weekly_bucket[weekly_bucket_key] = max(weekly_bucket[weekly_bucket_key], e1rm)

    return sorted(weekly_bucket.items())


def weekly_e1rm_by_exercise(
    entries: list[DatedE1RMByExercise],
) -> dict[str, list[tuple[str, float]]]:
    final_bucket: dict[str, list[tuple[str, float]]] = {}
    exercise_bucket: dict[str, list[DatedE1RM]] = defaultdict(list)

    for entry in entries:
        dated_e1rm = DatedE1RM(entry.date, entry.e1rm)
        exercise_bucket[entry.exercise].append(dated_e1rm)

    for exercise, dated_e1rm in exercise_bucket.items():
        final_bucket[exercise] = weekly_e1rm(dated_e1rm)

    return final_bucket
