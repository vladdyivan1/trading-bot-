"""CLI entrypoint for MVP pipeline execution."""

        from __future__ import annotations

        import argparse
        import json

        from ai.signal_analyzer import SignalAnalyzer
        from backtesting.engine import BacktestEngine
        from broker.contracts import ContractSpec
        from broker.ibkr_client import IBKRClient
        from config.settings import get_settings
        from data.historical_data import HistoricalDataEngine
        from data.market_data import summarize_market_data
        from database.db import init_db
        from execution.execution_engine import ExecutionEngine
        from execution.paper_trader import PaperTrader
        from risk.risk_manager import AccountSnapshot, RiskManager
        from strategies.strategy_registry import build_strategy


        def parse_args() -> argparse.Namespace:
            parser = argparse.ArgumentParser(description="IBKR LLM Trading Assistant MVP")
            parser.add_argument("--symbol", default="SPY")
            parser.add_argument("--asset-class", default="STK", choices=["STK", "ETF", "FX", "FUT", "OPT"])
            parser.add_argument("--timeframe", default="1 day", choices=["1 min", "5 mins", "15 mins", "1 hour", "1 day"])
            parser.add_argument("--strategy", default="moving_average_crossover")
            parser.add_argument("--years", type=int, default=5)
            parser.add_argument("--connect", action="store_true", help="Connect to IBKR before fetching data")
            parser.add_argument("--auto-paper-trade", action="store_true", help="Submit paper trade when signal passes all checks")
            return parser.parse_args()


        def run() -> None:
            args = parse_args()
            settings = get_settings()
            init_db()

            ibkr_client = IBKRClient(settings=settings)
            if args.connect:
                ibkr_client.connect()

            contract = ContractSpec(symbol=args.symbol, asset_class=args.asset_class)
            historical = HistoricalDataEngine(ibkr_client=ibkr_client)

            if args.connect:
                bars = historical.load_or_fetch(contract, timeframe=args.timeframe, years=args.years)
            else:
                bars = historical.data_store.load_dataframe(
                    symbol=contract.symbol,
                    asset_class=contract.asset_class,
                    exchange=contract.exchange,
                    currency=contract.currency,
                    timeframe=args.timeframe,
                )

            if bars.empty:
                raise RuntimeError("No data found. Run with --connect to download data from IBKR.")

            strategy = build_strategy(args.strategy)
            backtester = BacktestEngine()
            backtest = backtester.run(
                strategy=strategy,
                bars=bars,
                symbol=args.symbol,
                asset_class=args.asset_class,
                timeframe=args.timeframe,
            )

            latest_signal = strategy.generate_signal(bars, args.symbol, args.asset_class, args.timeframe)
            market_summary = summarize_market_data(bars)

            print("Backtest metrics:")
            print(json.dumps(backtest.metrics, indent=2, default=str))

            if latest_signal is None:
                print("No actionable signal generated.")
                return

            analyzer = SignalAnalyzer()
            llm_review = analyzer.review_signal(
                signal=latest_signal,
                market_summary=market_summary,
                backtest_metrics=backtest.metrics,
            )
            print("
LLM review:")
            print(llm_review.model_dump_json(indent=2))

            risk_manager = RiskManager(settings=settings)
            account = AccountSnapshot(
                account_equity=100_000,
                daily_pnl_pct=0.0,
                weekly_pnl_pct=0.0,
                drawdown_pct=1.0,
                open_positions=0,
                trades_today=0,
            )

            risk_decision = risk_manager.evaluate(
                signal=latest_signal,
                account=account,
                model_confidence=latest_signal.confidence_score,
                backtest_sample_size=int(backtest.metrics.get("num_trades", 0)),
                spread_pct=0.05,
            )
            print("
Risk decision:")
            print(risk_decision.model_dump_json(indent=2))

            if args.auto_paper_trade:
                if not args.connect:
                    raise RuntimeError("--auto-paper-trade requires --connect")
                paper_trader = PaperTrader(ibkr_client=ibkr_client)
                engine = ExecutionEngine(risk_manager=risk_manager, paper_trader=paper_trader)
                result = engine.process_signal(
                    signal=latest_signal,
                    account_snapshot=account,
                    model_confidence=latest_signal.confidence_score,
                    backtest_sample_size=int(backtest.metrics.get("num_trades", 0)),
                    spread_pct=0.05,
                )
                print("
Execution result:")
                print(result)

            if args.connect:
                ibkr_client.disconnect()


        if __name__ == "__main__":
            run()
