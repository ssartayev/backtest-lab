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

function Stats({
  title,
  subtitle,
  data,
  note,
}: {
  title: string;
  subtitle: string;
  data: Performance;
  note: string;
}) {
  return (
    <div className="stats">
      <h3>{title}</h3>
      <p className="subtitle">{subtitle}</p>
      <p className="note">{note}</p>
      <dl>
        <div>
          <dt>Money made<span>$100 would become ${(100 * (1 + data.total_return)).toFixed(0)}</span></dt>
          <dd>{pct(data.total_return)}</dd>
        </div>
        <div>
          <dt>Worst drop<span>the biggest fall along the way</span></dt>
          <dd>{pct(data.max_drawdown)}</dd>
        </div>
        <div>
          <dt>Smoothness<span>reward per unit of risk; above 1 is good</span></dt>
          <dd>{data.sharpe.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Times traded<span>how often it bought or sold</span></dt>
          <dd>{data.trades}</dd>
        </div>
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
          Would this rule for buying shares actually have made money?
        </p>
      </header>

      <section className="explainer">
        <h2>What this tests</h2>
        <p>
          <strong>The rule:</strong> watch two averages of a share price — a
          short one and a long one. Buy when the short average rises above the
          long one, sell when it falls back below. That is the whole strategy,
          and it is the only one tested here.
        </p>
        <p>
          <strong>The problem with testing it:</strong> if you keep adjusting the
          rule until it looks good on past prices, you have only made it fit
          those particular prices — like revising with the answer key in front of
          you. It then fails on prices it has not seen.
        </p>
        <p>
          <strong>So the history is cut in two.</strong> The rule is adjusted
          using the first 70% of the years, then scored on the last 30%, which
          the adjusting never touched. Both scores are shown below, because the
          gap between them is what tells you whether the rule is real.
        </p>
      </section>

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
            The computer chose the two averages itself, using only the practice
            years: a <strong>{result.parameters.fast}-day</strong> average
            against a <strong>{result.parameters.slow}-day</strong> average.
          </p>

          <div className="grid">
            <Stats
              title="Practice score"
              subtitle="In-sample"
              data={result.in_sample}
              note="The years the rule was adjusted on. Always flattering — ignore this number on its own."
            />
            <Stats
              title="Real test score"
              subtitle="Out-of-sample"
              data={result.out_of_sample}
              note="Years the rule had never seen. This is the number that counts."
            />
            <Stats
              title="Doing nothing"
              subtitle="Buy and hold"
              data={result.buy_and_hold}
              note="Buy on day one of the test years, never sell. The benchmark to beat."
            />
          </div>

          <div className={`verdict ${beatsMarket ? "good" : "bad"}`}>
            {beatsMarket ? (
              <>
                <strong>The rule worked.</strong> On years it had never seen, it
                made more than simply buying the shares and leaving them alone.
              </>
            ) : (
              <>
                <strong>The rule does not work.</strong> On years it had never
                seen it made less than simply buying the shares and leaving them
                alone — so the high practice score came from fitting the rule to
                the past, not from finding something real.
              </>
            )}
          </div>

          <div className="chart">
            <p className="chart-note">
              How $1 would have grown during the test years. Blue is the rule,
              grey is doing nothing — if blue sits below grey, the rule lost.
            </p>
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
