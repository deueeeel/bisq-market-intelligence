from decimal import Decimal

from bisq_market_intelligence.models import Offer


class InvalidMarketStateError(ValueError):
    """Raised when market data represents an invalid market state."""


class MarketAnalyzer:
    def __init__(self, offers: list[Offer]):
        self.offers = offers

    def best_bid(self) -> Offer | None:
        buy_offers = [
            offer
            for offer in self.offers
            if offer.direction == "BUY"
        ]

        if not buy_offers:
            return None

        return max(buy_offers, key=lambda offer: offer.price)

    def best_ask(self) -> Offer | None:
        sell_offers = [
            offer
            for offer in self.offers
            if offer.direction == "SELL"
        ]

        if not sell_offers:
            return None

        return min(sell_offers, key=lambda offer: offer.price)

    def _best_pair(self) -> tuple[Offer, Offer] | None:
        best_bid = self.best_bid()
        best_ask = self.best_ask()

        if best_bid is None or best_ask is None:
            return None

        return best_bid, best_ask

    def mid_price(self) -> Decimal | None:
        best_pair = self._best_pair()

        if best_pair is None:
            return None

        best_bid, best_ask = best_pair

        return (best_bid.price + best_ask.price) / 2

    def spread(self) -> Decimal | None:
        best_pair = self._best_pair()

        if best_pair is None:
            return None

        best_bid, best_ask = best_pair

        return best_ask.price - best_bid.price

    def spread_pct(self) -> Decimal | None:
        spread = self.spread()

        if spread is None:
            return None

        mid_price = self.mid_price()

        if mid_price is None:
            return None

        if mid_price == 0:
            raise InvalidMarketStateError(
                "Cannot calculate spread percentage with a zero mid-price"
            )

        return (spread / mid_price) * 100
