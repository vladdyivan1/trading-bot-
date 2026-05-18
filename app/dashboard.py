"""Streamlit dashboard for the trading assistant."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ai.signal_analyzer import SignalAnalyzer
from backtesting.engine import BacktestEngine
from config.settings import settings
from data.data_store import HistoricalDataStore
from execution.execution_engine import ExecutionEngine
from risk.kill_switch import KillSwitch
from risk.risk_manager import RiskContext
from strategies.strategy_registry import registry


def _load_data(symbol: str, timeframe: str) -> pd.DataFrame:
    return HistoricalDataStore().load_bars(symbol, "STK", "SMART", "USD", timeframe)


def main() -> None:
    st.set_page_config(page_title=settings.project_name, layout="wide")
    st.title("IBKR LLM Trading Assistant")
    kill_switch = KillSwitch()

    with st.sidebar:
        st.header("Controls")
        symbol = st.text_input("Symbol", "SPY").upper()
        timeframe = st.selectbox("Timeframe", ["1 min", "5 mins", "15 mins", "1 hour", "1 day"], index=4)
        strategy_name = st.selectbox("Strategy", registry.names())
        st.caption(f"Mode: {settings.trading_mode}; live enabled: {settings.enable_live_trading}")
        if st.button("Enable kill switch", type="primary"):
            kill_switch.enable("dashboard")
        if st.button("Disable kill switch"):
            kill_switch.disable()
        st.warning("Kill switch enabled" if kill_switch.is_enabled() else "Kill switch disabled")

    status_cols = st.columns(4)
    status_cols[0].metric("IBKR host", settings.ibkr_host)
    status_cols[1].metric("IBKR port", settings.ibkr_port)
    status_cols[2].metric("Max risk/trade", f"{settings.max_risk_per_trade_pct:.2%}")
    status_cols[3].metric("Max open positions", settings.max_open_positions)

    tabs = st.tabs(["Backtest", "AI Analysis", "Paper Trading", "Risk Settings", "Data"])

    with tabs[0]:
        bars = _load_data(symbol, timeframe)
        if bars.empty:
            st.info("No stored historical data found. Use the Python HistoricalDataService to download from IBKR.")
        else:
            strategy = registry.create(strategy_name, symbol=symbol, asset_class="STK", timeframe=timeframe)
            result = BacktestEngine(initial_capital=settings.initial_capital).run(bars, strategy)
            st.subheader("Metrics")
            st.dataframe(pd.DataFrame([result.metrics]))
            st.plotly_chart(px.line(result.equity_curve, title="Equity Curve"), use_container_width=True)
            st.subheader("Trade Log")
            st.dataframe(pd.DataFrame(result.trades))

    with tabs[1]:
        bars = _load_data(symbol, timeframe)
        if st.button("Review latest setup with LLM"):
            if bars.empty:
                st.error("No data available.")
            else:
                strategy = registry.create(strategy_name, symbol=symbol, asset_class="STK", timeframe=timeframe)
                signal = strategy.generate_signal(bars)
                if signal is None:
                    st.info("No actionable signal.")
                else:
                    backtest = BacktestEngine(initial_capital=settings.initial_capital).run(bars, strategy)
                    review = SignalAnalyzer().analyze(
                        signal,
                        backtest.metrics,
                        {"latest_close": float(bars["close"].iloc[-1]), "rows": len(bars)},
                    )
                    st.json(review.dict())

    with tabs[2]:
        st.write("Paper trading is the only enabled execution mode in the MVP.")
        if st.button("Risk-check and simulate paper trade"):
            bars = _load_data(symbol, timeframe)
            if bars.empty:
                st.error("No data available.")
            else:
                strategy = registry.create(strategy_name, symbol=symbol, asset_class="STK", timeframe=timeframe)
                signal = strategy.generate_signal(bars)
                if signal is None:
                    st.info("No actionable signal.")
                else:
                    backtest = BacktestEngine(initial_capital=settings.initial_capital).run(bars, strategy)
                    context = RiskContext(
                        account_equity=settings.initial_capital,
                        peak_equity=settings.initial_capital,
                        backtest_trades=int(backtest.metrics["number_of_trades"]),
                    )
                    result = ExecutionEngine().execute_paper_signal(signal, context, strategy.name)
                    st.json(
                        {
                            "accepted": result.accepted,
                            "reasons": result.risk_decision.reasons,
                            "quantity": result.risk_decision.quantity,
                            "fill": result.fill.__dict__ if result.fill else None,
                        }
                    )

    with tabs[3]:
        st.json(
            {
                "max_daily_loss_pct": settings.max_daily_loss_pct,
                "max_weekly_loss_pct": settings.max_weekly_loss_pct,
                "max_account_drawdown_pct": settings.max_account_drawdown_pct,
                "min_reward_risk": settings.min_reward_risk,
                "min_model_confidence": settings.min_model_confidence,
                "min_backtest_trades": settings.min_backtest_trades,
                "max_allowed_spread_pct": settings.max_allowed_spread_pct,
            }
        )

    with tabs[4]:
        bars = _load_data(symbol, timeframe)
        st.write(f"Stored bars: {len(bars)}")
        st.dataframe(bars.tail(100))


if __name__ == "__main__":
    main()
