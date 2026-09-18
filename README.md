# Backtest Lab

Tests a moving-average trading strategy on real price history — tuning it on old
data and scoring it on data the tuning never saw.

The point of the project is not the strategy. It is measuring the strategy
**honestly**, because a backtest is very easy to accidentally rig in your own
favour.

## The result on AAPL, 2015–2026

| | Total return | Sharpe | Max drawdown |
|---|---|---|---|
| In-sample *(parameters tuned here)* | **+354%** | 1.05 | −24.6% |
| Out-of-sample *(never seen while tuning)* | **+15%** | 0.32 | −22.3% |
| Buy and hold *(same period)* | +131% | 1.05 | −33.4% |

The strategy looks excellent on the period it was fitted to, and then **loses to
simply holding the stock** on fresh data.

That gap is the finding. Reporting only the first row would have looked far more
impressive and been worthless.

## The two ways a backtest lies

**1. Lookahead bias — using information you could not have had.**

The signal is computed from a day's closing price, so it cannot be acted on until
the following day. Positions are shifted one day forward:

```python
frame["signal"] = (frame["fast_ma"] > frame["slow_ma"]).astype(int)
frame["position"] = frame["signal"].shift(1).fillna(0)   # trade tomorrow
```

Without that `shift(1)`, the backtest buys using a price it has not seen yet, and
the returns become fiction.

**2. Overfitting — tuning and testing on the same data.**

History is split 70/30. Every parameter combination is searched on the first 70%
only, and the reported result comes from the last 30%. A test enforces this:

```python
def test_optimisation_never_sees_test_data():
    """Changing only the test half must not change the chosen parameters."""
```

If altering the test period changed which parameters were picked, information
would be leaking backwards — so it is asserted, not assumed.

## Stack

**Backend** FastAPI · SQLAlchemy · pandas · NumPy · pytest
**Frontend** React 19 · TypeScript · Recharts · Vite
**Data** Daily prices from Yahoo Finance, stored locally

SQLAlchemy is used instead of raw `sqlite3` so the same code runs against
PostgreSQL by changing `DATABASE_URL` alone. Prices are inserted once and reused,
so repeated backtests never re-download.

## Metrics

- **Total return** — growth over the period
- **Sharpe ratio** — return per unit of volatility, annualised (higher is better)
- **Max drawdown** — worst peak-to-trough fall, i.e. the loss you had to sit through
- **Trades** — how often the position changed

## Running it

**Backend**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**Tests**

```bash
cd backend && python -m pytest
```

## Layout

```
backend/
  app/backtest.py   strategy, train/test split, metrics
  app/data.py       download and store prices
  app/db.py         SQLAlchemy models
  app/main.py       FastAPI routes
  tests/            8 tests, including the no-leakage check
frontend/
  src/App.tsx       controls, stat cards, equity chart
```

## Limits

- One strategy family (moving-average crossover).
- No trading costs or slippage, so real returns would be lower — with 39 trades
  out of sample, commissions would matter.
- A single 70/30 split rather than walk-forward testing across multiple windows.
- Daily data only; nothing intraday.
