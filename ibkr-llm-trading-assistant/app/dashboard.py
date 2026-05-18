"""Streamlit dashboard for the trading assistant."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from backtesting.engine import BacktestEngine
from broker.ibkr_client import IBKRClient
from config.settings import get_settings
from data.historical_data import HistoricalDataEngine
from database.db import init_db
from risk.kill_switch import KillSwitch
from risk.risk_manager import RiskManager
from schemas import AssetClass
from strategies.strategy_registry import get_strategy, list_strategies

st.set_page_config(
    page_title="IBKR LLM Trading Assistant",
    page_icon="📈",
    layout="wide",
)

settings = get_settings()


@st.cache_resource
def get_ib_client():
    return IBKRClient()


def page_overview():
    st.header("Overview")
    client = get_ib_client()
    col1, col2, col3 = st.columns(3)
    connected = client.is_connected
    if st.button("Connect to IBKR"):
        connected = client.connect()
    col1.metric("IBKR Status", "Connected" if connected else "Disconnected")
    col2.metric("Paper Mode", "Yes" if settings.ibkr_paper else "No")
    col3.metric("Live Trading", "ENABLED" if settings.live_trading_enabled else "Disabled")

    kill = KillSwitch()
    if kill.is_active:
        st.error(f"Kill switch ACTIVE: {kill.reason}")
    if st.button("🛑 ACTIVATE KILL SWITCH", type="primary"):
        kill.activate("Dashboard manual activation")
        st.rerun()
    if kill.is_active and st.button("Deactivate Kill Switch"):
        kill.deactivate()
        st.rerun()

    if connected:
        summary = client.account_summary()
        st.subheader("Account Summary")
        st.json(summary)
        st.subheader("Positions")
        st.dataframe(pd.DataFrame(client.positions()))


def page_data():
    st.header("Historical Data")
    symbol = st.text_input("Symbol", "SPY")
    asset = st.selectbox("Asset Class", ["STK", "CASH"])
    timeframe = st.selectbox("Timeframe", HistoricalDataEngine.SUPPORTED_TIMEFRAMES)
    force = st.checkbox("Force refresh from IBKR")
    if st.button("Download / Load Data"):
        client = get_ib_client()
        if not client.is_connected:
            client.connect()
        ac = AssetClass.STK if asset == "STK" else AssetClass.CASH
        engine = HistoricalDataEngine(client)
        with st.spinner("Loading data..."):
            df = engine.download(symbol, ac, timeframe, force_refresh=force)
        st.success(f"Loaded {len(df)} bars")
        if not df.empty:
            st.line_chart(df["close"])


def page_backtest():
    st.header("Backtest Runner")
    symbol = st.text_input("Symbol", "SPY", key="bt_sym")
    strategy_name = st.selectbox("Strategy", list_strategies())
    timeframe = st.selectbox("Timeframe", HistoricalDataEngine.SUPPORTED_TIMEFRAMES, key="bt_tf")
    if st.button("Run Backtest"):
        engine = HistoricalDataEngine()
        df = engine.reload(symbol, "STK", timeframe)
        if df.empty:
            st.error("No data — download first")
            return
        strategy = get_strategy(strategy_name, symbol)
        result = BacktestEngine().run(strategy, df)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Return", f"{result.total_return:.2f}%")
        c2.metric("Win Rate", f"{result.win_rate:.1f}%")
        c3.metric("Sharpe", f"{result.sharpe_ratio:.2f}")
        c4.metric("Max DD", f"{result.max_drawdown:.2f}%")
        if result.equity_curve:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=result.equity_curve, mode="lines", name="Equity"))
            st.plotly_chart(fig, use_container_width=True)
        if result.trades:
            trades_df = pd.DataFrame([t.model_dump() for t in result.trades])
            st.subheader("Trade Log")
            st.dataframe(trades_df)


def page_strategies():
    st.header("Strategy Comparison")
    symbols = st.multiselect("Symbols", ["SPY", "QQQ", "AAPL"], default=["SPY"])
    strategy_names = st.multiselect("Strategies", list_strategies(), default=list_strategies())
    timeframe = st.selectbox("Timeframe", HistoricalDataEngine.SUPPORTED_TIMEFRAMES, key="cmp_tf")
    if st.button("Compare"):
        rows = []
        engine = BacktestEngine()
        hist = HistoricalDataEngine()
        for sym in symbols:
            df = hist.reload(sym, "STK", timeframe)
            if df.empty:
                continue
            for name in strategy_names:
                s = get_strategy(name, sym)
                r = engine.run(s, df)
                rows.append(
                    {
                        "symbol": sym,
                        "strategy": name,
                        "return_pct": r.total_return,
                        "sharpe": r.sharpe_ratio,
                        "win_rate": r.win_rate,
                        "trades": r.num_trades,
                        "max_dd": r.max_drawdown,
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows).sort_values("return_pct", ascending=False))


def page_ai():
    st.header("AI Analysis")
    st.info(
        "The LLM provides research and recommendations only. "
        "It cannot place trades. All orders pass through the risk manager."
    )
    api_configured = bool(settings.openai_api_key or settings.anthropic_api_key)
    st.metric("LLM Available", "Yes" if api_configured else "No — set API key in .env")
    symbol = st.text_input("Symbol for analysis", "SPY")
    strategy_name = st.selectbox("Strategy", list_strategies(), key="ai_strat")
    if st.button("Run AI Review") and api_configured:
        from ai.signal_analyzer import SignalAnalyzer

        hist = HistoricalDataEngine()
        df = hist.reload(symbol, "STK", "5 mins")
        if df.empty:
            st.error("No data")
            return
        strategy = get_strategy(strategy_name, symbol)
        signal = strategy.run(df)
        if not signal:
            st.warning("No signal at current bar")
            return
        backtest = BacktestEngine().run(strategy, df)
        review = SignalAnalyzer().analyze(signal, {"symbol": symbol, "bars": len(df)}, backtest)
        st.json(review.model_dump())


def page_risk():
    st.header("Risk Settings")
    st.json(
        {
            "max_risk_per_trade_pct": settings.max_risk_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_open_positions": settings.max_open_positions,
            "min_reward_to_risk": settings.min_reward_to_risk,
            "min_model_confidence": settings.min_model_confidence,
            "paper_trading": settings.paper_trading_enabled,
            "live_trading": settings.live_trading_enabled,
        }
    )
    st.warning("Edit .env file to change risk parameters. Live trading requires LIVE_TRADING_ENABLED=true.")


def page_paper():
    st.header("Paper Trading")
    st.caption("Executes through IBKR paper account after risk checks")
    symbol = st.text_input("Symbol", "SPY", key="paper_sym")
    strategy_name = st.selectbox("Strategy", list_strategies(), key="paper_strat")
    if st.button("Run Trade Pipeline"):
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "app" / "main.py"),
                "trade",
                symbol,
                "--strategy",
                strategy_name,
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        st.code(result.stdout + result.stderr)


def main():
    init_db()
    st.sidebar.title("IBKR LLM Assistant")
    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Data", "Backtest", "Strategies", "AI", "Risk", "Paper Trade"],
    )
    pages = {
        "Overview": page_overview,
        "Data": page_data,
        "Backtest": page_backtest,
        "Strategies": page_strategies,
        "AI": page_ai,
        "Risk": page_risk,
        "Paper Trade": page_paper,
    }
    pages[page]()


if __name__ == "__main__":
    main()
