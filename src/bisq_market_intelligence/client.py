import requests

from bisq_market_intelligence.models import InvalidOfferError, Offer


class BisqAPIError(Exception):
    """Raised when the Bisq API cannot be reached or returns unexpected data."""


class BisqClient:
    BASE_URL = "https://markets.bisq.network/api"

    def __init__(self, timeout: float = 5):
        self.timeout = timeout

    def get_offers(self, market: str) -> list[Offer]:
        try:
            response = requests.get(
                f"{self.BASE_URL}/offers",
                params={"market": market},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise BisqAPIError(
                f"Failed to fetch offers from Bisq API: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BisqAPIError(f"Bisq API returned invalid JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise BisqAPIError(
                f"Unexpected response type: {type(payload).__name__}"
            )

        market_key = market.lower()

        if market_key not in payload:
            raise BisqAPIError(
                f"Unexpected response structure: missing '{market_key}' key"
            )

        market_data = payload[market_key]

        if "buys" not in market_data or "sells" not in market_data:
            raise BisqAPIError(
                "Unexpected response structure: missing 'buys' or 'sells'"
            )

        offers: list[Offer] = []

        for data in market_data["buys"]:
            if data.get("direction") != "BUY":
                raise InvalidOfferError(
                    f"Offer {data.get('offer_id')} in 'buys' has direction "
                    f"'{data.get('direction')}', expected 'BUY'"
                )
            offers.append(Offer.from_json(data, market))

        for data in market_data["sells"]:
            if data.get("direction") != "SELL":
                raise InvalidOfferError(
                    f"Offer {data.get('offer_id')} in 'sells' has direction "
                    f"'{data.get('direction')}', expected 'SELL'"
                )
            offers.append(Offer.from_json(data, market))

        return offers
