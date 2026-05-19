"""Streamlit dashboard for the trading assistant."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.signal_analyzer import SignalAnalyzer
from ai.strategy_optimizer import StrategyOptimizer
from backtesting.engine import BacktestEngine
from broker.ibkr_client import IBKRClient
from config.settings import get_settings
from data.data_store import DataStore
from data.historical_data import HistoricalDataService
from database.db import get_session
from database.repositories import StrategyPerformanceRepository, TradeRepository
from execution.execution_engine import ExecutionEngine
from risk.kill_switch import KillSwitch
from risk.risk_manager import RiskManager
from strategies.strategy_registry import get_strategy, list_strategies

st.set_page_config(page_title="IBKR LLM Trading Assistant", layout="wide")
settings = get_settings()

st.title("IBKR LLM Trading Assistant")
st.caption("Paper trading by default · LLM does not place orders · Live trading disabled")

tab_conn, tab_data, tab_bt, tab_ai, tab_exec, tab_risk = st.tabs(
    ["Connection", "Data", "Backtest", "AI Analysis", "Paper Trading", "Risk"]
)

if "client" not in st.session_state:
    st.session_state.client = IBKRClient()
if "risk" not in st.session_state:
    st.session_state.risk = RiskManager()

with tab_conn:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("IBKR Connection")
        host = st.text_input("Host", settings.ibkr_host)
        port = st.number_input("Port", value=settings.ibkr_port)
        client_id = st.number_input("Client ID", value=settings.ibkr_client_id)
    with col2:
        st.metric("Paper Mode", "ON" if settings.paper_trading else "OFF")
        st.metric("Live Trading", "ENABLED" if settings.live_trading_enabled else "DISABLED")
        connected = st.session_state.client.is_connected
        st.metric("Status", "Connected" if connected else "Disconnected")

    if st.button("Connect"):
        settings.ibkr_host = host
        settings.ibkr_port = int(port)
        settings.ibkr_client_id = int(client_id)
        ok = st.session_state.client.connect()
        st.success("Connected") if ok else st.error("Connection failed — is IB Gateway running?")

    if st.session_state.client.is_connected:
        summary = st.session_state.client.account_summary()
        st.json(summary)
        positions = st.session_state.client.positions()
        if not positions.empty:
            st.dataframe(positions)

with tab_data:
    symbol = st.text_input("Symbol", "SPY", key="dl_sym")
    timeframe = st.selectbox("Timeframe", ["1 min", "5 mins", "15 mins", "1 hour", "1 day"])
    asset_class = st.selectbox("Asset Class", ["STK", "ETF", "CASH"], key="dl_ac")
    years = st.slider("Years", 1, 5, 5)
    if st.button("Download Historical Data"):
        with st.spinner("Downloading..."):
            svc = HistoricalDataService(st.session_state.client)
            df = svc.download(symbol, timeframe, asset_class, years=years, force_refresh=True)
            st.success(f"Stored {len(df)} bars")
    store = DataStore()
    cached = store.load(symbol, timeframe, asset_class)
    st.write(f"Cached bars: {len(cached)}")
    if not cached.empty:
        col = "close" if "close" in cached.columns else "Close"
        fig = go.Figure(go.Scatter(x=cached.index, y=cached[col], name=symbol))
        fig.update_layout(title=f"{symbol} {timeframe}", height=400)
        st.plotly_chart(fig, use_container_width=True)

with tab_bt:
    bt_symbol = st.text_input("Backtest Symbol", "SPY", key="bt_sym")
    strategy_name = st.selectbox("Strategy", list_strategies())
    bt_timeframe = st.selectbox("BT Timeframe", ["1 day", "1 hour", "5 mins"], key="bt_tf")
    if st.button("Run Backtest"):
        df = DataStore().load(bt_symbol, bt_timeframe)
        if df.empty:
            st.warning("No data — download first or use synthetic test data via CLI.")
        else:
            if "close" not in df.columns:
                df = df.rename(columns={c: c.lower() for c in df.columns})
            strat = get_strategy(strategy_name, {"symbol": bt_symbol, "timeframe": bt_timeframe})
            result = BacktestEngine().run(strat, df, bt_symbol)
            m = result.metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Return", f"{m.total_return:.2%}")
            c2.metric("Sharpe", f"{m.sharpe_ratio:.2f}")
            c3.metric("Max DD", f"{m.max_drawdown:.2%}")
            c4.metric("Trades", m.num_trades)
            st.dataframe(
                pd.DataFrame([m.model_dump()]),
                use_container_width=True,
            )
            if len(result.equity_curve) > 1:
                fig_eq = go.Figure(go.Scatter(y=result.equity_curve.values, name="Equity"))
                st.plotly_chart(fig_eq, use_container_width=True)
            if not result.trades.empty:
                st.subheader("Trade Log")
                st.dataframe(result.trades)

    st.subheader("Strategy Comparison")
    if st.button("Compare All Strategies"):
        cmp_df = DataStore().load(bt_symbol, bt_timeframe)
        if cmp_df.empty:
            st.warning("No data — download first.")
        else:
            if "close" not in cmp_df.columns:
                cmp_df = cmp_df.rename(columns={c: c.lower() for c in cmp_df.columns})
            from strategies.strategy_registry import _REGISTRY

            strats = [cls({"symbol": bt_symbol}) for cls in _REGISTRY.values()]
            comp = BacktestEngine().compare_strategies(strats, cmp_df, bt_symbol)
            st.dataframe(comp)

with tab_ai:
    ai_symbol = st.text_input("AI Symbol", "SPY", key="ai_sym")
    ai_strategy = st.selectbox("AI Strategy", list_strategies(), key="ai_strat")
    if st.button("Run LLM Analysis"):
        df = DataStore().load(ai_symbol, "1 day")
        if df.empty:
            st.error("No data")
        else:
            signal = get_strategy(ai_strategy, {"symbol": ai_symbol}).generate_signal(df)
            if not signal:
                st.info("No active signal")
            else:
                st.json(signal.model_dump_json_safe())
                rec = SignalAnalyzer().analyze(signal)
                st.json(rec.model_dump())
    st.subheader("Strategy Rankings")
    with get_session() as session:
        rankings = StrategyPerformanceRepository(session).get_rankings(10)
    if rankings:
        st.dataframe(pd.DataFrame([r.__dict__ for r in rankings]))
    else:
        st.info("No performance history yet")

with tab_exec:
    st.warning("Execution requires IBKR paper connection and risk approval")
    ex_symbol = st.text_input("Trade Symbol", "SPY", key="ex_sym")
    ex_strategy = st.selectbox("Trade Strategy", list_strategies(), key="ex_strat")
    skip_llm = st.checkbox("Skip LLM (testing only)")
    if st.button("Execute Paper Trade Pipeline"):
        df = DataStore().load(ex_symbol, "1 day")
        if df.empty:
            st.error("No data")
        else:
            strat = get_strategy(ex_strategy, {"symbol": ex_symbol})
            signal = strat.generate_signal(df)
            if not signal:
                st.info("No signal")
            else:
                bt = BacktestEngine().run(strat, df, ex_symbol)
                engine = ExecutionEngine(risk_manager=st.session_state.risk)
                result = engine.process_signal(
                    signal,
                    backtest_metrics=bt.metrics.model_dump(),
                    backtest_trades=bt.metrics.num_trades,
                    skip_llm=skip_llm,
                )
                st.json(result)
    with get_session() as session:
        trades = TradeRepository(session)
        open_trades = trades.get_open_trades()
    st.write(f"Open trade logs: {len(open_trades)}")

with tab_risk:
    st.subheader("Risk Settings")
    st.json(
        {
            "max_risk_per_trade_pct": settings.max_risk_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_open_positions": settings.max_open_positions,
            "min_reward_to_risk": settings.min_reward_to_risk,
            "min_model_confidence": settings.min_model_confidence,
            "live_trading_enabled": settings.live_trading_enabled,
        }
    )
    equity = st.number_input("Account Equity", value=100_000.0)
    st.session_state.risk.update_equity(equity)

    ks = KillSwitch()
    if st.button("ACTIVATE KILL SWITCH", type="primary"):
        ks.activate()
        st.error("Kill switch activated — all trading halted")
    if st.button("Deactivate Kill Switch"):
        ks.deactivate()
        st.success("Kill switch deactivated")
