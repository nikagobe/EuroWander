"""
Finance application service.

Handles expense CRUD and Tricount-style balance calculation.
"""

from fastapi import HTTPException, status

from app.modules.finances.domain.entities import (
    Balance,
    CurrencyAmount,
    Debt,
    Expense,
    ExpenseSource,
)
from app.modules.finances.domain.interfaces import ExpenseRepository
from app.modules.trips.domain.entities import TripMember


class FinanceService:
    def __init__(self, repo: ExpenseRepository) -> None:
        self._repo = repo

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def add_expense(
        self,
        trip_id: str,
        name: str,
        amount: float,
        currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
        source: ExpenseSource = ExpenseSource.MANUAL,
        source_ref: str = "",
    ) -> Expense:
        expense = Expense(
            trip_id=trip_id,
            name=name,
            amount=amount,
            currency=currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
            source=source,
            source_ref=source_ref,
        )
        return await self._repo.create(expense)

    async def upsert_ticket_expense(
        self,
        trip_id: str,
        name: str,
        amount: float,
        currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
        source_ref: str,
    ) -> Expense:
        """Create or replace the expense linked to a ticket (identified by source_ref = flight_id)."""
        existing = await self._repo.get_by_source_ref(trip_id, source_ref)
        if existing:
            # Delete stale entry so we replace it cleanly
            await self._repo.delete(existing.id, trip_id)
        return await self.add_expense(
            trip_id=trip_id,
            name=name,
            amount=amount,
            currency=currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
            source=ExpenseSource.TICKET,
            source_ref=source_ref,
        )

    async def list_expenses(self, trip_id: str) -> list[Expense]:
        return await self._repo.list_by_trip(trip_id)

    async def get_expense(self, expense_id: str, trip_id: str) -> Expense:
        """Fetch a single expense and verify it belongs to the given trip."""
        expense = await self._repo.get_by_id(expense_id)
        if expense is None or expense.trip_id != trip_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found.",
            )
        return expense

    async def update_expense(
        self,
        expense_id: str,
        trip_id: str,
        name: str,
        amount: float,
        currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> Expense:
        """
        Edit a manual expense's mutable fields.
        Ticket-sourced expenses cannot be edited directly — they are managed
        automatically when a ticket's payment info is updated.
        """
        expense = await self.get_expense(expense_id, trip_id)
        if expense.source == ExpenseSource.TICKET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ticket expenses are managed automatically. "
                       "Update the ticket payment info instead.",
            )
        found = await self._repo.update(
            expense_id=expense_id,
            trip_id=trip_id,
            name=name,
            amount=amount,
            currency=currency,
            paid_by=paid_by,
            eligible_member_ids=eligible_member_ids,
        )
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found.",
            )
        return await self.get_expense(expense_id, trip_id)

    async def delete_expense(self, expense_id: str, trip_id: str) -> None:
        deleted = await self._repo.delete(expense_id, trip_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found.",
            )

    # ── Balance calculation ───────────────────────────────────────────────────

    def calculate_balances(
        self,
        expenses: list[Expense],
        members: list[TripMember],
    ) -> tuple[list[Balance], list[Debt]]:
        """
        Tricount-style balance computation with full per-currency ledgers.

        For each expense (in whatever currency it was recorded):
          - paid_by person is credited +amount in that currency
          - each eligible member is debited -(amount / count) in that currency

        No FX conversion is done. Balances and simplified debts are returned
        per currency so the Flutter client can display them correctly.

        Returns:
            balances  — one Balance per user, each holding a list of
                        (currency, net_amount) pairs (non-zero only)
            debts     — simplified settlement transfers, one per
                        (debtor → creditor, currency) triplet
        """
        member_map: dict[str, TripMember] = {m.user_id: m for m in members}

        # ledger[user_id][currency] = net float
        ledger: dict[str, dict[str, float]] = {}

        def _credit(uid: str, currency: str, amount: float) -> None:
            ledger.setdefault(uid, {})
            ledger[uid][currency] = ledger[uid].get(currency, 0.0) + amount

        # Seed every trip member so they always appear in balances
        for m in members:
            ledger.setdefault(m.user_id, {})

        for expense in expenses:
            ccy = expense.currency
            _credit(expense.paid_by, ccy, expense.amount)
            if expense.eligible_member_ids:
                share = expense.amount / len(expense.eligible_member_ids)
                for uid in expense.eligible_member_ids:
                    _credit(uid, ccy, -share)

        def _name(uid: str) -> tuple[str, str]:
            m = member_map.get(uid)
            return (m.first_name, m.last_name) if m else ("", "")

        balances: list[Balance] = []
        for uid, ccy_map in ledger.items():
            amounts = [
                CurrencyAmount(currency=ccy, net_amount=round(amt, 2))
                for ccy, amt in ccy_map.items()
                if abs(amt) >= 0.005  # skip dust
            ]
            first, last = _name(uid)
            balances.append(Balance(
                user_id=uid,
                first_name=first,
                last_name=last,
                amounts=amounts,
            ))

        # Collect all currencies that appear in the ledger, run simplification per currency
        all_currencies: set[str] = {e.currency for e in expenses}
        debts: list[Debt] = []
        for ccy in all_currencies:
            net_for_ccy = {uid: ccy_map.get(ccy, 0.0) for uid, ccy_map in ledger.items()}
            debts.extend(self._simplify_debts(net_for_ccy, member_map, ccy))

        return balances, debts

    @staticmethod
    def _simplify_debts(
        net: dict[str, float],
        member_map: dict[str, TripMember],
        currency: str,
    ) -> list[Debt]:
        """
        Greedy debt simplification for a single currency:
        Repeatedly match the largest debtor against the largest creditor
        until all balances are settled.
        """
        creditors: list[list] = sorted(
            [[uid, amt] for uid, amt in net.items() if amt > 0.005],
            key=lambda x: x[1],
            reverse=True,
        )
        debtors: list[list] = sorted(
            [[uid, -amt] for uid, amt in net.items() if amt < -0.005],
            key=lambda x: x[1],
            reverse=True,
        )

        debts: list[Debt] = []
        ci, di = 0, 0

        def _name(uid: str) -> tuple[str, str]:
            m = member_map.get(uid)
            return (m.first_name, m.last_name) if m else ("", "")

        while ci < len(creditors) and di < len(debtors):
            cid, c_amt = creditors[ci]
            did, d_amt = debtors[di]

            settle = round(min(c_amt, d_amt), 2)
            if settle < 0.01:
                break

            debts.append(Debt(
                from_user_id=did,
                from_first_name=_name(did)[0],
                from_last_name=_name(did)[1],
                to_user_id=cid,
                to_first_name=_name(cid)[0],
                to_last_name=_name(cid)[1],
                amount=settle,
                currency=currency,
            ))

            c_amt -= settle
            d_amt -= settle
            creditors[ci][1] = c_amt
            debtors[di][1] = d_amt

            if c_amt < 0.01:
                ci += 1
            if d_amt < 0.01:
                di += 1

        return debts

