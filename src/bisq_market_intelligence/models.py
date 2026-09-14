from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


class InvalidOfferError(ValueError):
    """Raised when a Bisq offer is missing or contains invalid data."""


@dataclass(frozen=True)
class Offer:
    offer_id: str
    timestamp: datetime
    market: str
    direction: str
    price: Decimal
    min_amount: Decimal
    amount: Decimal
    volume: Decimal
    payment_method: str

    @classmethod
    def from_json(cls, data: dict, market: str) -> "Offer":
        required_fields = {
            "offer_id", "offer_date", "direction", "min_amount",
            "amount", "price", "volume", "payment_method",
        }

        for field in sorted(required_fields):
            if field not in data:
                raise InvalidOfferError(f"Missing required field '{field}'")
            if data[field] is None:
                raise InvalidOfferError(f"Required field '{field}' cannot be null")

        try:
            timestamp = datetime.fromtimestamp(
                int(data["offer_date"]) / 1000, tz=timezone.utc,
            )
            return cls(
                offer_id=data["offer_id"],
                timestamp=timestamp,
                market=market,
                direction=data["direction"],
                price=Decimal(str(data["price"])),
                min_amount=Decimal(str(data["min_amount"])),
                amount=Decimal(str(data["amount"])),
                volume=Decimal(str(data["volume"])),
                payment_method=data["payment_method"],
            )
        except (ValueError, TypeError, OverflowError, InvalidOperation) as exc:
            raise InvalidOfferError(f"Invalid data in Bisq offer: {exc}") from exc
