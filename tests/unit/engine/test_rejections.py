from app.engine import rejections


def test_build_rejection_drops_citations_and_preserves_reported_tools() -> None:
    result = rejections.build_rejection(
        rejections.NOTHING_FOUND, ["search_coaching_docs", "query_workouts"]
    )

    assert result == {
        "answer": rejections.NOTHING_FOUND,
        "used_tools": ["search_coaching_docs", "query_workouts"],
        "citations": [],
    }


def test_rejection_family_names_what_the_coach_can_answer() -> None:
    messages = [
        rejections.OUT_OF_SCOPE,
        rejections.NOTHING_FOUND,
        rejections.COULD_NOT_COMPLETE,
    ]

    assert len(set(messages)) == 3
    for message in messages:
        assert "logged workouts" in message
        assert "coaching material" in message
