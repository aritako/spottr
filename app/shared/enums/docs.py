from enum import StrEnum


class RetrievalStatus(StrEnum):
    """Outcome of a retrieval attempt."""

    OK = "ok"
    EMPTY_CORPUS = "empty_corpus"
    NO_MATCH = "no_match"
