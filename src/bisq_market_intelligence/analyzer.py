from bisq_market_intelligence.models import Offer


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
