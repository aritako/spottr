from app.eval.metrics import QuestionResult, RetrievedPassage


def _passages(*pairs: tuple[str, float]) -> tuple[RetrievedPassage, ...]:
    return tuple(
        RetrievedPassage(document_source=source, chunk_index=index, distance=distance)
        for index, (source, distance) in enumerate(pairs)
    )


def positive(question: str, expected: str, *pairs: tuple[str, float]) -> QuestionResult:
    return QuestionResult(
        question=question,
        expected_document=expected,
        passages=_passages(*pairs),
    )


def negative(question: str, *pairs: tuple[str, float]) -> QuestionResult:
    return QuestionResult(
        question=question,
        expected_document=None,
        passages=_passages(*pairs),
    )
