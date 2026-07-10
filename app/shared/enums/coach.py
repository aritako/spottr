from enum import StrEnum


class Metric(StrEnum):
    E1RM = "e1rm"
    TONNAGE = "tonnage"
    MAX_WEIGHT = "max_weight"
    AVG_RPE = "avg_rpe"
    SET_COUNT = "set_count"
