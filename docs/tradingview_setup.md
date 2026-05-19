# TradingView Webhook Setup

## 1. Add Pine strategy

1. Open TradingView → Pine Editor.
2. Paste `pine/spy_0dte_scalper.pine` and click **Add to chart**.
3. Apply chart to **SPY**, intraday timeframe (1m or 3m recommended).

## 2. Expose webhook endpoint

Run the backend locally or on a server with a **public HTTPS URL** (TradingView requires reachable webhooks).

- Local dev: use ngrok, Cloudflare Tunnel, or similar: `ngrok http 8000`
- Production: deploy Docker stack behind TLS terminator

Webhook URL format:

```text
https://YOUR_HOST/webhook/tradingview
```

## 3. Create alert

1. Right-click chart → **Add alert**.
2. Condition: **SPY 0DTE Scalper** → **Any alert() function call**.
3. Options:
   - **Once Per Bar Close** (matches `alert.freq_once_per_bar_close`)
   - Enable **Webhook URL** → paste your HTTPS endpoint
4. Message: use JSON from strategy `alert()` or customize with placeholders.

Example message (placeholders filled by TradingView at fire time):

```json
{
  "ticker": "{{ticker}}",
  "time": "{{timenow}}",
  "price": "{{close}}",
  "interval": "{{interval}}",
  "action": "{{strategy.order.action}}",
  "market_position": "{{strategy.market_position}}",
  "setup": "SPY_0DTE_SCALP",
  "bias": "bullish",
  "secret": "YOUR_WEBHOOK_SECRET"
}
```

Set `secret` to match `WEBHOOK_SECRET` in `.env`.

## 4. Important limitations

- Webhook URL is configured in the **alert dialog**, not in Pine source.
- Pine cannot call LLMs or external news APIs; all AI runs in this backend.
- Alert delivery is not guaranteed at HFT latency; design for seconds-level reaction.
- Options execution requires broker integration; default mode is **paper**.

## 5. Test

```bash
curl -X POST http://localhost:8000/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d @docs/alert_templates.json
```

(Use a single object from the template file, not the whole file.)
