"""
Moving-average crossover backtest with an honest train/test split.

Two mistakes make a backtest look far better than reality, and both are
avoided here deliberately:

1. **Lookahead bias.** Today's signal is computed from today's close, so it
   cannot be traded until the next day. Positions are shifted one day forward.

2. **Overfitting.** Parameters are searched on the training period only. The
   reported result is from the test period, which the search never saw. Both
   numbers are returned so the gap between them is visible: a large gap means
   the parameters were fitted to noise.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252
FAST_CHOICES = (5, 10, 20, 30)
SLOW_CHOICES = (50, 100, 150, 200)


@dataclass
class Performance:
    total_return: float
    annual_return: float
    sharpe: float
    max_drawdown: float
    trades: int
    days: int


def run_strategy(prices: pd.DataFrame, fast: int, slow: int) -> pd.DataFrame:
    if fast >= slow:
        raise ValueError("The fast window must be shorter than the slow window.")

    frame = prices.copy()
    frame["fast_ma"] = frame["close"].rolling(fast).mean()
    frame["slow_ma"] = frame["close"].rolling(slow).mean()

    # Hold the asset while the fast average is above the slow one.
    frame["signal"] = (frame["fast_ma"] > frame["slow_ma"]).astype(int)

    # The signal uses today's close, so the position can only start tomorrow.
    frame["position"] = frame["signal"].shift(1).fillna(0)

    frame["market_return"] = frame["close"].pct_change().fillna(0)
    frame["strategy_return"] = frame["position"] * frame["market_return"]
    frame["equity"] = (1 + frame["strategy_return"]).cumprod()
    return frame


def evaluate(frame: pd.DataFrame) -> Performance:
    returns = frame["strategy_return"].dropna()
    days = len(returns)
    if days == 0:
        return Performance(0.0, 0.0, 0.0, 0.0, 0, 0)

    equity = (1 + returns).cumprod()
    total = float(equity.iloc[-1] - 1)
    years = days / TRADING_DAYS
    annual = float((1 + total) ** (1 / years) - 1) if years > 0 and total > -1 else 0.0

    std = float(returns.std())
    sharpe = float(returns.mean() / std * np.sqrt(TRADING_DAYS)) if std > 0 else 0.0

    drawdown = float((equity / equity.cummax() - 1).min())
    trades = int(frame["position"].diff().abs().sum())

    return Performance(
        total_return=round(total, 4),
        annual_return=round(annual, 4),
        sharpe=round(sharpe, 3),
        max_drawdown=round(drawdown, 4),
        trades=trades,
        days=days,
    )


def split(prices: pd.DataFrame, train_fraction: float = 0.7):
    cut = int(len(prices) * train_fraction)
    return prices.iloc[:cut], prices.iloc[cut:]


def optimise(train: pd.DataFrame) -> tuple[int, int, float]:
    """Pick the parameters with the best Sharpe ratio on the training data only."""
    best = (FAST_CHOICES[0], SLOW_CHOICES[0], -np.inf)
    for fast in FAST_CHOICES:
        for slow in SLOW_CHOICES:
            if fast >= slow or slow >= len(train):
                continue
            sharpe = evaluate(run_strategy(train, fast, slow)).sharpe
            if sharpe > best[2]:
                best = (fast, slow, sharpe)
    return best


def backtest(prices: pd.DataFrame, train_fraction: float = 0.7) -> dict:
    train, test = split(prices, train_fraction)
    if len(test) < TRADING_DAYS // 4:
        raise ValueError("Not enough history for a meaningful out-of-sample test.")

    fast, slow, _ = optimise(train)

    train_result = run_strategy(train, fast, slow)
    test_result = run_strategy(test, fast, slow)

    # Buy and hold over the same test window, as the benchmark to beat.
    benchmark_returns = test["close"].pct_change().fillna(0)
    benchmark_frame = pd.DataFrame(
        {"strategy_return": benchmark_returns, "position": 1}
    )

    curve = (1 + test_result["strategy_return"].fillna(0)).cumprod()
    benchmark_curve = (1 + benchmark_returns).cumprod()

    return {
        "parameters": {"fast": fast, "slow": slow},
        "in_sample": asdict(evaluate(train_result)),
        "out_of_sample": asdict(evaluate(test_result)),
        "buy_and_hold": asdict(evaluate(benchmark_frame)),
        "equity_curve": [
            {
                "day": day.strftime("%Y-%m-%d"),
                "strategy": round(float(value), 4),
                "benchmark": round(float(benchmark_curve.loc[day]), 4),
            }
            for day, value in curve.items()
        ],
    }
