"""CLI entry point for common workflows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loguru import logger

from ai.signal_analyzer import SignalAnalyzer
from backtesting.engine import BacktestEngine
from config.settings import get_settings
from data.data_store import DataStore
from data.historical_data import HistoricalDataService
from execution.execution_engine import ExecutionEngine
from models.model_training import ModelTrainer
from models.predictive_model import PredictiveModel
from strategies.strategy_registry import get_strategy, list_strategies


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    logger.add(settings.log_file, rotation="10 MB", level=settings.log_level)


def cmd_download(args: argparse.Namespace) -> None:
    service = HistoricalDataService()
    df = service.download(
        args.symbol,
        timeframe=args.timeframe,
        asset_class=args.asset_class,
        years=args.years,
        force_refresh=args.force,
    )
    logger.info("Downloaded {} bars for {}", len(df), args.symbol)


def cmd_backtest(args: argparse.Namespace) -> None:
    store = DataStore()
    df = store.load(args.symbol, args.timeframe, args.asset_class)
    if df.empty:
        logger.error("No data for {}. Run download first.", args.symbol)
        return
    if "close" not in df.columns:
        df = df.rename(columns={c: c.lower() for c in df.columns})
    strategy = get_strategy(args.strategy, {"symbol": args.symbol, "timeframe": args.timeframe})
    engine = BacktestEngine()
    result = engine.run(strategy, df, args.symbol)
    print(json.dumps(result.metrics.model_dump(), indent=2))
    if args.export:
        result.trades.to_csv(args.export, index=False)
        logger.info("Trades exported to {}", args.export)


def cmd_analyze(args: argparse.Namespace) -> None:
    store = DataStore()
    df = store.load(args.symbol, args.timeframe)
    if df.empty:
        logger.error("No data for {}", args.symbol)
        return
    strategy = get_strategy(args.strategy, {"symbol": args.symbol})
    signal = strategy.generate_signal(df)
    if not signal:
        logger.info("No signal generated")
        return
    analyzer = SignalAnalyzer()
    rec = analyzer.analyze(signal, backtest_metrics={})
    print(json.dumps(rec.model_dump(), indent=2))


def cmd_trade(args: argparse.Namespace) -> None:
    store = DataStore()
    df = store.load(args.symbol, args.timeframe)
    if df.empty:
        logger.error("No data for {}", args.symbol)
        return
    strategy = get_strategy(args.strategy, {"symbol": args.symbol})
    signal = strategy.generate_signal(df)
    if not signal:
        logger.info("No signal to execute")
        return
    engine_bt = BacktestEngine()
    bt = engine_bt.run(strategy, df, args.symbol)
    engine = ExecutionEngine()
    result = engine.process_signal(
        signal,
        backtest_metrics=bt.metrics.model_dump(),
        backtest_trades=bt.metrics.num_trades,
        skip_llm=args.skip_llm,
    )
    print(json.dumps(result, indent=2, default=str))


def cmd_train(args: argparse.Namespace) -> None:
    store = DataStore()
    df = store.load(args.symbol, args.timeframe)
    if df.empty:
        logger.error("No data for {}", args.symbol)
        return
    trainer = ModelTrainer()
    metrics = trainer.train_and_save(df, args.symbol)
    print(json.dumps(metrics, indent=2))


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="IBKR LLM Trading Assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    p_dl = sub.add_parser("download", help="Download historical data")
    p_dl.add_argument("symbol", default="SPY")
    p_dl.add_argument("--timeframe", default="1 day")
    p_dl.add_argument("--asset-class", default="STK")
    p_dl.add_argument("--years", type=int, default=5)
    p_dl.add_argument("--force", action="store_true")
    p_dl.set_defaults(func=cmd_download)

    p_bt = sub.add_parser("backtest", help="Run backtest")
    p_bt.add_argument("symbol", default="SPY")
    p_bt.add_argument("--strategy", default="moving_average_crossover")
    p_bt.add_argument("--timeframe", default="1 day")
    p_bt.add_argument("--asset-class", default="STK")
    p_bt.add_argument("--export", default="")
    p_bt.set_defaults(func=cmd_backtest)

    p_an = sub.add_parser("analyze", help="LLM analyze current signal")
    p_an.add_argument("symbol", default="SPY")
    p_an.add_argument("--strategy", default="moving_average_crossover")
    p_an.add_argument("--timeframe", default="1 day")
    p_an.set_defaults(func=cmd_analyze)

    p_tr = sub.add_parser("trade", help="Full pipeline: signal → LLM → risk → paper")
    p_tr.add_argument("symbol", default="SPY")
    p_tr.add_argument("--strategy", default="moving_average_crossover")
    p_tr.add_argument("--timeframe", default="1 day")
    p_tr.add_argument("--skip-llm", action="store_true")
    p_tr.set_defaults(func=cmd_trade)

    p_ml = sub.add_parser("train-model", help="Train predictive model")
    p_ml.add_argument("symbol", default="SPY")
    p_ml.add_argument("--timeframe", default="1 day")
    p_ml.set_defaults(func=cmd_train)

    sub.add_parser("strategies", help="List strategies").set_defaults(
        func=lambda a: print("\n".join(list_strategies()))
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
