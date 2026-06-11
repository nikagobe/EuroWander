from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.finances.application.services import FinanceService
from app.modules.finances.infrastructure.repositories import MongoExpenseRepository
from app.modules.finances.presentation.schemas import (
    AddExpenseRequest,
    BalanceResponse,
    DebtResponse,
    ExpenseResponse,
    TripFinanceSummaryResponse,
    UpdateExpenseRequest,
)
from app.modules.trips.application.services import TripService
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/trips/{trip_id}/finances", tags=["finances"])


# ── Dependency factories ──────────────────────────────────────────────────────

def get_finance_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> FinanceService:
    repo = MongoExpenseRepository(db["expenses"])
    return FinanceService(repo)


def get_trip_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TripService:
    repo = MongoTripRepository(db["trips"])
    return TripService(repo)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=TripFinanceSummaryResponse)
async def get_finance_summary(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    finance_service: FinanceService = Depends(get_finance_service),
    trip_service: TripService = Depends(get_trip_service),
) -> TripFinanceSummaryResponse:
    """
    Return the full financial summary for a trip:
    - All expenses (manual + auto-generated from tickets)
    - Per-member net balance (positive = owed money, negative = owes money)
    - Simplified settlement debts (who pays whom how much)
    """
    trip = await trip_service.get_trip(trip_id, current_user.id)
    expenses = await finance_service.list_expenses(trip_id)
    balances, debts = finance_service.calculate_balances(expenses, trip.members)

    return TripFinanceSummaryResponse(
        trip_id=trip_id,
        expenses=[ExpenseResponse.from_entity(e) for e in expenses],
        balances=[BalanceResponse.from_entity(b) for b in balances],
        debts=[DebtResponse.from_entity(d) for d in debts],
    )


@router.get("/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    finance_service: FinanceService = Depends(get_finance_service),
    trip_service: TripService = Depends(get_trip_service),
) -> list[ExpenseResponse]:
    """Return all expenses for the trip. Caller must be a trip member."""
    await trip_service.get_trip(trip_id, current_user.id)  # auth check
    expenses = await finance_service.list_expenses(trip_id)
    return [ExpenseResponse.from_entity(e) for e in expenses]


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def add_expense(
    trip_id: str,
    req: AddExpenseRequest,
    current_user: User = Depends(get_current_user),
    finance_service: FinanceService = Depends(get_finance_service),
    trip_service: TripService = Depends(get_trip_service),
) -> ExpenseResponse:
    """
    Add a manual expense to the trip.
    Any trip member can record an expense.
    """
    await trip_service.get_trip(trip_id, current_user.id)  # auth check
    expense = await finance_service.add_expense(
        trip_id=trip_id,
        name=req.name,
        amount=req.amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )
    return ExpenseResponse.from_entity(expense)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    trip_id: str,
    expense_id: str,
    current_user: User = Depends(get_current_user),
    finance_service: FinanceService = Depends(get_finance_service),
    trip_service: TripService = Depends(get_trip_service),
) -> None:
    """Delete an expense. Any trip member can delete manual expenses."""
    await trip_service.get_trip(trip_id, current_user.id)  # auth check
    await finance_service.delete_expense(expense_id, trip_id)


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    trip_id: str,
    expense_id: str,
    current_user: User = Depends(get_current_user),
    finance_service: FinanceService = Depends(get_finance_service),
    trip_service: TripService = Depends(get_trip_service),
) -> ExpenseResponse:
    """Fetch a single expense by ID. Caller must be a trip member."""
    await trip_service.get_trip(trip_id, current_user.id)  # auth check
    expense = await finance_service.get_expense(expense_id, trip_id)
    return ExpenseResponse.from_entity(expense)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    trip_id: str,
    expense_id: str,
    req: UpdateExpenseRequest,
    current_user: User = Depends(get_current_user),
    finance_service: FinanceService = Depends(get_finance_service),
    trip_service: TripService = Depends(get_trip_service),
) -> ExpenseResponse:
    """
    Edit a manual expense.
    All writable fields must be provided (name, amount, currency, paid_by, eligible_member_ids).
    Ticket-sourced expenses (auto-created from flight/bus payments) cannot be edited here —
    update the ticket payment instead.
    """
    await trip_service.get_trip(trip_id, current_user.id)  # auth check
    expense = await finance_service.update_expense(
        expense_id=expense_id,
        trip_id=trip_id,
        name=req.name,
        amount=req.amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )
    return ExpenseResponse.from_entity(expense)


