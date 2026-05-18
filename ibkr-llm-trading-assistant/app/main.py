"""Main CLI entry point for the trading assistant MVP."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loguru import logger

from ai.signal_analyzer import SignalAnalyzer
from backtesting.engine import BacktestEngine
from broker.ibkr_client import IBKRClient
from config.settings import get_settings
from data.historical_data import HistoricalDataEngine
from database.db import init_db
from execution.execution_engine import ExecutionEngine
from models.predictive_model import PredictiveModel
from risk.risk_manager import RiskManager
from schemas import AssetClass, Timeframe
from strategies.strategy_registry import get_strategy, list_strategies


def setup_logging() -> None:
    settings = get_settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    logger.add(
        settings.log_dir / "trading_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level=settings.log_level,
    )


def cmd_init(_: argparse.Namespace) -> None:
    init_db()
    logger.info("Database initialized")


def cmd_download(args: argparse.Namespace) -> None:
    client = IBKRClient()
    if not client.connect():
        logger.error("Connect IB Gateway/TWS first")
        sys.exit(1)
    engine = HistoricalDataEngine(client)
    ac = AssetClass.STK if args.asset_class == "STK" else AssetClass.CASH
    df = engine.download(args.symbol, ac, args.timeframe, force_refresh=args.force)
    logger.info("Downloaded {} bars for {}", len(df), args.symbol)
    client.disconnect()


def cmd_backtest(args: argparse.Namespace) -> None:
    init_db()
    store_engine = HistoricalDataEngine()
    ac = args.asset_class
    df = store_engine.reload(args.symbol, ac, args.timeframe)
    if df.empty:
        logger.error("No data for {} — run download first", args.symbol)
        sys.exit(1)
    strategy = get_strategy(args.strategy, args.symbol)
    engine = BacktestEngine()
    result = engine.run(strategy, df)
    logger.info(
        "Backtest {} on {}: return={:.2f}% trades={} sharpe={:.2f} max_dd={:.2f}%",
        args.strategy,
        args.symbol,
        result.total_return,
        result.num_trades,
        result.sharpe_ratio,
        result.max_drawdown,
    )
    print(result.model_dump_json(indent=2))


def cmd_trade(args: argparse.Namespace) -> None:
    """Full MVP pipeline: signal -> backtest -> model -> LLM -> risk -> paper trade."""
    init_db()
    settings = get_settings()
    if settings.live_trading_enabled:
        logger.warning("Live trading flag is set — ensure you intend paper mode")

    client = IBKRClient()
    connected = client.connect()
    if not connected:
        logger.warning("IBKR offline — using cached data only")

    hist = HistoricalDataEngine(client)
    ac = AssetClass.STK if args.asset_class == "STK" else AssetClass.CASH
    try:
        df = hist.download(args.symbol, ac, args.timeframe, use_cache=True)
    except ConnectionError:
        df = hist.reload(args.symbol, ac.value, args.timeframe)
    if df.empty:
        logger.error("No market data available")
        sys.exit(1)

    strategy = get_strategy(args.strategy, args.symbol, asset_class=ac)
    signal = strategy.run(df)
    if not signal:
        logger.info("No signal generated")
        return

    backtest = BacktestEngine().run(strategy, df)

    model_score = None
    try:
        model = PredictiveModel(f"{args.symbol}_model")
        model_path = settings.models_dir / f"final_{args.symbol}.joblib"
        if model_path.exists():
            model.load(model_path)
            model_score = model.score_setup(df, signal.direction.value)
            signal.model_score = model_score
            signal.confidence_score = (signal.confidence_score + model_score) / 2
    except Exception as e:
        logger.debug("Model scoring skipped: {}", e)

    llm_review = None
    analyzer = SignalAnalyzer()
    if analyzer.llm.is_available():
        from data.market_data import MarketDataService

        market_summary = (
            MarketDataService(client).get_latest_summary(args.symbol, ac)
            if connected
            else {"symbol": args.symbol, "bars": len(df)}
        )
        llm_review = analyzer.analyze(signal, market_summary, backtest)
        logger.info(
            "LLM review: allowed={} quality={:.2f}",
            llm_review.trade_allowed,
            llm_review.setup_quality,
        )
    else:
        logger.info("LLM not configured — skipping advisory review")

    engine = ExecutionEngine(client, RiskManager())
    result = engine.process_signal(
        signal,
        llm_review=llm_review,
        backtest_result=backtest,
        model_confidence=model_score,
    )
    logger.info("Execution result: {}", result)
    if connected:
        client.disconnect()


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="IBKR LLM Trading Assistant")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Initialize database")
    p_init.set_defaults(func=cmd_init)

    p_dl = sub.add_parser("download", help="Download historical data")
    p_dl.add_argument("symbol", default="SPY")
    p_dl.add_argument("--timeframe", default="5 mins")
    p_dl.add_argument("--asset-class", default="STK")
    p_dl.add_argument("--force", action="store_true")
    p_dl.set_defaults(func=cmd_download)

    p_bt = sub.add_parser("backtest", help="Run backtest")
    p_bt.add_argument("symbol")
    p_bt.add_argument("--strategy", default="ma_crossover")
    p_bt.add_argument("--timeframe", default="5 mins")
    p_bt.add_argument("--asset-class", default="STK")
    p_bt.set_defaults(func=cmd_backtest)

    p_trade = sub.add_parser("trade", help="Full MVP trade pipeline")
    p_trade.add_argument("symbol", default="SPY")
    p_trade.add_argument("--strategy", default="ma_crossover")
    p_trade.add_argument("--timeframe", default="5 mins")
    p_trade.add_argument("--asset-class", default="STK")
    p_trade.set_defaults(func=cmd_trade)

    sub.add_parser("strategies", help="List strategies")

    args = parser.parse_args()
    if args.command == "strategies":
        print("Available strategies:", list_strategies())
        return
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
