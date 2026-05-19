from backend.schemas.decisions import Direction
from backend.services.options_selector import OptionsSelector


def test_select_call_contract():
    sel = OptionsSelector()
    c = sel.select_contract(500.0, Direction.CALL, dte=0)
    assert c is not None
    assert c.option_type == "call"
    assert c.underlying == "SPY"


def test_spread_validation():
    sel = OptionsSelector()
    c = sel.select_contract(500.0, Direction.PUT, dte=1)
    assert c is not None
    reasons = sel.validate_contract(c)
    assert isinstance(reasons, list)
