"""Streamlit dashboard for trading assistant MVP."""

from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from ai.signal_analyzer import SignalAnalyzer
from backtesting.engine import BacktestEngine
from broker.contracts import ContractSpec
from broker.ibkr_client import IBKRClient
from config.settings import get_settings
from data.historical_data import HistoricalDataEngine
from data.market_data import summarize_market_data
from database.db import init_db
from database.repositories import TradeRepository
from risk.kill_switch import KillSwitch
from strategies.strategy_registry import available_strategies, build_strategy


st.set_page_config(page_title="IBKR LLM Trading Assistant", layout="wide")
st.title("IBKR LLM Trading Assistant - MVP")

settings = get_settings()
init_db()

if "ibkr_client" not in st.session_state:
    st.session_state.ibkr_client = IBKRClient(settings=settings)
if "kill_switch" not in st.session_state:
    st.session_state.kill_switch = KillSwitch()

ibkr_client: IBKRClient = st.session_state.ibkr_client

tabs = st.tabs(["Connection", "Data", "Backtest", "AI Analysis", "Trade Log", "Risk"])

with tabs[0]:
    st.subheader("IBKR Connection Status")
    st.write(f"Connected: {ibkr_client.is_connected()}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect to IBKR"):
            try:
                ibkr_client.connect()
                st.success("Connected")
            except Exception as exc:
                st.error(str(exc))
    with col2:
        if st.button("Disconnect"):
            ibkr_client.disconnect()
            st.info("Disconnected")

    if ibkr_client.is_connected():
        try:
            st.json(ibkr_client.get_account_summary())
        except Exception as exc:
            st.warning(f"Unable to fetch account summary: {exc}")

with tabs[1]:
    st.subheader("Historical Data Downloader")
    symbol = st.text_input("Symbol", value="SPY")
    asset_class = st.selectbox("Asset class", ["STK", "ETF", "FX", "FUT", "OPT"], index=0)
    timeframe = st.selectbox("Timeframe", ["1 min", "5 mins", "15 mins", "1 hour", "1 day"], index=4)
    years = st.slider("Years", min_value=1, max_value=5, value=2)

    if st.button("Download / Refresh data"):
        if not ibkr_client.is_connected():
            st.error("Connect to IBKR first")
        else:
            engine = HistoricalDataEngine(ibkr_client=ibkr_client)
            contract = ContractSpec(symbol=symbol, asset_class=asset_class)
            bars = engine.load_or_fetch(contract, timeframe=timeframe, years=years, force_refresh=True)
            st.session_state["bars"] = bars
            st.success(f"Loaded {len(bars)} candles")

    bars = st.session_state.get("bars", pd.DataFrame())
    if not bars.empty:
        st.dataframe(bars.tail(100))

with tabs[2]:
    st.subheader("Backtest Runner")
    strategy_name = st.selectbox("Strategy", available_strategies())
    bars = st.session_state.get("bars", pd.DataFrame())
    if st.button("Run backtest"):
        if bars.empty:
            st.error("Load data first")
        else:
            strategy = build_strategy(strategy_name)
            bt_engine = BacktestEngine()
            result = bt_engine.run(strategy, bars, symbol="SYMB", asset_class="STK", timeframe="1 day")
            st.session_state["backtest"] = result
            st.json(result.metrics)

            fig = px.line(result.equity_curve, y="equity", title="Equity Curve")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(result.trades.tail(50))

with tabs[3]:
    st.subheader("AI Analysis Panel")
    backtest = st.session_state.get("backtest")
    bars = st.session_state.get("bars", pd.DataFrame())
    if st.button("Analyze latest setup"):
        if backtest is None or bars.empty:
            st.error("Run a backtest first")
        else:
            strategy = build_strategy(strategy_name)
            signal = strategy.generate_signal(bars, symbol="SPY", asset_class="STK", timeframe="1 day")
            if signal is None:
                st.warning("No signal generated")
            else:
                analyzer = SignalAnalyzer()
                review = analyzer.review_signal(signal, summarize_market_data(bars), backtest.metrics)
                st.json(review.model_dump(mode="json"))

with tabs[4]:
    st.subheader("Trade Log")
    repo = TradeRepository()
    rows = repo.list_recent(limit=300)
    if rows:
        df = pd.DataFrame(
            [
                {
                    "id": r.id,
                    "created_at": r.created_at,
                    "symbol": r.symbol,
                    "strategy": r.strategy_name,
                    "direction": r.direction,
                    "qty": r.quantity,
                    "status": r.status,
                    "order_id": r.order_id,
                    "reason": r.reason,
                }
                for r in rows
            ]
        )
        st.dataframe(df)
    else:
        st.info("No trades logged yet")

with tabs[5]:
    st.subheader("Risk Settings & Kill Switch")
    st.write(
        {
            "paper_trading_only": settings.paper_trading_only,
            "live_trading_enabled": settings.live_trading_enabled,
            "max_risk_per_trade_pct": settings.max_risk_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_open_positions": settings.max_open_positions,
            "min_reward_risk": settings.min_reward_risk,
            "min_model_confidence": settings.min_model_confidence,
        }
    )
    if st.button("Trigger Kill Switch"):
        st.session_state.kill_switch.trigger("Triggered from dashboard")
    if st.button("Reset Kill Switch"):
        st.session_state.kill_switch.reset()

    st.code(json.dumps({"kill_switch": st.session_state.kill_switch.enabled, "reason": st.session_state.kill_switch.reason}, indent=2))
