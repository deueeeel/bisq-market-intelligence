from unittest.mock import Mock, patch

import pytest
import requests

from bisq_market_intelligence.client import BisqAPIError, BisqClient
from bisq_market_intelligence.models import InvalidOfferError, Offer


def make_raw_offer(offer_id: str, direction: str, price: str = "100000") -> dict:
    return {
        "offer_id": offer_id,
        "offer_date": 1750000000000,
        "direction": direction,
        "min_amount": "0.01",
        "amount": "0.10",
        "price": price,
        "volume": "10000.00",
        "payment_method": "SEPA",
        "offer_fee_txid": None,
    }


def make_response(json_data=None, status_code=200, raise_exc=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data

    if raise_exc is not None:
        response.raise_for_status.side_effect = raise_exc
    else:
        response.raise_for_status.return_value = None

    return response


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_returns_offers_for_valid_response(mock_get):
    mock_get.return_value = make_response(
        json_data={
            "btc_usd": {
                "buys": [make_raw_offer("buy-1", "BUY")],
                "sells": [make_raw_offer("sell-1", "SELL")],
            }
        }
    )

    client = BisqClient()
    offers = client.get_offers("BTC_USD")

    assert len(offers) == 2
    assert all(isinstance(offer, Offer) for offer in offers)
    assert offers[0].offer_id == "buy-1"
    assert offers[0].direction == "BUY"
    assert offers[1].offer_id == "sell-1"
    assert offers[1].direction == "SELL"


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_raises_invalid_offer_error_on_direction_mismatch(mock_get):
    mock_get.return_value = make_response(
        json_data={
            "btc_usd": {
                "buys": [make_raw_offer("buy-1", "SELL")],
                "sells": [],
            }
        }
    )

    client = BisqClient()

    with pytest.raises(InvalidOfferError, match="expected 'BUY'"):
        client.get_offers("BTC_USD")


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_raises_bisq_api_error_on_http_error(mock_get):
    mock_get.return_value = make_response(
        raise_exc=requests.exceptions.HTTPError("500 Server Error")
    )

    client = BisqClient()

    with pytest.raises(BisqAPIError, match="Failed to fetch offers"):
        client.get_offers("BTC_USD")


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_raises_bisq_api_error_on_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("no route")

    client = BisqClient()

    with pytest.raises(BisqAPIError, match="Failed to fetch offers"):
        client.get_offers("BTC_USD")


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_raises_bisq_api_error_on_missing_market_key(mock_get):
    mock_get.return_value = make_response(json_data={"eth_usd": {"buys": [], "sells": []}})

    client = BisqClient()

    with pytest.raises(BisqAPIError, match="missing 'btc_usd' key"):
        client.get_offers("BTC_USD")


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_raises_bisq_api_error_on_non_dict_payload(mock_get):
    mock_get.return_value = make_response(json_data=None)

    client = BisqClient()

    with pytest.raises(BisqAPIError, match="NoneType"):
        client.get_offers("BTC_USD")


@patch("bisq_market_intelligence.client.requests.get")
def test_get_offers_returns_empty_list_for_market_with_no_offers(mock_get):
    mock_get.return_value = make_response(
        json_data={"xyz_abc": {"buys": [], "sells": []}}
    )

    client = BisqClient()
    offers = client.get_offers("XYZ_ABC")

    assert offers == []
