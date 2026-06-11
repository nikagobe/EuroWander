"""
Finances domain entities.

An Expense represents a payment made during a trip.
It tracks who paid, how much, and which members share the cost.
The FinanceSummary provides a Tricount-style breakdown of who owes whom.
Balances and debts are tracked per currency — no FX conversion is performed.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExpenseSource(str, Enum):
    MANUAL = "manual"    # User-created expense
    TICKET = "ticket"    # Auto-created from a paid flight/bus ticket


@dataclass
class Expense:
    """Pure domain model — no MongoDB or FastAPI awareness."""
    trip_id: str
    name: str                        # e.g. "Dinner at La Boqueria" or "Ryanair FR3122 (outbound)"
    amount: float
    currency: str
    paid_by: str                     # user_id of the person who paid
    eligible_member_ids: list[str]   # user_ids who share this expense (including payer usually)
    source: ExpenseSource = ExpenseSource.MANUAL
    source_ref: str = ""             # flight_id or other reference if source == TICKET
    id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def share_per_member(self) -> float:
        """Each eligible member's equal share of this expense."""
        if not self.eligible_member_ids:
            return 0.0
        return self.amount / len(self.eligible_member_ids)


@dataclass
class CurrencyAmount:
    """A (currency, amount) pair used inside Balance.
    Positive net = this person is owed money in that currency.
    Negative net = this person owes money in that currency.
    """
    currency: str
    net_amount: float


@dataclass
class Balance:
    """Net balance of one member in a trip, split per currency.
    Multiple entries in *amounts* means the member has mixed-currency activity.
    """
    user_id: str
    first_name: str
    last_name: str
    amounts: list[CurrencyAmount]   # one entry per currency that appears in the member's expenses


@dataclass
class Debt:
    """A single simplified debt: *from_user* owes *to_user* the given amount in one currency."""
    from_user_id: str
    from_first_name: str
    from_last_name: str
    to_user_id: str
    to_first_name: str
    to_last_name: str
    amount: float
    currency: str

