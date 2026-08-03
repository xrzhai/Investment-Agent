from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from harness.portfolio.models import (
    CashflowRecord,
    InstrumentMetadata,
    OptionContractRecord,
    PortfolioEvent,
    PositionRecord,
    QuoteRecord,
    SnapshotRecord,
    TradeResult,
)
from harness.portfolio.options import derive_open_put_metrics
from harness.settings import HarnessPaths


class PortfolioStore:
    """Transactional SQLite adapter for low-frequency portfolio facts."""

    def __init__(self, db_path: str | Path | None = None, paths: HarnessPaths | None = None):
        resolved_paths = paths or HarnessPaths.discover()
        self.db_path = Path(db_path).resolve() if db_path else resolved_paths.portfolio_db

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            yield conn
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    avg_cost REAL NOT NULL,
                    current_price REAL NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP,
                    target_bear REAL,
                    target_base REAL,
                    target_bull REAL,
                    prob_bear REAL,
                    prob_base REAL,
                    prob_bull REAL,
                    expected_cagr REAL,
                    time_horizon_months INTEGER,
                    sector TEXT,
                    region TEXT,
                    cap_style TEXT,
                    growth_value TEXT,
                    theme_tags TEXT,
                    risk_level TEXT,
                    ic_status TEXT,
                    meta_updated_at TIMESTAMP,
                    market TEXT NOT NULL DEFAULT 'US',
                    currency TEXT NOT NULL DEFAULT 'USD',
                    exchange TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_positions_symbol ON positions(symbol);

                CREATE TABLE IF NOT EXISTS option_contracts (
                    id INTEGER PRIMARY KEY,
                    underlying_symbol TEXT NOT NULL,
                    option_type TEXT NOT NULL DEFAULT 'put',
                    side TEXT NOT NULL DEFAULT 'short',
                    contracts INTEGER NOT NULL DEFAULT 1,
                    shares_per_contract INTEGER NOT NULL DEFAULT 100,
                    strike REAL NOT NULL,
                    expiry_date DATE NOT NULL,
                    opened_date DATE,
                    premium_per_share REAL NOT NULL DEFAULT 0,
                    premium_total REAL NOT NULL DEFAULT 0,
                    fees REAL NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'USD',
                    market TEXT NOT NULL DEFAULT 'US',
                    status TEXT NOT NULL DEFAULT 'open',
                    reserved_cash REAL NOT NULL DEFAULT 0,
                    net_cash_obligation REAL NOT NULL DEFAULT 0,
                    effective_entry_if_assigned REAL NOT NULL DEFAULT 0,
                    intent TEXT NOT NULL DEFAULT 'lower_price_entry',
                    notes TEXT NOT NULL DEFAULT '',
                    linked_decision_file TEXT NOT NULL DEFAULT '',
                    closed_date DATE,
                    assigned_date DATE,
                    assignment_price REAL,
                    realized_premium REAL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS ix_option_contracts_status ON option_contracts(status);
                CREATE INDEX IF NOT EXISTS ix_option_contracts_underlying ON option_contracts(underlying_symbol);

                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY,
                    snapshot_date DATE NOT NULL,
                    total_value REAL NOT NULL,
                    cash REAL NOT NULL DEFAULT 0,
                    daily_return_pct REAL NOT NULL DEFAULT 0,
                    max_drawdown_pct REAL NOT NULL DEFAULT 0,
                    top_position_weight REAL NOT NULL DEFAULT 0,
                    positions_json TEXT NOT NULL DEFAULT '{}',
                    notes TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_snapshots_date ON snapshots(snapshot_date);

                CREATE TABLE IF NOT EXISTS cashflow_events (
                    id INTEGER PRIMARY KEY,
                    event_date DATE NOT NULL,
                    amount_usd REAL NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS ix_cashflow_events_date ON cashflow_events(event_date);

                CREATE TABLE IF NOT EXISTS portfolio_events (
                    id INTEGER PRIMARY KEY,
                    event_id TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    occurred_at TIMESTAMP NOT NULL,
                    symbol TEXT,
                    payload_json TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_ref TEXT,
                    recorded_at TIMESTAMP NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_portfolio_events_time ON portfolio_events(occurred_at);
                CREATE INDEX IF NOT EXISTS ix_portfolio_events_symbol ON portfolio_events(symbol);

                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    as_of TIMESTAMP NOT NULL,
                    source TEXT NOT NULL,
                    source_ref TEXT,
                    recorded_at TIMESTAMP NOT NULL,
                    UNIQUE(symbol, as_of, source)
                );
                CREATE INDEX IF NOT EXISTS ix_quotes_symbol_time ON quotes(symbol, as_of DESC);

                CREATE TABLE IF NOT EXISTS instrument_metadata (
                    symbol TEXT PRIMARY KEY,
                    sector TEXT,
                    region TEXT,
                    cap_style TEXT,
                    growth_value TEXT,
                    theme_tags TEXT NOT NULL DEFAULT '[]',
                    risk_level TEXT,
                    source TEXT NOT NULL,
                    source_ref TEXT,
                    updated_at TIMESTAMP NOT NULL
                );
                """
            )
            conn.commit()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _row_value(row: sqlite3.Row, key: str, default=None):
        return row[key] if key in row.keys() and row[key] is not None else default

    @staticmethod
    def _market_currency(
        symbol: str,
        market: str | None = None,
        currency: str | None = None,
    ) -> tuple[str, str]:
        symbol = symbol.upper()
        inferred_currency = None
        if symbol.startswith("CASH_"):
            inferred_currency = symbol.removeprefix("CASH_")
        if symbol.endswith((".SH", ".SZ")):
            inferred_market = "CN_A"
            inferred_currency = inferred_currency or "CNY"
        elif symbol.endswith(".HK"):
            inferred_market = "HK"
            inferred_currency = inferred_currency or "HKD"
        elif inferred_currency == "CNY":
            inferred_market = "CN_A"
        elif inferred_currency == "HKD":
            inferred_market = "HK"
        else:
            inferred_market = "US"
            inferred_currency = inferred_currency or "USD"
        resolved_market = (market or inferred_market).upper()
        default_currency = "CNY" if resolved_market == "CN_A" else "HKD" if resolved_market == "HK" else inferred_currency
        return resolved_market, (currency or default_currency).upper()

    def list_positions(self) -> list[PositionRecord]:
        self.ensure_schema()
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT p.id, p.symbol, p.quantity, p.avg_cost, p.current_price, "
                "COALESCE(NULLIF(p.market,''), CASE WHEN p.symbol LIKE '%.SH' OR p.symbol LIKE '%.SZ' THEN 'CN_A' WHEN p.symbol LIKE '%.HK' THEN 'HK' ELSE 'US' END) AS market, "
                "COALESCE(NULLIF(p.currency,''), CASE WHEN p.symbol LIKE '%.SH' OR p.symbol LIKE '%.SZ' THEN 'CNY' WHEN p.symbol LIKE '%.HK' THEN 'HKD' ELSE 'USD' END) AS currency, "
                "p.exchange, p.updated_at, "
                "COALESCE(NULLIF(m.sector,''), p.sector) AS sector, COALESCE(NULLIF(m.region,''), p.region) AS region, "
                "COALESCE(NULLIF(m.cap_style,''), p.cap_style) AS cap_style, COALESCE(NULLIF(m.growth_value,''), p.growth_value) AS growth_value, "
                "COALESCE(NULLIF(m.theme_tags,''), p.theme_tags, '[]') AS theme_tags, COALESCE(NULLIF(m.risk_level,''), p.risk_level) AS risk_level "
                "FROM positions p LEFT JOIN instrument_metadata m ON m.symbol=p.symbol ORDER BY p.symbol"
            ).fetchall()
        return [PositionRecord.model_validate(dict(row)) for row in rows]

    def get_position(self, symbol: str) -> PositionRecord | None:
        self.ensure_schema()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT p.id, p.symbol, p.quantity, p.avg_cost, p.current_price, "
                "COALESCE(NULLIF(p.market,''), CASE WHEN p.symbol LIKE '%.SH' OR p.symbol LIKE '%.SZ' THEN 'CN_A' WHEN p.symbol LIKE '%.HK' THEN 'HK' ELSE 'US' END) AS market, "
                "COALESCE(NULLIF(p.currency,''), CASE WHEN p.symbol LIKE '%.SH' OR p.symbol LIKE '%.SZ' THEN 'CNY' WHEN p.symbol LIKE '%.HK' THEN 'HKD' ELSE 'USD' END) AS currency, "
                "p.exchange, p.updated_at, "
                "COALESCE(NULLIF(m.sector,''), p.sector) AS sector, COALESCE(NULLIF(m.region,''), p.region) AS region, "
                "COALESCE(NULLIF(m.cap_style,''), p.cap_style) AS cap_style, COALESCE(NULLIF(m.growth_value,''), p.growth_value) AS growth_value, "
                "COALESCE(NULLIF(m.theme_tags,''), p.theme_tags, '[]') AS theme_tags, COALESCE(NULLIF(m.risk_level,''), p.risk_level) AS risk_level "
                "FROM positions p LEFT JOIN instrument_metadata m ON m.symbol=p.symbol WHERE p.symbol = ? ORDER BY p.id LIMIT 1",
                (symbol.upper(),),
            ).fetchone()
        return PositionRecord.model_validate(dict(row)) if row else None

    def set_instrument_metadata(
        self,
        *,
        symbol: str,
        sector: str | None = None,
        region: str | None = None,
        cap_style: str | None = None,
        growth_value: str | None = None,
        theme_tags: list[str] | None = None,
        risk_level: str | None = None,
        source: str,
        source_ref: str | None = None,
        occurred_at: datetime | None = None,
    ) -> str:
        if not source.strip():
            raise ValueError("instrument metadata requires a source")
        symbol = symbol.upper()
        occurred_at = occurred_at or self._utc_now()
        event_id = str(uuid4())
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute("SELECT * FROM instrument_metadata WHERE symbol=?", (symbol,)).fetchone()
            resolved_sector = sector if sector is not None else self._row_value(existing, "sector") if existing else None
            resolved_region = region if region is not None else self._row_value(existing, "region") if existing else None
            resolved_cap_style = cap_style if cap_style is not None else self._row_value(existing, "cap_style") if existing else None
            resolved_growth_value = growth_value if growth_value is not None else self._row_value(existing, "growth_value") if existing else None
            resolved_risk_level = risk_level if risk_level is not None else self._row_value(existing, "risk_level") if existing else None
            if theme_tags is not None:
                resolved_themes = theme_tags
            elif existing:
                resolved_themes = PositionRecord.parse_theme_tags(self._row_value(existing, "theme_tags", "[]"))
            else:
                resolved_themes = []
            payload = {
                "sector": resolved_sector,
                "region": resolved_region,
                "cap_style": resolved_cap_style,
                "growth_value": resolved_growth_value,
                "theme_tags": resolved_themes,
                "risk_level": resolved_risk_level,
            }
            conn.execute(
                "INSERT INTO instrument_metadata(symbol,sector,region,cap_style,growth_value,theme_tags,risk_level,source,source_ref,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET sector=excluded.sector, region=excluded.region, "
                "cap_style=excluded.cap_style, growth_value=excluded.growth_value, theme_tags=excluded.theme_tags, "
                "risk_level=excluded.risk_level, source=excluded.source, source_ref=excluded.source_ref, updated_at=excluded.updated_at",
                (
                    symbol, resolved_sector, resolved_region, resolved_cap_style, resolved_growth_value,
                    json.dumps(resolved_themes, ensure_ascii=False), resolved_risk_level,
                    source, source_ref, occurred_at.isoformat(),
                ),
            )
            self._append_event(
                conn,
                event_id=event_id,
                event_type="instrument_metadata_updated",
                occurred_at=occurred_at,
                symbol=symbol,
                payload=payload,
                source=source,
                source_ref=source_ref,
            )
            conn.commit()
        return event_id

    def get_instrument_metadata(self, symbol: str) -> InstrumentMetadata | None:
        self.ensure_schema()
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM instrument_metadata WHERE symbol=?", (symbol.upper(),)).fetchone()
        return InstrumentMetadata.model_validate(dict(row)) if row else None

    def set_position_baseline(
        self,
        *,
        symbol: str,
        quantity: float,
        avg_cost: float,
        market: str | None = None,
        currency: str | None = None,
        source: str = "baseline",
        source_ref: str | None = None,
        occurred_at: datetime | None = None,
    ) -> str:
        if quantity < 0 or avg_cost < 0:
            raise ValueError("baseline quantity and avg_cost cannot be negative")
        symbol = symbol.upper()
        requested_market, requested_currency = market, currency
        market, currency = self._market_currency(symbol, market, currency)
        occurred_at = occurred_at or self._utc_now()
        event_id = str(uuid4())
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM positions WHERE symbol = ? ORDER BY id LIMIT 1", (symbol,)).fetchone()
            if row:
                if requested_market is None and self._row_value(row, "market"):
                    market = str(row["market"]).upper()
                if requested_currency is None and self._row_value(row, "currency"):
                    currency = str(row["currency"]).upper()
                conn.execute(
                    "UPDATE positions SET quantity=?, avg_cost=?, market=?, currency=?, updated_at=? WHERE id=?",
                    (quantity, avg_cost, market, currency, occurred_at.isoformat(), row["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO positions(symbol, quantity, avg_cost, current_price, updated_at, market, currency) VALUES(?,?,?,?,?,?,?)",
                    (symbol, quantity, avg_cost, 0.0, occurred_at.isoformat(), market, currency),
                )
            self._append_event(
                conn,
                event_id=event_id,
                event_type="position_baseline",
                occurred_at=occurred_at,
                symbol=symbol,
                payload={"quantity": quantity, "avg_cost": avg_cost, "market": market, "currency": currency},
                source=source,
                source_ref=source_ref,
            )
            conn.commit()
        return event_id

    def record_trade(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        fees: float = 0.0,
        market: str | None = None,
        currency: str | None = None,
        occurred_at: datetime | None = None,
        source: str = "execution_evidence",
        decision_ref: str | None = None,
        execution_ref: str,
        correction_reason: str | None = None,
        adjust_cash_position: bool = True,
    ) -> TradeResult:
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if quantity <= 0 or price <= 0 or fees < 0:
            raise ValueError("quantity/price must be positive and fees non-negative")
        if source == "correction":
            if not correction_reason or not correction_reason.strip():
                raise ValueError("correction trades require correction_reason")
        elif not decision_ref or not decision_ref.strip():
            raise ValueError("trade recording requires a decision_ref")
        if not execution_ref.strip():
            raise ValueError("trade recording requires an execution_ref")
        symbol = symbol.upper()
        requested_market, requested_currency = market, currency
        market, currency = self._market_currency(symbol, market, currency)
        occurred_at = occurred_at or self._utc_now()
        event_id = f"trade:{execution_ref.strip()}"

        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM portfolio_events WHERE event_id=?", (event_id,)).fetchone():
                raise ValueError(f"execution_ref is already recorded: {execution_ref}")
            row = conn.execute("SELECT * FROM positions WHERE symbol=? ORDER BY id LIMIT 1", (symbol,)).fetchone()
            if row:
                if requested_market is None and self._row_value(row, "market"):
                    market = str(row["market"]).upper()
                if requested_currency is None and self._row_value(row, "currency"):
                    currency = str(row["currency"]).upper()
            previous_qty = float(row["quantity"]) if row else 0.0
            previous_avg = float(row["avg_cost"]) if row else 0.0
            current_price = float(row["current_price"]) if row else 0.0

            if side == "buy":
                new_qty = previous_qty + quantity
                new_avg = ((previous_qty * previous_avg) + (quantity * price) + fees) / new_qty
                if row:
                    conn.execute(
                        "UPDATE positions SET quantity=?, avg_cost=?, market=?, currency=?, updated_at=? WHERE id=?",
                        (new_qty, new_avg, market, currency, occurred_at.isoformat(), row["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO positions(symbol, quantity, avg_cost, current_price, updated_at, market, currency) VALUES(?,?,?,?,?,?,?)",
                        (symbol, new_qty, new_avg, current_price, occurred_at.isoformat(), market, currency),
                    )
                closed = False
            else:
                if row is None:
                    raise ValueError(f"cannot sell {symbol}: no position")
                if quantity > previous_qty:
                    raise ValueError(f"cannot sell {quantity} {symbol}: only {previous_qty} available")
                new_qty = previous_qty - quantity
                new_avg = previous_avg if new_qty else None
                closed = new_qty == 0
                if closed:
                    conn.execute("DELETE FROM positions WHERE id=?", (row["id"],))
                else:
                    conn.execute(
                        "UPDATE positions SET quantity=?, updated_at=? WHERE id=?",
                        (new_qty, occurred_at.isoformat(), row["id"]),
                    )

            cash_adjustment = 0.0
            previous_cash = None
            new_cash = None
            if adjust_cash_position:
                cash_adjustment = (
                    -(quantity * price + fees)
                    if side == "buy"
                    else quantity * price - fees
                )
                if side == "sell" and cash_adjustment < 0:
                    raise ValueError("sell fees cannot exceed gross proceeds")
                previous_cash, new_cash = self._adjust_cash_position(
                    conn,
                    currency=currency,
                    amount=cash_adjustment,
                    occurred_at=occurred_at,
                    require_sufficient=side == "buy",
                )

            payload = {
                "side": side,
                "quantity": quantity,
                "price": price,
                "fees": fees,
                "currency": currency,
                "market": market,
                "previous_quantity": previous_qty,
                "new_quantity": new_qty,
                "new_avg_cost": new_avg,
                "correction_reason": correction_reason,
                "decision_ref": decision_ref,
                "execution_ref": execution_ref,
                "cash_adjustment": round(cash_adjustment, 2),
                "previous_cash": previous_cash,
                "new_cash": new_cash,
            }
            self._append_event(
                conn,
                event_id=event_id,
                event_type="trade",
                occurred_at=occurred_at,
                symbol=symbol,
                payload=payload,
                source=source,
                source_ref=execution_ref,
            )
            conn.commit()

        return TradeResult(
            event_id=event_id,
            symbol=symbol,
            side=side,
            trade_quantity=quantity,
            trade_price=price,
            fees=fees,
            previous_quantity=previous_qty,
            new_quantity=new_qty,
            new_avg_cost=new_avg,
            closed=closed,
        )

    def record_cashflow(
        self,
        *,
        amount_usd: float,
        description: str,
        event_date: date | None = None,
        source: str = "cashflow_evidence",
        cashflow_ref: str,
        adjust_cash_position: bool = True,
    ) -> str:
        if not cashflow_ref.strip():
            raise ValueError("cashflow recording requires a cashflow_ref")
        event_date = event_date or date.today()
        occurred_at = datetime.combine(event_date, datetime.min.time(), tzinfo=timezone.utc)
        event_id = f"cashflow:{cashflow_ref.strip()}"
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM portfolio_events WHERE event_id=?", (event_id,)).fetchone():
                raise ValueError(f"cashflow_ref is already recorded: {cashflow_ref}")
            conn.execute(
                "INSERT INTO cashflow_events(event_date, amount_usd, description, created_at) VALUES(?,?,?,?)",
                (event_date.isoformat(), amount_usd, description, self._utc_now().isoformat()),
            )
            if adjust_cash_position:
                row = conn.execute("SELECT * FROM positions WHERE symbol='CASH_USD' ORDER BY id LIMIT 1").fetchone()
                new_cash = (float(row["quantity"]) if row else 0.0) + amount_usd
                if row:
                    conn.execute(
                        "UPDATE positions SET quantity=?, avg_cost=1, current_price=1, market='US', currency='USD', updated_at=? WHERE id=?",
                        (new_cash, occurred_at.isoformat(), row["id"]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO positions(symbol, quantity, avg_cost, current_price, updated_at, market, currency) VALUES('CASH_USD',?,1,1,?,'US','USD')",
                        (new_cash, occurred_at.isoformat()),
                    )
            self._append_event(
                conn,
                event_id=event_id,
                event_type="cashflow",
                occurred_at=occurred_at,
                symbol="CASH_USD",
                payload={"amount_usd": amount_usd, "description": description, "adjusted_cash_position": adjust_cash_position},
                source=source,
                source_ref=cashflow_ref,
            )
            conn.commit()
        return event_id

    def record_quote(
        self,
        *,
        symbol: str,
        price: float,
        currency: str,
        as_of: datetime,
        source: str,
        source_ref: str | None = None,
    ) -> QuoteRecord:
        if price <= 0:
            raise ValueError("price must be positive")
        if not source.strip():
            raise ValueError("quote source cannot be empty")
        if as_of.tzinfo is None:
            raise ValueError("quote as_of must be timezone-aware")
        as_of = as_of.astimezone(timezone.utc)
        symbol = symbol.upper()
        currency = currency.upper()
        recorded_at = self._utc_now()
        event_id = str(uuid4())
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM quotes WHERE symbol=? AND as_of=? AND source=?",
                (symbol, as_of.isoformat(), source),
            ).fetchone()
            if existing and (
                float(existing["price"]) == float(price)
                and str(existing["currency"]).upper() == currency
                and existing["source_ref"] == source_ref
            ):
                conn.execute(
                    "UPDATE positions SET current_price=?, updated_at=? WHERE symbol=?",
                    (price, as_of.isoformat(), symbol),
                )
                conn.commit()
                return QuoteRecord.model_validate(dict(existing))
            conn.execute(
                "INSERT INTO quotes(symbol, price, currency, as_of, source, source_ref, recorded_at) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(symbol, as_of, source) DO UPDATE SET price=excluded.price, currency=excluded.currency, source_ref=excluded.source_ref, recorded_at=excluded.recorded_at",
                (symbol, price, currency, as_of.isoformat(), source, source_ref, recorded_at.isoformat()),
            )
            row = conn.execute(
                "SELECT id FROM quotes WHERE symbol=? AND as_of=? AND source=?",
                (symbol, as_of.isoformat(), source),
            ).fetchone()
            conn.execute(
                "UPDATE positions SET current_price=?, updated_at=? WHERE symbol=?",
                (price, as_of.isoformat(), symbol),
            )
            self._append_event(
                conn,
                event_id=event_id,
                event_type="quote_corrected" if existing else "quote_observed",
                occurred_at=as_of,
                symbol=symbol,
                payload={
                    "price": price,
                    "currency": currency,
                    "previous_price": float(existing["price"]) if existing else None,
                    "previous_source_ref": existing["source_ref"] if existing else None,
                },
                source=source,
                source_ref=source_ref,
            )
            conn.commit()
        return QuoteRecord(
            id=row["id"],
            symbol=symbol,
            price=price,
            currency=currency,
            as_of=as_of,
            source=source,
            source_ref=source_ref,
            recorded_at=recorded_at,
        )

    def latest_quotes(self, *, as_of: datetime | None = None) -> dict[str, QuoteRecord]:
        if as_of is not None and as_of.tzinfo is None:
            raise ValueError("quote cutoff must be timezone-aware")
        if as_of is not None:
            as_of = as_of.astimezone(timezone.utc)
        self.ensure_schema()
        with self.connect() as conn:
            if as_of is None:
                rows = conn.execute(
                    "SELECT q.* FROM quotes q JOIN (SELECT symbol, MAX(as_of) AS max_as_of FROM quotes GROUP BY symbol) latest "
                    "ON q.symbol=latest.symbol AND q.as_of=latest.max_as_of ORDER BY q.symbol, q.id DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT q.* FROM quotes q JOIN (SELECT symbol, MAX(as_of) AS max_as_of FROM quotes WHERE as_of<=? GROUP BY symbol) latest "
                    "ON q.symbol=latest.symbol AND q.as_of=latest.max_as_of ORDER BY q.symbol, q.id DESC",
                    (as_of.isoformat(),),
                ).fetchall()
        result: dict[str, QuoteRecord] = {}
        for row in rows:
            result.setdefault(row["symbol"], QuoteRecord.model_validate(dict(row)))
        return result

    def record_fx_rate(
        self,
        *,
        currency: str,
        base_currency: str,
        rate_to_base: float,
        as_of: datetime,
        source: str,
        source_ref: str | None = None,
    ) -> QuoteRecord:
        currency = currency.upper()
        base_currency = base_currency.upper()
        if currency == base_currency:
            raise ValueError("FX observation requires two different currencies")
        return self.record_quote(
            symbol=f"FX:{currency}/{base_currency}",
            price=rate_to_base,
            currency=base_currency,
            as_of=as_of,
            source=source,
            source_ref=source_ref,
        )

    def list_option_contracts(self, status: str | None = None) -> list[OptionContractRecord]:
        self.ensure_schema()
        with self.connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM option_contracts WHERE status=? ORDER BY expiry_date", (status,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM option_contracts ORDER BY expiry_date").fetchall()
        return [OptionContractRecord.model_validate(dict(row)) for row in rows]

    def record_option_open(
        self,
        *,
        underlying_symbol: str,
        expiry_date: date,
        strike: float,
        contracts: int,
        premium_per_share: float,
        opened_date: date | None = None,
        fees: float = 0.0,
        currency: str | None = None,
        market: str | None = None,
        intent: str = "lower_price_entry",
        decision_ref: str,
        execution_ref: str,
        notes: str = "",
        adjust_cash_position: bool = True,
    ) -> tuple[int, str]:
        opened_date = opened_date or date.today()
        if opened_date > expiry_date:
            raise ValueError("opened_date cannot be after expiry_date")
        if not decision_ref.strip():
            raise ValueError("option opening requires a decision_ref")
        if not execution_ref.strip():
            raise ValueError("option opening requires an execution_ref")
        metrics = derive_open_put_metrics(
            strike=strike,
            contracts=contracts,
            premium_per_share=premium_per_share,
            fees=fees,
        )
        event_id = f"option-open:{execution_ref.strip()}"
        now = self._utc_now()
        symbol = underlying_symbol.upper()
        market, currency = self._market_currency(symbol, market, currency)
        opened_at = datetime.combine(opened_date, datetime.min.time(), tzinfo=timezone.utc)
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM portfolio_events WHERE event_id=?", (event_id,)).fetchone():
                raise ValueError(f"execution_ref is already recorded: {execution_ref}")
            cursor = conn.execute(
                "INSERT INTO option_contracts(underlying_symbol, option_type, side, contracts, shares_per_contract, strike, expiry_date, opened_date, premium_per_share, premium_total, fees, currency, market, status, reserved_cash, net_cash_obligation, effective_entry_if_assigned, intent, notes, linked_decision_file, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'open',?,?,?,?,?,?,?,?)",
                (
                    symbol, "put", "short", metrics["contract_count"], 100, strike,
                    expiry_date.isoformat(), opened_date.isoformat(), premium_per_share,
                    metrics["premium_total"], fees, currency, market,
                    metrics["reserved_cash"], metrics["net_cash_obligation"],
                    metrics["effective_entry_if_assigned"], intent, notes, decision_ref,
                    now.isoformat(), now.isoformat(),
                ),
            )
            contract_id = int(cursor.lastrowid)
            premium_cash = round(metrics["premium_total"] - fees, 2)
            if adjust_cash_position and premium_cash:
                self._adjust_cash_position(
                    conn,
                    currency=currency,
                    amount=premium_cash,
                    occurred_at=opened_at,
                )
            self._append_event(
                conn,
                event_id=event_id,
                event_type="option_opened",
                occurred_at=opened_at,
                symbol=symbol,
                payload={
                    "contract_id": contract_id,
                    "expiry_date": expiry_date.isoformat(),
                    "strike": strike,
                    "premium_cash_adjustment": premium_cash if adjust_cash_position else 0.0,
                    "execution_ref": execution_ref,
                    **metrics,
                },
                source="decision",
                source_ref=decision_ref,
            )
            conn.commit()
        return contract_id, event_id

    def transition_option(
        self,
        *,
        contract_id: int,
        new_status: str,
        event_date: date,
        execution_ref: str,
        assignment_price: float | None = None,
        realized_cost_to_close: float = 0.0,
        notes: str = "",
    ) -> str:
        if new_status not in {"assigned", "expired", "closed"}:
            raise ValueError("unsupported option status transition")
        if not execution_ref.strip():
            raise ValueError("option transition requires an execution_ref")
        event_id = f"option-{contract_id}-{new_status}:{execution_ref.strip()}"
        now = self._utc_now()
        event_at = datetime.combine(event_date, datetime.min.time(), tzinfo=timezone.utc)
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM portfolio_events WHERE event_id=?", (event_id,)).fetchone():
                raise ValueError(f"execution_ref is already recorded: {execution_ref}")
            row = conn.execute("SELECT * FROM option_contracts WHERE id=?", (contract_id,)).fetchone()
            if not row:
                raise ValueError(f"option contract #{contract_id} not found")
            if row["status"] != "open":
                raise ValueError(f"option contract #{contract_id} is {row['status']}, expected open")
            opened = date.fromisoformat(str(row["opened_date"])[:10]) if row["opened_date"] else None
            expiry = date.fromisoformat(str(row["expiry_date"])[:10])
            if opened and event_date < opened:
                raise ValueError("event date cannot precede opened_date")
            if new_status == "expired" and event_date < expiry:
                raise ValueError("expiration event cannot precede expiry_date")
            if new_status == "closed" and event_date > expiry:
                raise ValueError("close event cannot follow expiry_date")

            premium_total = float(row["premium_total"] or 0.0)
            fees = float(row["fees"] or 0.0)
            realized_premium = premium_total - fees
            _, option_currency = self._market_currency(
                str(row["underlying_symbol"]),
                self._row_value(row, "market"),
                self._row_value(row, "currency"),
            )
            if new_status == "closed":
                if realized_cost_to_close < 0:
                    raise ValueError("realized_cost_to_close cannot be negative")
                realized_premium -= realized_cost_to_close
                if realized_cost_to_close:
                    self._adjust_cash_position(
                        conn,
                        currency=option_currency,
                        amount=-realized_cost_to_close,
                        occurred_at=event_at,
                    )
            assigned_date = event_date.isoformat() if new_status == "assigned" else row["assigned_date"]
            closed_date = event_date.isoformat() if new_status in {"expired", "closed"} else row["closed_date"]
            assignment = assignment_price if new_status == "assigned" else row["assignment_price"]
            if new_status == "assigned" and assignment is None:
                assignment = float(row["strike"])
            assignment_payload: dict = {}
            if new_status == "assigned":
                assignment_payload = self._apply_option_assignment(
                    conn,
                    row=row,
                    assignment_price=float(assignment),
                    occurred_at=event_at,
                )
            merged_notes = "\n".join(part for part in (row["notes"] or "", notes.strip()) if part)
            conn.execute(
                "UPDATE option_contracts SET status=?, assigned_date=?, closed_date=?, assignment_price=?, realized_premium=?, notes=?, updated_at=? WHERE id=?",
                (new_status, assigned_date, closed_date, assignment, round(realized_premium, 2), merged_notes, now.isoformat(), contract_id),
            )
            self._append_event(
                conn,
                event_id=event_id,
                event_type=f"option_{new_status}",
                occurred_at=event_at,
                symbol=row["underlying_symbol"],
                payload={
                    "contract_id": contract_id,
                    "status": new_status,
                    "assignment_price": assignment,
                    "realized_premium": round(realized_premium, 2),
                    "close_cost_cash_adjustment": -realized_cost_to_close if new_status == "closed" else 0.0,
                    "execution_ref": execution_ref,
                    **assignment_payload,
                },
                source="execution_evidence",
                source_ref=execution_ref,
            )
            conn.commit()
        return event_id

    def list_events(self, *, after: datetime | None = None, limit: int = 200) -> list[PortfolioEvent]:
        if not 1 <= limit <= 1_000:
            raise ValueError("event query limit must be between 1 and 1000")
        self.ensure_schema()
        with self.connect() as conn:
            if after:
                rows = conn.execute(
                    "SELECT * FROM portfolio_events WHERE occurred_at>? ORDER BY occurred_at DESC, id DESC LIMIT ?",
                    (after.isoformat(), limit),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM portfolio_events ORDER BY occurred_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
        return [
            PortfolioEvent(
                event_id=row["event_id"],
                event_type=row["event_type"],
                occurred_at=row["occurred_at"],
                symbol=row["symbol"],
                payload=json.loads(row["payload_json"]),
                source=row["source"],
                source_ref=row["source_ref"],
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]

    def record_snapshot(self, snapshot: SnapshotRecord, *, source: str = "portfolio_review", source_ref: str | None = None) -> str:
        event_id = str(uuid4())
        occurred_at = datetime.combine(snapshot.snapshot_date, datetime.min.time(), tzinfo=timezone.utc)
        self.ensure_schema()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT id FROM snapshots WHERE snapshot_date=? ORDER BY id DESC", (snapshot.snapshot_date.isoformat(),)).fetchall()
            if rows:
                conn.execute(
                    "UPDATE snapshots SET total_value=?, cash=?, daily_return_pct=?, max_drawdown_pct=?, top_position_weight=?, positions_json=?, notes=? WHERE id=?",
                    (snapshot.total_value, snapshot.cash, snapshot.daily_return_pct, snapshot.max_drawdown_pct, snapshot.top_position_weight, snapshot.positions_json, snapshot.notes, rows[0]["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO snapshots(snapshot_date,total_value,cash,daily_return_pct,max_drawdown_pct,top_position_weight,positions_json,notes) VALUES(?,?,?,?,?,?,?,?)",
                    (snapshot.snapshot_date.isoformat(), snapshot.total_value, snapshot.cash, snapshot.daily_return_pct, snapshot.max_drawdown_pct, snapshot.top_position_weight, snapshot.positions_json, snapshot.notes),
                )
            self._append_event(
                conn,
                event_id=event_id,
                event_type="snapshot_recorded",
                occurred_at=occurred_at,
                symbol=None,
                payload={"snapshot_date": snapshot.snapshot_date.isoformat(), "total_value": snapshot.total_value, "cash": snapshot.cash},
                source=source,
                source_ref=source_ref,
            )
            conn.commit()
        return event_id

    def list_snapshots(self) -> list[SnapshotRecord]:
        self.ensure_schema()
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM snapshots ORDER BY snapshot_date, id").fetchall()
        return [SnapshotRecord.model_validate(dict(row)) for row in rows]

    def list_cashflows(self) -> list[CashflowRecord]:
        self.ensure_schema()
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM cashflow_events ORDER BY event_date, id").fetchall()
        return [CashflowRecord.model_validate(dict(row)) for row in rows]

    def bootstrap_legacy_events(self) -> int:
        """Add idempotent baseline events for legacy rows without changing them."""
        self.ensure_schema()
        added = 0
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for row in conn.execute("SELECT * FROM positions ORDER BY id").fetchall():
                event_id = f"legacy-position-{row['id']}"
                market, currency = self._market_currency(
                    row["symbol"],
                    self._row_value(row, "market"),
                    self._row_value(row, "currency"),
                )
                classifications = {
                    "sector": self._row_value(row, "sector"),
                    "region": self._row_value(row, "region"),
                    "cap_style": self._row_value(row, "cap_style"),
                    "growth_value": self._row_value(row, "growth_value"),
                    "theme_tags": self._row_value(row, "theme_tags", "[]"),
                    "risk_level": self._row_value(row, "risk_level"),
                }
                if any(value not in (None, "", "[]") for value in classifications.values()):
                    conn.execute(
                        "INSERT OR IGNORE INTO instrument_metadata(symbol,sector,region,cap_style,growth_value,theme_tags,risk_level,source,source_ref,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (
                            row["symbol"], classifications["sector"], classifications["region"],
                            classifications["cap_style"], classifications["growth_value"],
                            classifications["theme_tags"], classifications["risk_level"],
                            "legacy_migration", None,
                            self._coerce_datetime(self._row_value(row, "updated_at")).isoformat(),
                        ),
                    )
                added += self._append_event(
                    conn,
                    event_id=event_id,
                    event_type="legacy_position_baseline",
                    occurred_at=self._coerce_datetime(self._row_value(row, "updated_at")),
                    symbol=row["symbol"],
                    payload={
                        "quantity": row["quantity"],
                        "avg_cost": row["avg_cost"],
                        "market": market,
                        "currency": currency,
                        "classifications": classifications,
                    },
                    source="legacy_migration",
                    source_ref=None,
                    ignore_existing=True,
                )
            for row in conn.execute("SELECT * FROM option_contracts ORDER BY id").fetchall():
                event_id = f"legacy-option-{row['id']}"
                added += self._append_event(
                    conn,
                    event_id=event_id,
                    event_type="legacy_option_baseline",
                    occurred_at=self._coerce_datetime(self._row_value(row, "updated_at") or self._row_value(row, "created_at")),
                    symbol=row["underlying_symbol"],
                    payload={"contract_id": row["id"], "status": row["status"], "strike": row["strike"], "expiry_date": str(row["expiry_date"])},
                    source="legacy_migration",
                    source_ref=None,
                    ignore_existing=True,
                )
            for row in conn.execute("SELECT * FROM cashflow_events ORDER BY id").fetchall():
                event_id = f"legacy-cashflow-{row['id']}"
                occurred = datetime.combine(date.fromisoformat(str(row["event_date"])[:10]), datetime.min.time(), tzinfo=timezone.utc)
                added += self._append_event(
                    conn,
                    event_id=event_id,
                    event_type="legacy_cashflow",
                    occurred_at=occurred,
                    symbol="CASH_USD",
                    payload={"amount_usd": row["amount_usd"], "description": row["description"]},
                    source="legacy_migration",
                    source_ref=None,
                    ignore_existing=True,
                )
            conn.commit()
        return added

    @staticmethod
    def _coerce_datetime(value) -> datetime:
        if isinstance(value, datetime):
            return value
        if value:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc)

    def _append_event(
        self,
        conn: sqlite3.Connection,
        *,
        event_id: str,
        event_type: str,
        occurred_at: datetime,
        symbol: str | None,
        payload: dict,
        source: str,
        source_ref: str | None,
        ignore_existing: bool = False,
    ) -> int:
        sql = (
            "INSERT OR IGNORE INTO portfolio_events(event_id,event_type,occurred_at,symbol,payload_json,source,source_ref,recorded_at) VALUES(?,?,?,?,?,?,?,?)"
            if ignore_existing
            else "INSERT INTO portfolio_events(event_id,event_type,occurred_at,symbol,payload_json,source,source_ref,recorded_at) VALUES(?,?,?,?,?,?,?,?)"
        )
        cursor = conn.execute(
            sql,
            (
                event_id,
                event_type,
                occurred_at.isoformat(),
                symbol,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                source,
                source_ref,
                self._utc_now().isoformat(),
            ),
        )
        return 1 if cursor.rowcount else 0

    def _adjust_cash_position(
        self,
        conn: sqlite3.Connection,
        *,
        currency: str,
        amount: float,
        occurred_at: datetime,
        require_sufficient: bool = False,
    ) -> tuple[float, float]:
        currency = currency.upper()
        symbol = f"CASH_{currency}"
        row = conn.execute("SELECT * FROM positions WHERE symbol=? ORDER BY id LIMIT 1", (symbol,)).fetchone()
        previous = float(row["quantity"]) if row else 0.0
        current = previous + amount
        if require_sufficient and current < -1e-9:
            raise ValueError(
                f"insufficient {symbol}: assignment needs {abs(amount):.2f}, available {previous:.2f}"
            )
        if row:
            conn.execute(
                "UPDATE positions SET quantity=?, avg_cost=1, current_price=1, currency=?, updated_at=? WHERE id=?",
                (current, currency, occurred_at.isoformat(), row["id"]),
            )
        else:
            market, _ = self._market_currency(symbol, currency=currency)
            conn.execute(
                "INSERT INTO positions(symbol, quantity, avg_cost, current_price, updated_at, market, currency) VALUES(?,?,1,1,?,?,?)",
                (symbol, current, occurred_at.isoformat(), market, currency),
            )
        return previous, current

    def _apply_option_assignment(
        self,
        conn: sqlite3.Connection,
        *,
        row: sqlite3.Row,
        assignment_price: float,
        occurred_at: datetime,
    ) -> dict:
        if row["option_type"] != "put" or row["side"] != "short":
            raise ValueError("automatic assignment is supported only for short puts")
        shares = int(row["contracts"]) * int(row["shares_per_contract"])
        symbol = str(row["underlying_symbol"]).upper()
        market, currency = self._market_currency(
            symbol,
            self._row_value(row, "market"),
            self._row_value(row, "currency"),
        )
        cash_used = round(shares * assignment_price, 2)
        previous_cash, new_cash = self._adjust_cash_position(
            conn,
            currency=currency,
            amount=-cash_used,
            occurred_at=occurred_at,
            require_sufficient=True,
        )
        position = conn.execute("SELECT * FROM positions WHERE symbol=? ORDER BY id LIMIT 1", (symbol,)).fetchone()
        previous_qty = float(position["quantity"]) if position else 0.0
        previous_avg = float(position["avg_cost"]) if position else 0.0
        new_qty = previous_qty + shares
        new_avg = ((previous_qty * previous_avg) + cash_used) / new_qty
        if position:
            conn.execute(
                "UPDATE positions SET quantity=?, avg_cost=?, market=?, currency=?, updated_at=? WHERE id=?",
                (new_qty, new_avg, market, currency, occurred_at.isoformat(), position["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO positions(symbol, quantity, avg_cost, current_price, updated_at, market, currency) VALUES(?,?,?,?,?,?,?)",
                (symbol, new_qty, new_avg, assignment_price, occurred_at.isoformat(), market, currency),
            )
        return {
            "assigned_shares": shares,
            "cash_used": cash_used,
            "previous_cash": previous_cash,
            "new_cash": new_cash,
            "previous_quantity": previous_qty,
            "new_quantity": new_qty,
            "new_avg_cost": round(new_avg, 8),
        }
