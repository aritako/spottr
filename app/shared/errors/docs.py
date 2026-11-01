class EmptyDocumentError(Exception):
    pass


class EmbeddingDimensionError(Exception):
    """The embedding model returned a vector the stored chunks cannot be compared against."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(
            f"Query embedding has {actual} dimensions but retrieval expects {expected} to "
            "compare against the stored chunks. Use the same embedding model the corpus "
            "was ingested with."
        )
        self.expected = expected
        self.actual = actual
