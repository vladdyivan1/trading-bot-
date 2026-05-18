# ibkr-llm-trading-assistant

        Production-quality MVP for a **safe, modular, LLM-assisted automated trading system** with Interactive Brokers.

        > Safety-first design: the LLM never places orders directly. Deterministic Python code handles validation, risk, and execution.

        ## Features (MVP)

        - Interactive Brokers connectivity via `ib_insync` (IB Gateway / TWS)
        - Historical data pull (up to 5 years where available) and SQLite caching
        - Deterministic strategy framework and backtesting engine
        - Risk manager with hard guardrails and kill switch
        - Paper trading execution engine (live disabled by default)
        - LLM assistant for setup review, trade review, and strategy suggestions
        - Predictive modeling module with walk-forward training
        - Streamlit dashboard for operations and monitoring
        - SQLAlchemy persistence for bars, signals, backtests, trades, and LLM outputs

        ## Project structure

        ```
        ibkr-llm-trading-assistant/
          README.md
          requirements.txt
          .env.example
          config/
            settings.py
          app/
            main.py
            dashboard.py
          broker/
            ibkr_client.py
            contracts.py
            orders.py
            account.py
          data/
            historical_data.py
            market_data.py
            data_store.py
          strategies/
            base_strategy.py
            moving_average_strategy.py
            rsi_strategy.py
            breakout_strategy.py
            strategy_registry.py
          backtesting/
            engine.py
            metrics.py
            walk_forward.py
          ai/
            llm_client.py
            prompts.py
            signal_analyzer.py
            trade_reviewer.py
            strategy_optimizer.py
          models/
            feature_engineering.py
            predictive_model.py
            model_training.py
          risk/
            risk_manager.py
            position_sizing.py
            kill_switch.py
          execution/
            paper_trader.py
            live_trader.py
            execution_engine.py
          database/
            db.py
            models.py
            repositories.py
          logs/
          tests/
        ```

        ## Installation

        1. Use Python 3.11+
2. Create and activate a virtual environment
3. Install dependencies:

        ```bash
        pip install -r requirements.txt
        ```

        ## Environment setup

        1. Copy `.env.example` to `.env`
2. Fill in IBKR and LLM credentials
3. Keep safety defaults:
   - `PAPER_TRADING_ONLY=true`
   - `LIVE_TRADING_ENABLED=false`

        ## Connect IB Gateway/TWS (paper)

        - Start IB Gateway or TWS paper account
        - Ensure API is enabled (socket connections)
        - Typical paper ports:
          - TWS paper: `7497`
          - IB Gateway paper: `4002` (configure if needed)
        - Update `.env` values (`IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`)

        ## Initialize DB

        ```bash
        python -c "from database.db import init_db; init_db()"
        ```

        ## Download historical data

        Use CLI with IBKR connection enabled:

        ```bash
        python app/main.py --connect --symbol SPY --asset-class STK --timeframe "1 day" --years 5
        ```

        For forex:

        ```bash
        python app/main.py --connect --symbol EURUSD --asset-class FX --timeframe "1 hour" --years 3
        ```

        Downloaded candles are cached in SQLite and can be reused without re-pulling.

        ## Run backtests

        ```bash
        python app/main.py --symbol SPY --asset-class STK --timeframe "1 day" --strategy moving_average_crossover
        ```

        Backtest metrics include:

        - Total return
        - CAGR
        - Win rate
        - Profit factor
        - Max drawdown
        - Average win/loss
        - Expectancy
        - Sharpe ratio
        - Sortino ratio
        - Number of trades
        - Average hold time

        ## Run paper trade (validated only)

        ```bash
        python app/main.py --connect --auto-paper-trade --symbol SPY --asset-class STK --timeframe "5 mins"
        ```

        Flow:

        1. Strategy proposes structured signal
        2. Backtest + market summary context generated
        3. LLM returns structured JSON analysis
        4. **Risk manager enforces hard limits**
        5. Execution engine submits paper order only if all checks pass

        ## Streamlit dashboard

        ```bash
        streamlit run app/dashboard.py
        ```

        Dashboard sections:

        - IBKR connection status + account summary
        - Historical downloader
        - Backtest runner + equity curve
        - AI analysis panel
        - Trade log
        - Risk settings + kill switch

        ## LLM layer behavior

        The LLM receives market summaries, signal context, backtest metrics, and/or trade logs.
It must return JSON-only structured analysis and suggestions.

        The LLM can:

        - Score setup quality
        - Explain risks
        - Suggest conservative parameter experiments
        - Review losing trades

        The LLM **cannot**:

        - Place orders
        - Override risk manager limits
        - Enable live trading

        ## Why live trading is disabled by default

        This MVP is intentionally conservative:

        - `paper_trading_only` defaults to true
        - `live_trading_enabled` defaults to false
        - Risk checks are deterministic and blocking
        - Kill switch can immediately block all execution

        ## Safely enabling live trading later

        Only after extensive paper validation, model monitoring, and operational controls:

        1. Verify stable out-of-sample performance and drawdown controls
        2. Add broker-grade observability, reconciliation, and alerts
        3. Test failover and incident playbooks
        4. Explicitly set:
           - `PAPER_TRADING_ONLY=false`
           - `LIVE_TRADING_ENABLED=true`
        5. Keep human approvals and staged rollout limits

        ## Tests

        Run:

        ```bash
        pytest -q
        ```

        Included tests cover:

        - Backtest calculations
        - Risk manager blocking logic
        - Strategy signal generation
        - Position sizing
        - Data validation

        ## Development roadmap

        - **Phase 1:** structure, IBKR connection, historical data, SQLite, strategy, backtesting
        - **Phase 2:** risk manager, paper trading, dashboard, trade logging
        - **Phase 3:** LLM assistant, predictive model, strategy performance review
        - **Phase 4:** options/futures expansion, portfolio risk, optimization
