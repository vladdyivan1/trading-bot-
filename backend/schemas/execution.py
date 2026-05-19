from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OptionContract(BaseModel):
    symbol: str
    underlying: str = "SPY"
    expiration: str
    strike: float
    option_type: str  # call | put
    delta: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    dte: int = 0


class ExecutionResult(BaseModel):
    success: bool
    order_id: str
    contract: Optional[OptionContract] = None
    side: str
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    status: str  # open | closed | rejected
    message: str = ""
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
