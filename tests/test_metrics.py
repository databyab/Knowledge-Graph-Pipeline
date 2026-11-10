from eval.metrics import set_scores


def test_set_scores() -> None:
    assert set_scores({"a", "b"}, {"b", "c"}) == (0.5, 0.5, 0.5)
