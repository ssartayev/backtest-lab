"""Download daily prices and store them, skipping days already saved."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from .db import Price, get_session, init_db


def load_prices(symbol: str, start: str = "2018-01-01") -> int:
    """Fetch from Yahoo Finance and insert only the missing days."""
    import yfinance as yf

    init_db()
    frame = yf.download(
        symbol, start=start, progress=False, auto_adjust=True, multi_level_index=False
    )
    if frame is None or frame.empty:
        raise ValueError(f"No price data returned for {symbol}.")

    frame = frame.reset_index()
    frame.columns = [str(c).lower() for c in frame.columns]

    with get_session() as session:
        existing = {
            row[0]
            for row in session.execute(
                select(Price.day).where(Price.symbol == symbol)
            )
        }
        added = 0
        for record in frame.to_dict("records"):
            day = pd.Timestamp(record["date"]).date()
            if day in existing:
                continue
            session.add(
                Price(
                    symbol=symbol,
                    day=day,
                    open=float(record["open"]),
                    high=float(record["high"]),
                    low=float(record["low"]),
                    close=float(record["close"]),
                    volume=float(record.get("volume") or 0),
                )
            )
            added += 1
        session.commit()
    return added


def read_prices(symbol: str) -> pd.DataFrame:
    """Read one symbol's history back out of the database, oldest first."""
    with get_session() as session:
        rows = session.execute(
            select(Price.day, Price.close)
            .where(Price.symbol == symbol)
            .order_by(Price.day)
        ).all()

    if not rows:
        raise ValueError(f"No stored data for {symbol}. Load it first.")

    frame = pd.DataFrame(rows, columns=["day", "close"])
    frame["day"] = pd.to_datetime(frame["day"])
    return frame.set_index("day")
