"""Service layer with business logic for bank accounts."""

from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Compte, TypeCompte
from app.repositories import CompteRepository
from app.schemas import CompteCreate, CompteUpdate


class InsufficientFundsError(Exception):
    """Raised when withdrawal exceeds available balance."""

    pass


class NegativeBalanceError(Exception):
    """Raised when EPARGNE account would have negative balance."""

    pass


class InvalidAmountError(Exception):
    """Raised when transaction amount is invalid (zero or negative)."""

    pass


class CompteNotFoundError(Exception):
    """Raised when compte is not found."""

    pass


class CompteService:
    """Business logic for managing bank accounts."""

    def __init__(self, session: AsyncSession):
        self.repository = CompteRepository(session)

    async def get_all(self) -> List[Compte]:
        """Get all accounts."""
        return await self.repository.get_all()

    async def get_by_id(self, compte_id: str) -> Compte:
        """Get account by ID."""
        compte = await self.repository.get_by_id(compte_id)
        if not compte:
            raise CompteNotFoundError(f"Compte with id {compte_id} not found")
        return compte

    async def create(self, compte_dto: CompteCreate) -> Compte:
        """Create new account with business rules validation."""
        # Validate: EPARGNE accounts cannot start with negative balance
        if compte_dto.type == TypeCompte.EPARGNE and compte_dto.solde < 0:
            raise NegativeBalanceError("EPARGNE accounts cannot have negative balance")

        from app.mappers.compte_mapper import CompteMapper

        compte = CompteMapper.to_entity(compte_dto)
        return await self.repository.create(compte)

    async def update(self, compte_id: str, compte_dto: CompteUpdate) -> Compte:
        """Update existing account with validation."""
        compte = await self.get_by_id(compte_id)

        # If updating balance on EPARGNE, validate it's not negative
        new_solde = compte_dto.solde if compte_dto.solde is not None else compte.solde
        compte_type = compte_dto.type if compte_dto.type is not None else compte.type

        if compte_type == TypeCompte.EPARGNE and new_solde < 0:
            raise NegativeBalanceError("EPARGNE accounts cannot have negative balance")

        from app.mappers.compte_mapper import CompteMapper

        updated = CompteMapper.update_entity(compte, compte_dto)
        return await self.repository.update(updated)

    async def delete(self, compte_id: str) -> None:
        """Delete account."""

        if await self.repository.delete(compte_id):
            return
        raise CompteNotFoundError(f"Compte with id {compte_id} not found")

    async def find_by_type(self, type_compte: TypeCompte) -> List[Compte]:
        """Find accounts by type."""
        return await self.repository.find_by_type(type_compte)

    async def find_by_solde_range(
        self, min_solde: Optional[float] = None, max_solde: Optional[float] = None
    ) -> List[Compte]:
        """Find accounts by balance range."""
        return await self.repository.find_by_solde_range(min_solde, max_solde)

    async def deposit(self, compte_id: str, amount: float) -> Compte:
        """Deposit money into account."""
        if amount <= 0:
            raise InvalidAmountError("Deposit amount must be positive")

        compte = await self.get_by_id(compte_id)
        compte.solde += amount
        return await self.repository.update(compte)

    async def withdraw(self, compte_id: str, amount: float) -> Compte:
        """Withdraw money from account."""
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive")

        compte = await self.get_by_id(compte_id)

        # Check insufficient funds
        if compte.solde < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. Balance: {compte.solde}, Requested: {amount}"
            )

        new_balance = compte.solde - amount

        # EPARGNE accounts cannot go negative
        if compte.type == TypeCompte.EPARGNE and new_balance < 0:
            raise NegativeBalanceError("EPARGNE accounts cannot have negative balance")

        compte.solde = new_balance
        return await self.repository.update(compte)
