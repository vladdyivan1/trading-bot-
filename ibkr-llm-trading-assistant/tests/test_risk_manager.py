"""Risk manager tests."""

from config.settings import Settings
from risk.position_sizing import size_by_risk
from risk.risk_manager import RiskManager
from schemas import Direction, LLMRecommendation, TradeSignal


def _signal(confidence: float = 0.8, rr_entry: float = 100.0) -> TradeSignal:
    return TradeSignal(
        symbol="SPY",
        direction=Direction.LONG,
        entry_price=rr_entry,
        stop_loss=rr_entry - 2.0,
        take_profit=rr_entry + 4.0,
        confidence_score=confidence,
        reason="test",
    )


def test_blocks_low_confidence() -> None:
    rm = RiskManager(Settings(min_model_confidence=0.65))
    rm.update_equity(100_000)
    result = rm.validate(_signal(confidence=0.5), backtest_trades=50)
    assert not result.approved
    assert any("Confidence" in r for r in result.reasons)


def test_blocks_kill_switch() -> None:
    rm = RiskManager(Settings(kill_switch=True, min_model_confidence=0.5))
    rm.update_equity(100_000)
    result = rm.validate(_signal(confidence=0.9), backtest_trades=50)
    assert not result.approved


def test_approves_valid_signal() -> None:
    rm = RiskManager(
        Settings(
            min_model_confidence=0.5,
            min_reward_to_risk=1.0,
            min_backtest_trades=10,
            kill_switch=False,
        )
    )
    rm.update_equity(100_000)
    llm = LLMRecommendation(trade_allowed=True, setup_quality=0.8, market_regime="test")
    result = rm.validate(_signal(confidence=0.9), llm=llm, backtest_trades=50)
    assert result.approved
    assert result.adjusted_quantity and result.adjusted_quantity > 0


def test_position_sizing() -> None:
    sig = _signal()
    qty = size_by_risk(100_000, sig, risk_pct=0.5)
    assert qty > 0
