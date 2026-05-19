from backend.config import Settings
from backend.schemas.alerts import Direction
from backend.services.options_selector import OptionsSelector


def test_select_call_contract():
    sel = OptionsSelector(Settings())
    contract, reason = sel.select(Direction.CALL, 585.0)
    assert contract is not None
    assert contract.contract_type == "CALL"
    assert reason == ""


def test_spread_rejection_with_tight_filter():
    s = Settings(max_spread_pct=0.001)
    sel = OptionsSelector(s)
    contract, reason = sel.select(Direction.PUT, 585.0)
    assert contract is None or reason != ""
