"""HTML rendering for the built-in operational dashboard."""

from __future__ import annotations

import html


def render_dashboard(metrics: dict) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    rejection_rows = "".join(
        f"<tr><td>{esc(reason)}</td><td>{count}</td></tr>"
        for reason, count in metrics["rejection_reasons"].items()
    )
    time_rows = "".join(
        f"<tr><td>{esc(bucket)}</td><td>{data['trades']}</td><td>{data['pnl']:.2f}</td></tr>"
        for bucket, data in metrics["time_of_day"].items()
    )
    sentiment_rows = "".join(
        f"<tr><td>{esc(sentiment)}</td><td>{count}</td></tr>"
        for sentiment, count in metrics["sentiment_heatmap"].items()
    )
    regime_rows = "".join(
        f"<tr><td>{esc(regime)}</td><td>{count}</td></tr>"
        for regime, count in metrics["regime_counts"].items()
    )
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SPY 0DTE AI Scalper Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #172033; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }}
    .card {{ border: 1px solid #d9e2ec; border-radius: 8px; padding: 1rem; background: #f8fafc; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 0.75rem; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 0.5rem; text-align: left; }}
    th {{ background: #edf2f7; }}
  </style>
</head>
<body>
  <h1>SPY 0DTE AI Scalper</h1>
  <div class="grid">
    <div class="card"><strong>Alerts</strong><br>{metrics['alerts']}</div>
    <div class="card"><strong>Approved</strong><br>{metrics['approved']}</div>
    <div class="card"><strong>Rejected</strong><br>{metrics['rejected']}</div>
    <div class="card"><strong>Open Positions</strong><br>{metrics['open_positions']}</div>
    <div class="card"><strong>Closed Positions</strong><br>{metrics['closed_positions']}</div>
    <div class="card"><strong>PnL</strong><br>{metrics['pnl']:.2f}</div>
    <div class="card"><strong>Win Rate</strong><br>{metrics['win_rate']:.1%}</div>
    <div class="card"><strong>Max Drawdown</strong><br>{metrics['max_drawdown']:.2f}</div>
  </div>

  <h2>Rejection Reasons</h2>
  <table><tr><th>Reason</th><th>Count</th></tr>{rejection_rows}</table>

  <h2>0DTE Performance by Time of Day</h2>
  <table><tr><th>Hour ET</th><th>Trades</th><th>PnL</th></tr>{time_rows}</table>

  <h2>News Sentiment Heatmap</h2>
  <table><tr><th>Sentiment</th><th>Decisions</th></tr>{sentiment_rows}</table>

  <h2>Regime Analytics</h2>
  <table><tr><th>Regime</th><th>Decisions</th></tr>{regime_rows}</table>
</body>
</html>
"""
