from app.engine import rejections


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
