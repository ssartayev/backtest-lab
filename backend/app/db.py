"""
Database layer. SQLAlchemy is used rather than raw sqlite3 so the same code
runs against PostgreSQL by changing DATABASE_URL alone.
"""
from __future__ import annotations

import os
from datetime import date

from sqlalchemy import (
    Date,
    Float,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/prices.db")

engine = create_engine(DATABASE_URL, future=True)


class Base(DeclarativeBase):
    pass


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("symbol", "day", name="uq_symbol_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


def init_db() -> None:
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine, future=True)


def symbols_in_db() -> list[str]:
    with get_session() as session:
        rows = session.execute(select(Price.symbol).distinct().order_by(Price.symbol))
        return [row[0] for row in rows]


def row_count(symbol: str) -> int:
    from sqlalchemy import func

    with get_session() as session:
        return session.execute(
            select(func.count()).select_from(Price).where(Price.symbol == symbol)
        ).scalar_one()
