import numpy as np
import pandas as pd
import pytest

from app.backtest import backtest, evaluate, run_strategy, split


def make_prices(values):
    days = pd.date_range("2020-01-01", periods=len(values), freq="B")
    return pd.DataFrame({"close": values}, index=days)


def trending_prices(n=800, drift=0.0005, seed=0):
    rng = np.random.default_rng(seed)
    steps = rng.normal(drift, 0.01, n)
    return make_prices(100 * np.exp(np.cumsum(steps)))


def test_fast_window_must_be_shorter():
    with pytest.raises(ValueError):
        run_strategy(trending_prices(300), fast=50, slow=20)


def test_position_never_uses_same_day_signal():
    """The position on day N must come from the signal on day N-1."""
    frame = run_strategy(trending_prices(400), 10, 50)
    shifted = frame["signal"].shift(1).fillna(0)
    assert frame["position"].equals(shifted)


def test_flat_prices_produce_no_return():
    frame = run_strategy(make_prices([100.0] * 400), 10, 50)
    assert evaluate(frame).total_return == pytest.approx(0.0, abs=1e-9)


def test_split_is_contiguous_and_ordered():
    prices = trending_prices(500)
    train, test = split(prices, 0.7)
    assert len(train) + len(test) == len(prices)
    assert train.index[-1] < test.index[0]


def test_optimisation_never_sees_test_data():
    """
    Changing only the test half must not change the chosen parameters —
    if it does, information is leaking from the test set into the search.
    """
    prices = trending_prices(900)
    first = backtest(prices)["parameters"]

    altered = prices.copy()
    cut = int(len(altered) * 0.7)
    altered.iloc[cut:, 0] = altered.iloc[cut:, 0] * 1.5

    assert backtest(altered)["parameters"] == first


def test_drawdown_is_never_positive():
    result = evaluate(run_strategy(trending_prices(600), 20, 100))
    assert result.max_drawdown <= 0


def test_backtest_reports_both_periods():
    result = backtest(trending_prices(900))
    assert set(result) >= {"in_sample", "out_of_sample", "buy_and_hold", "parameters"}
    assert result["out_of_sample"]["days"] > 0
    assert len(result["equity_curve"]) > 0


def test_short_history_is_rejected():
    with pytest.raises(ValueError):
        backtest(trending_prices(120))
