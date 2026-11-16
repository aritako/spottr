import json
from datetime import date
from unittest.mock import MagicMock, patch

from app.engine.tools import Tools
from app.shared.enums.coach import Metric
from app.shared.enums.docs import RetrievalStatus
from app.shared.schemas.docs import PassageRead, PassageRetrieval


def test_query_workouts_delegates_to_the_analytics_handler() -> None:
    tools = Tools(MagicMock())
    expected = {
        "metric": "tonnage",
        "group_by": "day",
        "exercise": "Back Squat",
        "buckets": [{"label": "Jun 15, 2026", "value": 500.0}],
    }

    with patch.object(tools.analyticsHandler, "query_workouts", return_value=expected) as query:
        result = tools.query_workouts(
            metric=Metric.TONNAGE,
            exercise="Back Squat",
            start_date="2026-06-01",
            end_date="2026-06-30",
            group_by="day",
        )

    query.assert_called_once_with(
        metric=Metric.TONNAGE,
        exercise="Back Squat",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        group_by="day",
    )
    assert result == expected


def test_query_workouts_defaults_to_all_time_weekly_tonnage() -> None:
    tools = Tools(MagicMock())

    with patch.object(
        tools.analyticsHandler, "query_workouts", return_value={"result": "no data"}
    ) as query:
        tools.query_workouts()

    query.assert_called_once_with(
        metric=Metric.TONNAGE,
        exercise=None,
        start_date=None,
        end_date=None,
        group_by="week",
    )


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
