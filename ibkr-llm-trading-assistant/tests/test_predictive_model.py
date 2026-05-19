"""ML model tests."""

from models.predictive_model import PredictiveModel


def test_train_and_score(sample_ohlcv) -> None:
    model = PredictiveModel()
    metrics = model.train(sample_ohlcv)
    assert metrics["samples"] > 50
    score = model.score_setup(sample_ohlcv)
    assert 0.0 <= score <= 1.0
