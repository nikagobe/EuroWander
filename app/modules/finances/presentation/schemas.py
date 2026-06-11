from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.finances.domain.entities import (
    Balance,
    CurrencyAmount,
    Debt,
    Expense,
    ExpenseSource,
)


# ── Request schemas ───────────────────────────────────────────────────────────

class AddExpenseRequest(BaseModel):
    name: str
    amount: float
    currency: str = "EUR"
    paid_by: str
    eligible_member_ids: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Dinner at La Boqueria",
                "amount": 64.80,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": [
                    "664abc123def456789012345",
                    "664abc123def456789099999",
                ],
            }
        }
    )


class UpdateExpenseRequest(BaseModel):
    """
    Patch a manual expense. All fields are required — send the full updated state.
    Ticket-sourced expenses (auto-created from flight/bus payments) cannot be
    edited here; update the ticket payment instead.
    """
    name: str
    amount: float
    currency: str = "EUR"
    paid_by: str
    eligible_member_ids: list[str]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Dinner at La Boqueria (corrected)",
                "amount": 72.00,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": [
                    "664abc123def456789012345",
                    "664abc123def456789099999",
                ],
            }
        }
    )


# ── Response schemas ──────────────────────────────────────────────────────────

class CurrencyAmountResponse(BaseModel):
    currency: str
    net_amount: float

    @classmethod
    def from_entity(cls, ca: CurrencyAmount) -> "CurrencyAmountResponse":
        return cls(currency=ca.currency, net_amount=ca.net_amount)


class ExpenseResponse(BaseModel):
    id: str
    trip_id: str
    name: str
    amount: float
    currency: str
    paid_by: str
    eligible_member_ids: list[str]
    share_per_member: float
    source: ExpenseSource
    source_ref: str
    created_at: datetime

    @classmethod
    def from_entity(cls, e: Expense) -> "ExpenseResponse":
        return cls(
            id=e.id,
            trip_id=e.trip_id,
            name=e.name,
            amount=e.amount,
            currency=e.currency,
            paid_by=e.paid_by,
            eligible_member_ids=e.eligible_member_ids,
            share_per_member=round(e.share_per_member, 2),
            source=e.source,
            source_ref=e.source_ref,
            created_at=e.created_at,
        )


class BalanceResponse(BaseModel):
    """
    Per-user balance broken down by currency.

    Each entry in *net_by_currency* represents the user's net position in one currency:
      - positive → they are owed that amount by others
      - negative → they owe that amount to others

    Example: Alice paid €120 for flights and £35 for a museum — two separate entries.
    """
    user_id: str
    first_name: str
    last_name: str
    net_by_currency: list[CurrencyAmountResponse]

    @classmethod
    def from_entity(cls, b: Balance) -> "BalanceResponse":
        return cls(
            user_id=b.user_id,
            first_name=b.first_name,
            last_name=b.last_name,
            net_by_currency=[CurrencyAmountResponse.from_entity(ca) for ca in b.amounts],
        )


class DebtResponse(BaseModel):
    from_user_id: str
    from_first_name: str
    from_last_name: str
    to_user_id: str
    to_first_name: str
    to_last_name: str
    amount: float
    currency: str

    @classmethod
    def from_entity(cls, d: Debt) -> "DebtResponse":
        return cls(
            from_user_id=d.from_user_id,
            from_first_name=d.from_first_name,
            from_last_name=d.from_last_name,
            to_user_id=d.to_user_id,
            to_first_name=d.to_first_name,
            to_last_name=d.to_last_name,
            amount=d.amount,
            currency=d.currency,
        )


class TripFinanceSummaryResponse(BaseModel):
    """Full financial picture for a trip: all expenses, per-user balances, simplified debts."""
    trip_id: str
    expenses: list[ExpenseResponse]
    balances: list[BalanceResponse]
    debts: list[DebtResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": "664abc123def456789012345",
                "expenses": [],
                "balances": [
                    {
                        "user_id": "...",
                        "first_name": "Alice",
                        "last_name": "B",
                        "net_by_currency": [
                            {"currency": "EUR", "net_amount": 32.40},
                            {"currency": "GBP", "net_amount": -10.00},
                        ],
                    }
                ],
                "debts": [
                    {
                        "from_user_id": "...", "from_first_name": "Bob", "from_last_name": "C",
                        "to_user_id": "...", "to_first_name": "Alice", "to_last_name": "B",
                        "amount": 32.40, "currency": "EUR",
                    }
                ],
            }
        }
    )

