# app/routers/compte_router.py

from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database import get_session

from app.services.compte_service import (
    CompteService,
    CompteNotFoundError,
    InvalidAmountError,
    NegativeBalanceError,
    InsufficientFundsError,
)


from app.schemas.compte import (
    CompteCreate,
    CompteUpdate,
    CompteResponse,
    CompteSummary,
    CompteMinimal,
    TypeCompte,
    TransactionRequest, 
)

router = APIRouter()


# Dependency function to get the Service Layer instance
async def get_compte_service(
    session: AsyncSession = Depends(get_session),
) -> CompteService:
    return CompteService(session=session)


# Utility to select response model based on projection
def get_response_model(projection: str):
    if projection == "minimal":
        return CompteMinimal
    if projection == "summary":
        return CompteSummary
    return CompteResponse 


# ----------------------------------------------------
# 1. GET /comptes - list all (with projection query param)
# ----------------------------------------------------
@router.get("/", response_model=List[Union[CompteResponse, CompteSummary, CompteMinimal]])
async def list_comptes(
    service: CompteService = Depends(get_compte_service),
    projection: str = Query(
        "full", enum=["minimal", "summary", "full"], description="Response detail level"
    ),
):
    """List all bank accounts with optional projection."""
    comptes = await service.get_all()

    # Simple mapping/read conversion using the appropriate schema
    Model = get_response_model(projection)
    # Using Model.model_validate to convert the ORM entity (Compte) into the Pydantic response schema
    return [Model.model_validate(c) for c in comptes]


# ----------------------------------------------------
# 6. GET /comptes/search - filter by type, solde range
# ----------------------------------------------------
@router.get("/search", response_model=List[CompteResponse])
async def search_comptes(
    service: CompteService = Depends(get_compte_service),
    type: Optional[TypeCompte] = Query(None, description="Filter by account type"),
    min_solde: Optional[float] = Query(None, description="Minimum balance"),
    max_solde: Optional[float] = Query(None, description="Maximum balance"),
):
    """Search accounts by type or balance range."""

    if type:
        return await service.find_by_type(type)

    if min_solde is not None or max_solde is not None:
        return await service.find_by_solde_range(
            min_solde=min_solde, max_solde=max_solde
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Must provide at least one search criterion (type, min_solde, or max_solde)",
    )

# ----------------------------------------------------
# 2. GET /comptes/{id} - get by ID
# ----------------------------------------------------
@router.get("/{compte_id}", response_model=CompteResponse)
async def get_compte_by_id(
    compte_id: str, service: CompteService = Depends(get_compte_service)
):
    """Retrieve a single bank account by its ID."""
    try:
        compte = await service.get_by_id(compte_id)
        return (
            compte  # Returns Compte entity, which will be validated by CompteResponse
        )
    except CompteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ----------------------------------------------------
# 3. POST /comptes - create account
# ----------------------------------------------------
@router.post("/", response_model=CompteResponse, status_code=status.HTTP_201_CREATED)
async def create_compte(
    compte_in: CompteCreate, service: CompteService = Depends(get_compte_service)
):
    """Create a new bank account."""
    try:
        compte = await service.create(compte_in)
        return compte
    except NegativeBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )

# ----------------------------------------------------
# 4. PUT /comptes/{id} - update account
# ----------------------------------------------------
@router.put("/{compte_id}", response_model=CompteResponse)
async def update_compte(
    compte_id: str,
    compte_in: CompteUpdate,
    service: CompteService = Depends(get_compte_service),
):
    """Update an existing bank account."""
    try:
        compte = await service.update(compte_id, compte_in)
        return compte
    except CompteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NegativeBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


# ----------------------------------------------------
# 5. DELETE /comptes/{id} - delete account
# ----------------------------------------------------
@router.delete("/{compte_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compte(
    compte_id: str, service: CompteService = Depends(get_compte_service)
):
    """Delete a bank account by ID."""
    try:
        await service.delete(compte_id)
        return
    except CompteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ----------------------------------------------------
# 7. POST /comptes/{id}/deposit - deposit money
# ----------------------------------------------------
@router.post("/{compte_id}/deposit", response_model=CompteResponse)
async def deposit_money(
    compte_id: str,
    transaction_in: TransactionRequest,  # 🚨 CORRECTED: Use TransactionRequest schema
    service: CompteService = Depends(get_compte_service),
):
    """Deposit money into the specified account."""
    try:
        compte = await service.deposit(compte_id, transaction_in.amount)
        return compte
    except CompteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidAmountError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


# ----------------------------------------------------
# 8. POST /comptes/{id}/withdraw - withdraw money
# ----------------------------------------------------
@router.post("/{compte_id}/withdraw", response_model=CompteResponse)
async def withdraw_money(
    compte_id: str,
    transaction_in: TransactionRequest,  # 🚨 CORRECTED: Use TransactionRequest schema
    service: CompteService = Depends(get_compte_service),
):
    """Withdraw money from the specified account."""
    try:
        compte = await service.withdraw(compte_id, transaction_in.amount)
        return compte
    except CompteNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidAmountError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except NegativeBalanceError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
