class EmptyDocumentError(Exception):
    pass


class EmbeddingDimensionError(Exception):
    """The embedding model returned a vector the stored chunks cannot be compared against."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"Query embedding has {actual} dimensions but the corpus stores {expected}. "
            "The embedding model and the ingested chunks must match."
        )
        self.expected = expected
        self.actual = actual
