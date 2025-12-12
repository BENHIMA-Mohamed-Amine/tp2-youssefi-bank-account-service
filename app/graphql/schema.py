import strawberry
from typing import List, Optional
from strawberry.types import Info

# Import your Service and Pydantic Schemas
from app.services.compte_service import CompteService
from app.schemas.compte import CompteCreate, CompteUpdate

# Import the GraphQL Types
from app.graphql.types import CompteType, CompteCreateInput, CompteUpdateInput
from app.models.compte import TypeCompte as EnumTypeCompte


# --- READ OPERATIONS (Queries) ---
@strawberry.type
class Query:
    @strawberry.field
    async def get_all_comptes(
        self,
        info: Info,
        type: Optional[EnumTypeCompte] = None,
        min_solde: Optional[float] = None,
        max_solde: Optional[float] = None,
    ) -> List[CompteType]:
        """
        Fetch accounts with optional filtering.
        Logic: Prioritizes Type search, then Range search, then returns All.
        """
        session = info.context["session"]
        service = CompteService(session)

        # 1. Search by Type
        if type:
            return await service.find_by_type(type)

        # 2. Search by Balance Range
        if min_solde is not None or max_solde is not None:
            return await service.find_by_solde_range(min_solde, max_solde)

        # 3. Default: Return All
        return await service.get_all()

    @strawberry.field
    async def get_compte(self, info: Info, id: str) -> Optional[CompteType]:
        """Fetch a specific account by ID."""
        session = info.context["session"]
        service = CompteService(session)
        try:
            return await service.get_by_id(id)
        except Exception:
            return None


# --- WRITE OPERATIONS (Mutations) ---
@strawberry.type
class Mutation:
    @strawberry.field
    async def create_compte(self, info: Info, input: CompteCreateInput) -> CompteType:
        """Create a new account."""
        session = info.context["session"]
        service = CompteService(session)

        compte_dto = CompteCreate(
            solde=input.solde, type=input.type, devise=input.devise
        )
        return await service.create(compte_dto)

    @strawberry.field
    async def update_compte(
        self, info: Info, id: str, input: CompteUpdateInput
    ) -> CompteType:
        """Update generic account details."""
        session = info.context["session"]
        service = CompteService(session)

        compte_dto = CompteUpdate(
            solde=input.solde, type=input.type, devise=input.devise
        )
        return await service.update(id, compte_dto)

    @strawberry.field
    async def delete_compte(self, info: Info, id: str) -> str:
        """Delete an account."""
        session = info.context["session"]
        service = CompteService(session)

        await service.delete(id)
        return f"Compte {id} deleted successfully"

    # --- Domain Specific Mutations ---

    @strawberry.field
    async def deposit(self, info: Info, id: str, amount: float) -> CompteType:
        """Add money to an account."""
        session = info.context["session"]
        service = CompteService(session)
        return await service.deposit(id, amount)

    @strawberry.field
    async def withdraw(self, info: Info, id: str, amount: float) -> CompteType:
        """Remove money from an account (with validation)."""
        session = info.context["session"]
        service = CompteService(session)
        return await service.withdraw(id, amount)


# Final Schema Assembly
schema = strawberry.Schema(query=Query, mutation=Mutation)
