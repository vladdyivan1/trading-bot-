# TradingView Webhook Setup (SPY 0DTE System)

## 1) Add script to chart
1. Open a SPY chart in TradingView.
2. Open **Pine Editor** and paste `pine/spy_0dte_scalper.pine`.
3. Click **Add to chart**.

## 2) Create alert
1. Click **Alerts** -> **Create Alert**.
2. Condition: select the loaded strategy.
3. Trigger: **Order fills and alert() function calls**.
4. Expiration: set according to your trading session preference.
5. In **Webhook URL**, enter your backend URL:
   - Local: `http://localhost:8000/webhook/tradingview`
   - Cloud: `https://<your-domain>/webhook/tradingview`

## 3) Alert message
- Use the JSON emitted from `alert()` / `alert_message` in the Pine strategy.
- Keep message format as valid JSON (required by TradingView webhook integrations).
- If you use a static template for manual alerts, start from `docs/tradingview_alert_template.json`.

## 4) Secret header (recommended)
- Configure your webhook relay or gateway to send `X-Webhook-Secret`.
- Set `WEBHOOK_SECRET` in `.env`.

## 5) Verify delivery
1. Start backend and open `/dashboard`.
2. Trigger a test alert from TradingView.
3. Check `/dashboard-api/alerts` for decision payload and rejection/approval reason.
