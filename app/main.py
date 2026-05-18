"""Command-line MVP orchestration entrypoint."""

from __future__ import annotations

import argparse

from ai.signal_analyzer import SignalAnalyzer
from backtesting.engine import BacktestEngine
from config.settings import settings
from data.data_store import HistoricalDataStore
from execution.execution_engine import ExecutionEngine
from risk.risk_manager import RiskContext
from strategies.strategy_registry import registry


def run_backtest(symbol: str, strategy_name: str, timeframe: str = "1 day") -> None:
    store = HistoricalDataStore()
    bars = store.load_bars(symbol, "STK", "SMART", "USD", timeframe)
    if bars.empty:
        raise RuntimeError(f"No stored data for {symbol}. Download historical data first.")
    strategy = registry.create(strategy_name, symbol=symbol, asset_class="STK", timeframe=timeframe)
    result = BacktestEngine(initial_capital=settings.initial_capital).run(bars, strategy)
    print(result.metrics)


def run_signal_review_and_paper_trade(symbol: str, strategy_name: str, timeframe: str = "1 day") -> None:
    store = HistoricalDataStore()
    bars = store.load_bars(symbol, "STK", "SMART", "USD", timeframe)
    if bars.empty:
        raise RuntimeError(f"No stored data for {symbol}. Download historical data first.")
    strategy = registry.create(strategy_name, symbol=symbol, asset_class="STK", timeframe=timeframe)
    backtest = BacktestEngine(initial_capital=settings.initial_capital).run(bars, strategy)
    signal = strategy.generate_signal(bars)
    if signal is None:
        print("No actionable signal.")
        return
    llm_review = SignalAnalyzer().analyze(
        signal,
        backtest.metrics,
        market_summary={"latest_close": float(bars["close"].iloc[-1]), "rows": len(bars)},
    )
    if not llm_review.trade_allowed:
        print(f"LLM did not approve setup: {llm_review.reasoning}")
        return
    context = RiskContext(
        account_equity=settings.initial_capital,
        peak_equity=settings.initial_capital,
        backtest_trades=int(backtest.metrics["number_of_trades"]),
    )
    execution = ExecutionEngine().execute_paper_signal(signal, context, strategy.name)
    print(execution)


def main() -> None:
    parser = argparse.ArgumentParser(description=settings.project_name)
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--strategy", default="moving_average_crossover", choices=registry.names())
    parser.add_argument("--timeframe", default="1 day")
    parser.add_argument("--paper-trade", action="store_true")
    args = parser.parse_args()
    if args.paper_trade:
        run_signal_review_and_paper_trade(args.symbol, args.strategy, args.timeframe)
    else:
        run_backtest(args.symbol, args.strategy, args.timeframe)


if __name__ == "__main__":
    main()
