from abc import ABC, abstractmethod

from app.modules.finances.domain.entities import Expense


class ExpenseRepository(ABC):
    @abstractmethod
    async def create(self, expense: Expense) -> Expense: ...

    @abstractmethod
    async def get_by_id(self, expense_id: str) -> Expense | None: ...

    @abstractmethod
    async def list_by_trip(self, trip_id: str) -> list[Expense]: ...

    @abstractmethod
    async def delete(self, expense_id: str, trip_id: str) -> bool: ...

    @abstractmethod
    async def update(
        self,
        expense_id: str,
        trip_id: str,
        name: str,
        amount: float,
        currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> bool:
        """Overwrite the mutable fields of an expense. Returns False if not found."""
        ...

    @abstractmethod
    async def get_by_source_ref(self, trip_id: str, source_ref: str) -> Expense | None:
        """Find a ticket-sourced expense by its source_ref (flight_id). Used for upsert."""
        ...

