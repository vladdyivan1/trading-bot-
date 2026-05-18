from risk.position_sizing import calculate_position_size, reward_risk_ratio


def test_position_size_calculation():
    units = calculate_position_size(
        account_equity=100_000,
        entry_price=500,
        stop_loss=495,
        max_risk_pct=0.5,
        max_units=10,
    )
    assert units > 0
    assert units <= 10


def test_reward_risk_ratio():
    rr = reward_risk_ratio(entry_price=100, stop_loss=98, take_profit=104)
    assert rr == 2.0
