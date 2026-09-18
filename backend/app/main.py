"""FastAPI service: load price history and run backtests against it."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .backtest import backtest
from .data import load_prices, read_prices
from .db import init_db, row_count, symbols_in_db

app = FastAPI(title="Backtest Lab")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class LoadRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    start: str = "2018-01-01"


class BacktestRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    train_fraction: float = Field(default=0.7, ge=0.4, le=0.9)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/symbols")
def list_symbols() -> dict:
    return {
        "symbols": [
            {"symbol": s, "rows": row_count(s)} for s in symbols_in_db()
        ]
    }


@app.post("/api/load")
def load(request: LoadRequest) -> dict:
    symbol = request.symbol.upper().strip()
    try:
        added = load_prices(symbol, request.start)
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
    return {"symbol": symbol, "rows_added": added, "rows_total": row_count(symbol)}


@app.post("/api/backtest")
def run(request: BacktestRequest) -> dict:
    symbol = request.symbol.upper().strip()
    try:
        prices = read_prices(symbol)
        result = backtest(prices, request.train_fraction)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    result["symbol"] = symbol
    return result
