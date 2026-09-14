from datetime import datetime, timezone
from decimal import Decimal

import pytest

from bisq_market_intelligence.models import InvalidOfferError, Offer


@pytest.fixture
def valid_offer_data() -> dict:
    return {
        "offer_id": "offer-123",
        "offer_date": "1750000000000",
        "direction": "BUY",
        "min_amount": "0.01",
        "amount": "0.10",
        "price": "100000.00",
        "volume": "10000.00",
        "payment_method": "SEPA",
    }


def test_from_json_creates_offer_with_decimal_fields(valid_offer_data):
    offer = Offer.from_json(valid_offer_data, market="BTC_USD")

    assert isinstance(offer, Offer)
    assert offer.offer_id == "offer-123"
    assert offer.market == "BTC_USD"
    assert offer.direction == "BUY"
    assert offer.price == Decimal("100000.00")
    assert offer.min_amount == Decimal("0.01")
    assert offer.amount == Decimal("0.10")
    assert offer.volume == Decimal("10000.00")


def test_from_json_raises_when_required_field_is_missing(valid_offer_data):
    del valid_offer_data["price"]

    with pytest.raises(
        InvalidOfferError,
        match="Missing required field 'price'",
    ):
        Offer.from_json(valid_offer_data, market="BTC_USD")


def test_from_json_raises_when_required_field_is_null(valid_offer_data):
    valid_offer_data["price"] = None

    with pytest.raises(
        InvalidOfferError,
        match="Required field 'price' cannot be null",
    ):
        Offer.from_json(valid_offer_data, market="BTC_USD")


def test_from_json_raises_when_price_is_invalid(valid_offer_data):
    valid_offer_data["price"] = "not-a-number"

    with pytest.raises(
        InvalidOfferError,
        match="Invalid data in Bisq offer:",
    ):
        Offer.from_json(valid_offer_data, market="BTC_USD")


def test_from_json_converts_offer_date_from_milliseconds(valid_offer_data):
    offer = Offer.from_json(valid_offer_data, market="BTC_USD")

    expected_timestamp = datetime.fromtimestamp(
        1750000000000 / 1000,
        tz=timezone.utc,
    )

    assert offer.timestamp == expected_timestamp
    assert offer.timestamp.tzinfo == timezone.utc
