import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BacktestResult, Performance } from "./types";
import "./App.css";

const API = "http://127.0.0.1:8000";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function Stats({ title, data, note }: { title: string; data: Performance; note?: string }) {
  return (
    <div className="stats">
      <h3>{title}</h3>
      {note && <p className="note">{note}</p>}
      <dl>
        <div><dt>Total return</dt><dd>{pct(data.total_return)}</dd></div>
        <div><dt>Sharpe ratio</dt><dd>{data.sharpe.toFixed(2)}</dd></div>
        <div><dt>Max drawdown</dt><dd>{pct(data.max_drawdown)}</dd></div>
        <div><dt>Trades</dt><dd>{data.trades}</dd></div>
      </dl>
    </div>
  );
}

export default function App() {
  const [symbol, setSymbol] = useState("AAPL");
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function post(path: string, body: unknown) {
    const response = await fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}));
      throw new Error(detail.detail ?? `Request failed (${response.status})`);
    }
    return response.json();
  }

  async function run() {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setStatus(`Loading price history for ${symbol.toUpperCase()}…`);
      await post("/api/load", { symbol, start: "2015-01-01" });
      setStatus("Running the backtest…");
      setResult(await post("/api/backtest", { symbol, train_fraction: 0.7 }));
      setStatus("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  const beatsMarket =
    result && result.out_of_sample.total_return > result.buy_and_hold.total_return;

  return (
    <div className="page">
      <header>
        <h1>Backtest Lab</h1>
        <p className="sub">
          Tests a moving-average strategy, tuning it on old data and scoring it on
          data the tuning never saw.
        </p>
      </header>

      <div className="controls">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="Ticker, e.g. AAPL"
          maxLength={8}
        />
        <button className="btn" onClick={run} disabled={busy || !symbol.trim()}>
          {busy ? "Working…" : "Run backtest"}
        </button>
      </div>

      {status && <p className="status">{status}</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <p className="params">
            Best parameters found on the training period:{" "}
            <strong>{result.parameters.fast}-day</strong> vs{" "}
            <strong>{result.parameters.slow}-day</strong> moving average.
          </p>

          <div className="grid">
            <Stats
              title="In-sample"
              data={result.in_sample}
              note="Tuned on this period — flattering by construction"
            />
            <Stats
              title="Out-of-sample"
              data={result.out_of_sample}
              note="Never seen during tuning — the honest number"
            />
            <Stats
              title="Buy and hold"
              data={result.buy_and_hold}
              note="Same period, no trading at all"
            />
          </div>

          <div className={`verdict ${beatsMarket ? "good" : "bad"}`}>
            {beatsMarket
              ? "Out of sample, the strategy beat buying and holding."
              : "Out of sample, the strategy lost to simply buying and holding — the in-sample result was largely overfitting."}
          </div>

          <div className="chart">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={result.equity_curve}>
                <CartesianGrid stroke="#243040" strokeDasharray="3 3" />
                <XAxis dataKey="day" stroke="#8b9bb0" fontSize={11} minTickGap={50} />
                <YAxis stroke="#8b9bb0" fontSize={11} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{
                    background: "#141b23",
                    border: "1px solid #243040",
                    borderRadius: 8,
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="strategy"
                  stroke="#60a5fa"
                  dot={false}
                  name="Strategy"
                />
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="#8b9bb0"
                  dot={false}
                  name="Buy and hold"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
