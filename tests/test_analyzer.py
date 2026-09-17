from datetime import datetime, timezone
from decimal import Decimal

import pytest

from bisq_market_intelligence.analyzer import (
    InvalidMarketStateError,
    MarketAnalyzer,
)
from bisq_market_intelligence.models import Offer


def make_offer(
    offer_id: str,
    direction: str,
    price: str,
    amount: str,
) -> Offer:
    return Offer(
        offer_id=offer_id,
        timestamp=datetime(2026, 9, 15, tzinfo=timezone.utc),
        market="BTC_USD",
        direction=direction,
        price=Decimal(price),
        min_amount=Decimal("0.01"),
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
