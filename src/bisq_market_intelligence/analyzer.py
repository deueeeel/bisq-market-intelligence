from dataclasses import dataclass
from decimal import Decimal

from bisq_market_intelligence.models import Offer


class InvalidMarketStateError(ValueError):
    """Raised when market data represents an invalid market state."""


@dataclass(frozen=True)
class ExecutionResult:
    requested_amount: Decimal
    executed_amount: Decimal
    fully_filled: bool
    total_cost: Decimal
    average_execution_price: Decimal | None
    reference_price: Decimal | None
    last_execution_price: Decimal | None
    side: str

    def slippage(self) -> Decimal | None:
        """Return absolute execution slippage."""
        if self.average_execution_price is None:
            return None

        if self.reference_price is None:
            return None

        if self.side == "BUY":
            return self.average_execution_price - self.reference_price

        return self.reference_price - self.average_execution_price

    def slippage_pct(self) -> Decimal | None:
        """Return execution slippage as a percentage."""
        slippage = self.slippage()

        if slippage is None or self.reference_price is None:
            return None

        return slippage / self.reference_price * 100

    def price_impact(self) -> Decimal | None:
        """Return absolute price impact based on the last executed level."""
        if self.last_execution_price is None:
            return None

        if self.reference_price is None:
            return None

        if self.side == "BUY":
            return self.last_execution_price - self.reference_price

        return self.reference_price - self.last_execution_price

    def price_impact_pct(self) -> Decimal | None:
        """Return price impact as a percentage."""
        price_impact = self.price_impact()

        if price_impact is None or self.reference_price is None:
            return None

        return price_impact / self.reference_price * 100


class MarketAnalyzer:
    def __init__(self, offers: list[Offer]) -> None:
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

    def simulate_execution(
        self,
        amount: Decimal,
        side: str,
    ) -> ExecutionResult:
        if amount <= 0:
            raise ValueError("amount must be greater than zero")

        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be 'BUY' or 'SELL'")

        if side == "BUY":
            reference_offer = self.best_ask()

            execution_offers = sorted(
                (
                    offer
                    for offer in self.offers
                    if offer.direction == "SELL"
                ),
                key=lambda offer: (offer.price, offer.timestamp),
            )
        else:
            reference_offer = self.best_bid()

            execution_offers = sorted(
                (
                    offer
                    for offer in self.offers
                    if offer.direction == "BUY"
                ),
                key=lambda offer: (-offer.price, offer.timestamp),
            )

        reference_price = (
            reference_offer.price
            if reference_offer is not None
            else None
        )

        remaining_amount = amount
        executed_amount = Decimal("0")
        total_cost = Decimal("0")
        last_execution_price = None

        for offer in execution_offers:
            if remaining_amount <= 0:
                break

            amount_to_execute = min(
                remaining_amount,
                offer.amount,
            )

            if amount_to_execute < offer.min_amount:
                continue

            executed_amount += amount_to_execute
            total_cost += amount_to_execute * offer.price
            remaining_amount -= amount_to_execute
            last_execution_price = offer.price

        fully_filled = executed_amount == amount

        average_execution_price = (
            total_cost / executed_amount
            if executed_amount > 0
            else None
        )

        return ExecutionResult(
            requested_amount=amount,
            executed_amount=executed_amount,
            fully_filled=fully_filled,
            total_cost=total_cost,
            average_execution_price=average_execution_price,
            reference_price=reference_price,
            last_execution_price=last_execution_price,
            side=side,
        )

    def execution_curve(
        self,
        amounts: list[Decimal],
        side: str,
    ) -> list[ExecutionResult]:
        return [
            self.simulate_execution(amount, side)
            for amount in amounts
        ]
