from datetime import datetime, timezone
from decimal import Decimal

import pytest

from bisq_market_intelligence.analyzer import (
    ExecutionResult,
    InvalidMarketStateError,
    MarketAnalyzer,
)
from bisq_market_intelligence.models import Offer


def make_offer(
    offer_id: str,
    direction: str,
    price: str,
    amount: str,
    min_amount: str = "0.01",
    timestamp: datetime | None = None,
) -> Offer:
    return Offer(
        offer_id=offer_id,
        timestamp=timestamp or datetime(2026, 9, 15, tzinfo=timezone.utc),
        market="BTC_USD",
        direction=direction,
        price=Decimal(price),
        min_amount=Decimal(min_amount),
        amount=Decimal(amount),
        volume=Decimal(price) * Decimal(amount),
        payment_method="SEPA",
    )


def test_best_bid_returns_highest_buy_offer():
    offers = [
        make_offer("buy-1", "BUY", "99000", "0.10"),
        make_offer("buy-2", "BUY", "99500", "0.25"),
        make_offer("buy-3", "BUY", "99200", "0.15"),
        make_offer("sell-1", "SELL", "100200", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    best_bid = analyzer.best_bid()

    assert best_bid is not None
    assert best_bid.offer_id == "buy-2"
    assert best_bid.price == Decimal("99500")
    assert best_bid.amount == Decimal("0.25")


def test_best_ask_returns_lowest_sell_offer():
    offers = [
        make_offer("sell-1", "SELL", "100200", "0.10"),
        make_offer("sell-2", "SELL", "100000", "0.30"),
        make_offer("sell-3", "SELL", "100400", "0.20"),
        make_offer("buy-1", "BUY", "99500", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    best_ask = analyzer.best_ask()

    assert best_ask is not None
    assert best_ask.offer_id == "sell-2"
    assert best_ask.price == Decimal("100000")
    assert best_ask.amount == Decimal("0.30")


def test_best_bid_returns_none_when_no_buy_offers():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.best_bid() is None


def test_best_ask_returns_none_when_no_sell_offers():
    offers = [
        make_offer("buy-1", "BUY", "99500", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.best_ask() is None


def test_mid_price_returns_average_of_best_bid_and_ask():
    offers = [
        make_offer("buy-1", "BUY", "99000", "0.10"),
        make_offer("buy-2", "BUY", "99500", "0.25"),
        make_offer("sell-1", "SELL", "100500", "0.10"),
        make_offer("sell-2", "SELL", "100000", "0.30"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.mid_price() == Decimal("99750")


def test_mid_price_returns_none_when_bid_is_missing():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.mid_price() is None


def test_mid_price_returns_none_when_ask_is_missing():
    offers = [
        make_offer("buy-1", "BUY", "99500", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.mid_price() is None


def test_spread_returns_difference_between_best_ask_and_best_bid():
    offers = [
        make_offer("buy-1", "BUY", "99000", "0.10"),
        make_offer("buy-2", "BUY", "99500", "0.25"),
        make_offer("sell-1", "SELL", "100500", "0.10"),
        make_offer("sell-2", "SELL", "100000", "0.30"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.spread() == Decimal("500")


def test_spread_returns_none_when_bid_is_missing():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.spread() is None


def test_spread_returns_none_when_ask_is_missing():
    offers = [
        make_offer("buy-1", "BUY", "99500", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.spread() is None


def test_spread_pct_returns_spread_as_percentage_of_mid_price():
    offers = [
        make_offer("buy-1", "BUY", "99500", "0.25"),
        make_offer("sell-1", "SELL", "100000", "0.30"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.spread_pct() == (
        Decimal("500") / Decimal("99750")
    ) * 100


def test_spread_pct_returns_none_when_bid_is_missing():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.spread_pct() is None


def test_spread_pct_returns_none_when_ask_is_missing():
    offers = [
        make_offer("buy-1", "BUY", "99500", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    assert analyzer.spread_pct() is None


def test_spread_pct_raises_when_mid_price_is_zero():
    offers = [
        make_offer("buy-1", "BUY", "0", "0.10"),
        make_offer("sell-1", "SELL", "0", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)

    with pytest.raises(
        InvalidMarketStateError,
        match="zero mid-price",
    ):
        analyzer.spread_pct()


def test_simulate_execution_buy_fully_filled_by_single_offer():
    offers = [
        make_offer("sell-1", "SELL", "100000", "1.00"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.50"), "BUY")

    assert result.fully_filled is True
    assert result.executed_amount == Decimal("0.50")
    assert result.total_cost == Decimal("50000.00")
    assert result.average_execution_price == Decimal("100000")
    assert result.reference_price == Decimal("100000")


def test_simulate_execution_buy_consumes_multiple_offers_weighted_average():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.20"),
        make_offer("sell-2", "SELL", "100200", "0.15"),
        make_offer("sell-3", "SELL", "100500", "0.40"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.50"), "BUY")

    expected_cost = (
        Decimal("0.20") * Decimal("100000")
        + Decimal("0.15") * Decimal("100200")
        + Decimal("0.15") * Decimal("100500")
    )

    assert result.fully_filled is True
    assert result.executed_amount == Decimal("0.50")
    assert result.total_cost == expected_cost
    assert result.average_execution_price == expected_cost / Decimal("0.50")
    assert result.reference_price == Decimal("100000")


def test_simulate_execution_partial_fill_when_liquidity_insufficient():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.30"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("1.00"), "BUY")

    assert result.fully_filled is False
    assert result.executed_amount == Decimal("0.30")
    assert result.average_execution_price == Decimal("100000")


def test_simulate_execution_returns_zero_when_no_offers_on_required_side():
    offers = [
        make_offer("buy-1", "BUY", "99500", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.50"), "BUY")

    assert result.fully_filled is False
    assert result.executed_amount == Decimal("0")
    assert result.total_cost == Decimal("0")
    assert result.average_execution_price is None
    assert result.reference_price is None


def test_simulate_execution_raises_on_invalid_side():
    offers = [make_offer("sell-1", "SELL", "100000", "0.50")]
    analyzer = MarketAnalyzer(offers)

    with pytest.raises(ValueError, match="side must be"):
        analyzer.simulate_execution(Decimal("0.10"), "COMPRAR")


def test_simulate_execution_raises_on_non_positive_amount():
    offers = [make_offer("sell-1", "SELL", "100000", "0.50")]
    analyzer = MarketAnalyzer(offers)

    with pytest.raises(ValueError, match="amount must be"):
        analyzer.simulate_execution(Decimal("0"), "BUY")


def test_simulate_execution_breaks_price_tie_by_earliest_timestamp():
    earlier = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    later = datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc)

    offers = [
        make_offer("sell-late", "SELL", "100000", "0.20", timestamp=later),
        make_offer("sell-early", "SELL", "100000", "0.20", timestamp=earlier),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.20"), "BUY")

    assert result.executed_amount == Decimal("0.20")
    assert result.total_cost == Decimal("0.20") * Decimal("100000")


def test_simulate_execution_skips_offer_below_its_own_min_amount():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.20", min_amount="0.05"),
        make_offer("sell-2", "SELL", "100200", "0.10", min_amount="0.01"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.03"), "BUY")

    assert result.fully_filled is True
    assert result.executed_amount == Decimal("0.03")
    assert result.average_execution_price == Decimal("100200")

def test_buy_execution_calculates_slippage_and_price_impact():
    offers = [
        make_offer("ask-1", "SELL", "100", "0.10"),
        make_offer("ask-2", "SELL", "101", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.20"), "BUY")

    assert result.average_execution_price == Decimal("100.5")
    assert result.reference_price == Decimal("100")
    assert result.last_execution_price == Decimal("101")

    assert result.slippage() == Decimal("0.5")
    assert result.slippage_pct() == Decimal("0.5")

    assert result.price_impact() == Decimal("1")
    assert result.price_impact_pct() == Decimal("1")


def test_sell_execution_calculates_slippage_and_price_impact():
    offers = [
        make_offer("bid-1", "BUY", "100", "0.10"),
        make_offer("bid-2", "BUY", "99", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.20"), "SELL")

    assert result.average_execution_price == Decimal("99.5")
    assert result.reference_price == Decimal("100")
    assert result.last_execution_price == Decimal("99")

    assert result.slippage() == Decimal("0.5")
    assert result.slippage_pct() == Decimal("0.5")

    assert result.price_impact() == Decimal("1")
    assert result.price_impact_pct() == Decimal("1")


def test_partial_execution_calculates_slippage_and_price_impact():
    offers = [
        make_offer("ask-1", "SELL", "100", "0.10"),
        make_offer("ask-2", "SELL", "101", "0.10"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.30"), "BUY")

    assert result.executed_amount == Decimal("0.20")
    assert result.fully_filled is False

    assert result.average_execution_price == Decimal("100.5")
    assert result.reference_price == Decimal("100")
    assert result.last_execution_price == Decimal("101")

    assert result.slippage() == Decimal("0.5")
    assert result.slippage_pct() == Decimal("0.5")

    assert result.price_impact() == Decimal("1")
    assert result.price_impact_pct() == Decimal("1")


def test_no_execution_returns_none_for_all_execution_metrics():
    offers = [
        make_offer("ask-1", "SELL", "100", "0.10", min_amount="0.05"),
    ]

    analyzer = MarketAnalyzer(offers)
    result = analyzer.simulate_execution(Decimal("0.02"), "BUY")

    assert result.executed_amount == Decimal("0")
    assert result.fully_filled is False

    assert result.reference_price == Decimal("100")
    assert result.average_execution_price is None
    assert result.last_execution_price is None

    assert result.slippage() is None
    assert result.slippage_pct() is None
    assert result.price_impact() is None
    assert result.price_impact_pct() is None


def test_execution_curve_returns_results_in_order_for_valid_amounts():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.20"),
        make_offer("sell-2", "SELL", "100200", "0.20"),
        make_offer("sell-3", "SELL", "100500", "0.20"),
    ]

    analyzer = MarketAnalyzer(offers)
    results = analyzer.execution_curve(
        [Decimal("0.10"), Decimal("0.30"), Decimal("0.60")],
        "BUY",
    )

    assert len(results) == 3

    assert results[0].requested_amount == Decimal("0.10")
    assert results[0].executed_amount == Decimal("0.10")
    assert results[0].average_execution_price == Decimal("100000")

    assert results[1].requested_amount == Decimal("0.30")
    assert results[1].executed_amount == Decimal("0.30")

    assert results[2].requested_amount == Decimal("0.60")
    assert results[2].executed_amount == Decimal("0.60")
    assert results[2].last_execution_price == Decimal("100500")


def test_execution_curve_returns_empty_list_for_empty_amounts():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.20"),
    ]

    analyzer = MarketAnalyzer(offers)
    results = analyzer.execution_curve([], "BUY")

    assert results == []


def test_execution_curve_raises_and_aborts_on_invalid_amount():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.20"),
        make_offer("sell-2", "SELL", "100200", "0.20"),
    ]

    analyzer = MarketAnalyzer(offers)

    with pytest.raises(ValueError, match="amount must be"):
        analyzer.execution_curve(
            [Decimal("0.10"), Decimal("-1"), Decimal("0.20")],
            "BUY",
        )


def test_execution_curve_raises_on_invalid_side():
    offers = [
        make_offer("sell-1", "SELL", "100000", "0.20"),
    ]

    analyzer = MarketAnalyzer(offers)

    with pytest.raises(ValueError, match="side must be"):
        analyzer.execution_curve([Decimal("0.10")], "HOLD")
