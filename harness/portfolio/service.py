from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping

from harness.portfolio.market_data import MarketDataClient, RefreshReport
from harness.portfolio.models import InvestorProfile, PortfolioState, PositionView, SnapshotRecord
from harness.portfolio.store import PortfolioStore
from harness.settings import HarnessPaths


class PortfolioService:
    """Bounded portfolio queries and low-frequency snapshot calculations."""

    def __init__(
        self,
        store: PortfolioStore | None = None,
        *,
        paths: HarnessPaths | None = None,
        base_currency: str = "USD",
        stale_after_days: int = 7,
    ):
        self.paths = paths or HarnessPaths.discover()
        self.store = store or PortfolioStore(paths=self.paths)
        self.base_currency = base_currency.upper()
        self.stale_after_days = stale_after_days

    def load_profile(self, path: str | Path | None = None) -> InvestorProfile:
        profile_path = Path(path) if path else self.paths.profile_file
        if not profile_path.exists():
            return InvestorProfile()
        return InvestorProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))

    def get_state(
        self,
        *,
        fx_rates_to_base: Mapping[str, float] | None = None,
        as_of: datetime | None = None,
    ) -> PortfolioState:
        """Return current state without loading trade history.

        ``fx_rates_to_base`` is the amount of base currency for one unit of the
        named currency, for example ``{"CNY": 0.138}`` when base is USD.
        """

        generated_at = as_of or datetime.now(timezone.utc)
        if generated_at.tzinfo is None:
            raise ValueError("portfolio as_of must be timezone-aware")
        positions = self.store.list_positions()
        quotes = self.store.latest_quotes(as_of=generated_at)
        supplied_fx = {key.upper(): float(value) for key, value in (fx_rates_to_base or {}).items()}
        warnings: list[str] = []
        views: list[PositionView] = []
        total_value = 0.0
        total_cost = 0.0
        cash_value = 0.0
        valuation_complete = True
        priced_count = 0

        for position in positions:
            symbol = position.symbol.upper()
            currency = position.currency.upper()
            quality: list[str] = []
            quote = quotes.get(symbol)
            is_cash = symbol.startswith("CASH_")

            if is_cash:
                price = 1.0
                quote_as_of = position.updated_at
                quote_source = "cash_nominal"
            elif quote is not None:
                price = quote.price
                quote_as_of = quote.as_of
                quote_source = quote.source
                if quote.currency.upper() != currency:
                    quality.append(f"quote_currency_mismatch:{quote.currency.upper()}!=position:{currency}")
                quote_age_days = (generated_at - quote.as_of).total_seconds() / 86_400
                if quote_age_days > self.stale_after_days:
                    quality.append(f"stale_quote:{quote_age_days:.1f}d")
            elif position.current_price > 0:
                price = position.current_price
                quote_as_of = position.updated_at
                quote_source = "legacy_cached_price"
                quality.append("price_has_no_structured_quote_source")
            else:
                price = None
                quote_as_of = None
                quote_source = None
                quality.append("missing_price")

            fx_rate, fx_as_of, fx_source = self._resolve_fx(currency, supplied_fx, quotes)
            if fx_rate is None:
                quality.append(f"missing_fx_rate:{currency}->{self.base_currency}")
            elif fx_source == "request_supplied":
                quality.append("fx_rate_has_no_persisted_source")
            elif fx_as_of is not None:
                fx_age_days = (generated_at - fx_as_of).total_seconds() / 86_400
                if fx_age_days > self.stale_after_days:
                    quality.append(f"stale_fx:{fx_age_days:.1f}d")

            local_value = position.quantity * price if price is not None else None
            base_value = local_value * fx_rate if local_value is not None and fx_rate is not None else None
            local_cost = position.quantity * position.avg_cost
            unrealized_local = local_value - local_cost if local_value is not None else None
            unrealized_pct = (
                (unrealized_local / local_cost) * 100
                if unrealized_local is not None and local_cost > 0
                else None
            )

            if base_value is None:
                valuation_complete = False
            else:
                priced_count += 1
                total_value += base_value
                total_cost += local_cost * fx_rate
                if is_cash:
                    cash_value += base_value

            views.append(
                PositionView(
                    symbol=symbol,
                    quantity=position.quantity,
                    avg_cost=position.avg_cost,
                    currency=currency,
                    market=position.market,
                    sector=position.sector,
                    region=position.region,
                    cap_style=position.cap_style,
                    growth_value=position.growth_value,
                    theme_tags=position.theme_tags,
                    risk_level=position.risk_level,
                    current_price=price,
                    quote_as_of=quote_as_of,
                    quote_source=quote_source,
                    local_market_value=local_value,
                    base_market_value=base_value,
                    unrealized_pnl_local=unrealized_local,
                    unrealized_pnl_pct=unrealized_pct,
                    fx_rate_to_base=fx_rate,
                    fx_as_of=fx_as_of,
                    fx_source=fx_source,
                    data_quality=quality,
                )
            )

        if not valuation_complete:
            warnings.append("portfolio valuation is partial because one or more positions lack a price or FX rate")
        if total_value > 0:
            for view in views:
                if view.base_market_value is not None:
                    view.weight_pct = view.base_market_value / total_value * 100
                    if not valuation_complete:
                        view.data_quality.append("weight_uses_partial_portfolio_total")

        total_cost_out = total_cost if valuation_complete else None
        total_pnl = total_value - total_cost if valuation_complete else None
        cash_pct = cash_value / total_value * 100 if total_value > 0 else None
        sector_exposure: dict[str, float] = defaultdict(float)
        region_exposure: dict[str, float] = defaultdict(float)
        theme_exposure: dict[str, float] = defaultdict(float)
        for view in views:
            if view.symbol.startswith("CASH_") or view.weight_pct is None:
                continue
            if view.sector:
                sector_exposure[view.sector] += view.weight_pct
            if view.region:
                region_exposure[view.region] += view.weight_pct
            for theme in view.theme_tags:
                theme_exposure[theme] += view.weight_pct
        return PortfolioState(
            as_of=generated_at,
            base_currency=self.base_currency,
            total_value=round(total_value, 2),
            total_cost=round(total_cost_out, 2) if total_cost_out is not None else None,
            total_unrealized_pnl=round(total_pnl, 2) if total_pnl is not None else None,
            cash_value=round(cash_value, 2),
            cash_pct=round(cash_pct, 4) if cash_pct is not None else None,
            valuation_complete=valuation_complete,
            held_position_count=len(positions),
            priced_position_count=priced_count,
            sector_exposure_pct={key: round(value, 4) for key, value in sorted(sector_exposure.items())},
            region_exposure_pct={key: round(value, 4) for key, value in sorted(region_exposure.items())},
            theme_exposure_pct={key: round(value, 4) for key, value in sorted(theme_exposure.items())},
            positions=views,
            open_options=self.store.list_option_contracts(status="open"),
            warnings=warnings,
        )

    def refresh_quotes(
        self,
        *,
        client: MarketDataClient | None = None,
        fx_currencies: list[str] | None = None,
    ) -> RefreshReport:
        """Pull fresh quotes + FX for all positions and persist them as sourced rows.

        This is the bridge the harness was missing: it fetches prices over
        HTTP (Yahoo for US/crypto, Tencent for A-shares), persists each as a
        sourced quote via ``PortfolioStore.record_quote``, and returns a
        ``RefreshReport`` summarizing what was observed and what failed.
        Partial failures are isolated per symbol and reported, never fatal.
        """
        client = client or MarketDataClient()
        positions = self.store.list_positions()
        symbols = [p.symbol for p in positions if not p.symbol.startswith("CASH_")]
        currencies = sorted({p.currency for p in positions if p.currency and not p.currency.startswith("CASH_")} | set(fx_currencies or []))
        report = client.refresh_portfolio(symbols, fx_pairs=[(c, self.base_currency) for c in currencies if c.upper() != self.base_currency])
        for obs in report.observed:
            self.store.record_quote(
                symbol=obs.symbol,
                price=obs.price,
                currency=obs.currency,
                as_of=obs.as_of,
                source=obs.source,
                source_ref=obs.source_ref,
            )
        return report

    def record_snapshot(
        self,
        *,
        snapshot_date: date | None = None,
        notes: str = "",
        source_ref: str | None = None,
        fx_rates_to_base: Mapping[str, float] | None = None,
    ) -> tuple[SnapshotRecord, str]:
        day = snapshot_date or date.today()
        state = self.get_state(fx_rates_to_base=fx_rates_to_base)
        if not state.valuation_complete:
            raise ValueError("refusing to record a partial portfolio valuation")

        snapshots = self.store.list_snapshots()
        cashflows = self.store.list_cashflows()
        previous = next((item for item in reversed(snapshots) if item.snapshot_date < day), None)
        daily_return = 0.0
        if previous and previous.total_value:
            period_flows = [
                flow
                for flow in cashflows
                if previous.snapshot_date < flow.event_date <= day
                and flow.flow_scope == "external"
            ]
            missing_base = [str(flow.id or flow.event_date) for flow in period_flows if flow.amount_base is None]
            if missing_base:
                raise ValueError(
                    "cashflow TWR adjustment requires event-time base amounts; "
                    f"missing for {', '.join(missing_base)}"
                )
            flows = sum(flow.amount_base for flow in period_flows)
            daily_return = ((state.total_value - flows) / previous.total_value - 1) * 100

        history = [
            item.total_value
            for item in snapshots
            if item.snapshot_date < day and item.total_value > 0
        ]
        history.append(state.total_value)
        peak = 0.0
        max_drawdown = 0.0
        for value in history:
            peak = max(peak, value)
            if peak:
                max_drawdown = min(max_drawdown, (value / peak - 1) * 100)

        non_cash_weights = [
            item.weight_pct or 0.0
            for item in state.positions
            if not item.symbol.startswith("CASH_")
        ]
        compact_positions = [
            {
                "symbol": item.symbol,
                "quantity": item.quantity,
                "price": item.current_price,
                "quote_as_of": item.quote_as_of.isoformat() if item.quote_as_of else None,
                "base_market_value": item.base_market_value,
                "weight_pct": item.weight_pct,
            }
            for item in state.positions
        ]
        snapshot = SnapshotRecord(
            snapshot_date=day,
            total_value=state.total_value,
            cash=state.cash_value,
            daily_return_pct=round(daily_return, 4),
            max_drawdown_pct=round(max_drawdown, 4),
            top_position_weight=round(max(non_cash_weights, default=0.0), 4),
            positions_json=json.dumps(compact_positions, ensure_ascii=False, separators=(",", ":")),
            notes=notes,
        )
        event_id = self.store.record_snapshot(snapshot, source_ref=source_ref)
        return snapshot, event_id

    def recent_events(self, *, after: datetime | None = None, limit: int = 50):
        return self.store.list_events(after=after, limit=limit)

    def _resolve_fx(self, currency: str, supplied: Mapping[str, float], quotes) -> tuple[float | None, datetime | None, str | None]:
        if currency == self.base_currency:
            return 1.0, None, "base_currency"
        for key in (currency, f"{currency}/{self.base_currency}", f"{currency}{self.base_currency}"):
            if key in supplied:
                value = float(supplied[key])
                if value <= 0:
                    raise ValueError(f"FX rate must be positive: {key}")
                return value, None, "request_supplied"
        quote = quotes.get(f"FX:{currency}/{self.base_currency}")
        if quote is not None:
            if quote.currency.upper() != self.base_currency:
                return None, None, None
            return quote.price, quote.as_of, quote.source
        return None, None, None
