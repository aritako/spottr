import json
from datetime import date
from unittest.mock import MagicMock, patch

from app.engine.helpers import DatedTonnageByExercise, weekly_tonnage_by_exercise
from app.engine.tools import Tools
from app.shared.enums.docs import RetrievalStatus
from app.shared.schemas.docs import PassageRead, PassageRetrieval


def test_weekly_tonnage_by_exercise() -> None:
    entries = [
        DatedTonnageByExercise(exercise="bench", date=date(2025, 12, 30), tonnage=100.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 1), tonnage=100.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 2), tonnage=120.0),
        DatedTonnageByExercise(exercise="bench", date=date(2026, 1, 8), tonnage=120.0),
        DatedTonnageByExercise(exercise="squat", date=date(2026, 1, 1), tonnage=80.0),
        DatedTonnageByExercise(exercise="squat", date=date(2026, 1, 8), tonnage=90.0),
        DatedTonnageByExercise(exercise="deadlift", date=date(2026, 1, 1), tonnage=150.0),
        DatedTonnageByExercise(exercise="deadlift", date=date(2026, 1, 8), tonnage=160.0),
        DatedTonnageByExercise(exercise="overhead press", date=date(2026, 1, 1), tonnage=100.0),
        DatedTonnageByExercise(exercise="overhead press", date=date(2026, 1, 8), tonnage=120.0),
    ]
    result = weekly_tonnage_by_exercise(entries)
    assert result == {
        "bench": [("2026-W01", 320.0), ("2026-W02", 120.0)],
        "squat": [("2026-W01", 80.0), ("2026-W02", 90.0)],
        "deadlift": [("2026-W01", 150.0), ("2026-W02", 160.0)],
        "overhead press": [("2026-W01", 100.0), ("2026-W02", 120.0)],
    }


def test_search_coaching_docs_returns_the_handler_result() -> None:
    tools = Tools(MagicMock())
    passage = PassageRead(
        document_id=1,
        document_title="Deload Guidelines",
        chunk_index=2,
        content="Deload every four to six weeks.",
    )
    retrieval = PassageRetrieval(status=RetrievalStatus.OK, passages=[passage])

    with patch.object(tools.docsHandler, "retrieve", return_value=retrieval) as retrieve:
        result = tools.search_coaching_docs("should I deload?", k=None)

    retrieve.assert_called_once_with("should I deload?", None)
    assert result == {
        "status": "ok",
        "passages": [
            {
                "document_id": 1,
                "document_title": "Deload Guidelines",
                "chunk_index": 2,
                "content": "Deload every four to six weeks.",
            }
        ],
    }
    assert json.loads(json.dumps(result)) == result
