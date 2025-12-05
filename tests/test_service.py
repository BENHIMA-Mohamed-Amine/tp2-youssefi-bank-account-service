import pytest
import pytest_asyncio
import uuid
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import all necessary components from the application
from app.models.compte import Compte, TypeCompte
from app.repositories.compte_repository import CompteRepository
from app.schemas.compte import CompteCreate, CompteUpdate
from app.services.compte_service import (
    CompteService,
    CompteNotFoundError,
    NegativeBalanceError,
    InvalidAmountError,
)

# --- 1. Fixtures to mimic test_repository.py environment ---


@pytest_asyncio.fixture
async def test_session():
    """Provides an isolated, in-memory SQLite AsyncSession for testing."""
    # Use :memory: for in-memory SQLite
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        # Create all tables in the memory database
        await conn.run_sync(SQLModel.metadata.create_all)

    # Setup the async session maker
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Yield the session for tests to use
    async with async_session() as session:
        yield session

    # Dispose of the engine resources after testing
    await engine.dispose()


@pytest_asyncio.fixture
async def repository(test_session):
    """Provides a real CompteRepository instance using the test session."""
    return CompteRepository(test_session)


@pytest_asyncio.fixture
async def compte_service(test_session):
    """Provides a real CompteService instance using the test session."""
    # The CompteService internally creates a CompteRepository with the session
    return CompteService(test_session)


# --- 2. Fixtures for Test Data ---


@pytest_asyncio.fixture
async def setup_initial_accounts(repository: CompteRepository):
    """Creates initial accounts for testing transactional methods."""
    courant = Compte(type=TypeCompte.COURANT, solde=1000.0)
    epargne = Compte(type=TypeCompte.EPARGNE, solde=500.0)

    courant = await repository.create(courant)
    epargne = await repository.create(epargne)

    return {"courant": courant, "epargne": epargne}


# --- 3. Tests for Basic CRUD Operations ---


@pytest.mark.asyncio
async def test_get_all_success(compte_service: CompteService):
    """Test getting all accounts when none exist."""
    result = await compte_service.get_all()
    assert len(result) == 0

    # Test after creating accounts
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    await compte_service.create(create_dto)
    result = await compte_service.get_all()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_by_id_success(compte_service: CompteService):
    """Test getting an account by ID successfully."""
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    created = await compte_service.create(create_dto)

    found = await compte_service.get_by_id(created.id)
    assert found.id == created.id
    assert found.solde == 100.0


@pytest.mark.asyncio
async def test_get_by_id_not_found(compte_service: CompteService):
    """Test getting an account by ID when it does not exist (CompteNotFoundError)."""
    with pytest.raises(CompteNotFoundError):
        await compte_service.get_by_id(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_create_success(compte_service: CompteService):
    """Test successful account creation."""
    create_dto = CompteCreate(solde=500.0, type=TypeCompte.EPARGNE, devise="EUR")
    created = await compte_service.create(create_dto)

    assert created.id is not None
    assert created.solde == 500.0
    assert created.type == TypeCompte.EPARGNE


@pytest.mark.asyncio
async def test_update_success(compte_service: CompteService):
    """Test successful account update."""
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    created = await compte_service.create(create_dto)

    update_dto = CompteUpdate(solde=200.0)
    updated = await compte_service.update(created.id, update_dto)

    assert updated.solde == 200.0


@pytest.mark.asyncio
async def test_delete_success(compte_service: CompteService):
    """Test successful account deletion."""
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    created = await compte_service.create(create_dto)

    await compte_service.delete(created.id)

    with pytest.raises(CompteNotFoundError):
        await compte_service.get_by_id(created.id)


@pytest.mark.asyncio
async def test_delete_not_found(compte_service: CompteService):
    """Test deleting a non-existent account (CompteNotFoundError)."""
    with pytest.raises(CompteNotFoundError):
        await compte_service.delete(str(uuid.uuid4()))


# --- 4. Tests for Business Rules and Exceptions (Creation/Update) ---


@pytest.mark.asyncio
async def test_create_epargne_negative_balance_raises_error(
    compte_service: CompteService,
):
    """Rule 1: EPARGNE accounts cannot be created with a negative initial balance."""
    negative_dto = CompteCreate(solde=-10.0, type=TypeCompte.EPARGNE, devise="MAD")

    with pytest.raises(NegativeBalanceError):
        await compte_service.create(negative_dto)

    # Ensure no account was actually saved
    accounts = await compte_service.get_all()
    assert len(accounts) == 0


@pytest.mark.asyncio
async def test_update_epargne_to_negative_balance_raises_error(
    compte_service: CompteService,
):
    """Rule 1: EPARGNE accounts cannot be updated to have a negative balance."""
    # 1. Create a valid EPARGNE account
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.EPARGNE, devise="MAD")
    epargne = await compte_service.create(create_dto)

    # 2. Attempt to update the balance to a negative value
    update_dto = CompteUpdate(solde=-10.0)

    with pytest.raises(NegativeBalanceError):
        await compte_service.update(epargne.id, update_dto)

    # 3. Verify the balance was not changed in the database
    current_state = await compte_service.get_by_id(epargne.id)
    assert current_state.solde == 100.0


# --- 5. Tests for Transaction Logic (Deposit/Withdraw) ---


@pytest.mark.asyncio
async def test_deposit_success(compte_service: CompteService):
    """Test successful deposit operation."""
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    account = await compte_service.create(create_dto)

    deposit_amount = 50.0
    updated = await compte_service.deposit(account.id, deposit_amount)

    assert updated.solde == 150.0


@pytest.mark.asyncio
async def test_deposit_invalid_amount_raises_error(compte_service: CompteService):
    """Rule 3: Deposit amount must be positive."""
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    account = await compte_service.create(create_dto)

    with pytest.raises(InvalidAmountError):
        await compte_service.deposit(account.id, 0.0)

    # Verify balance is unchanged
    current_state = await compte_service.get_by_id(account.id)
    assert current_state.solde == 100.0


@pytest.mark.asyncio
async def test_withdraw_success_courant_to_negative(compte_service: CompteService):
    """Test successful withdrawal from a COURANT account (can go negative)."""
    create_dto = CompteCreate(solde=1000.0, type=TypeCompte.COURANT, devise="MAD")
    courant = await compte_service.create(create_dto)

    withdraw_amount = 1200.0
    updated = await compte_service.withdraw(courant.id, withdraw_amount)

    assert updated.solde == -200.0


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds_courant_success_overdraft(
    compte_service: CompteService,
):
    """Test successful withdrawal leading to negative balance (overdraft) for COURANT."""
    create_dto = CompteCreate(solde=100.0, type=TypeCompte.COURANT, devise="MAD")
    account = await compte_service.create(create_dto)

    withdraw_amount = 100.01  # Withdrawal that causes overdraft

    # We expect a successful update, NOT an exception
    updated = await compte_service.withdraw(account.id, withdraw_amount)

    assert updated.solde == pytest.approx(
        -0.01
    )  # Use pytest.approx for floating point comparisons

    # Check the database state to be sure
    current_state = await compte_service.get_by_id(account.id)
    assert current_state.solde == pytest.approx(-0.01)


@pytest.mark.asyncio
async def test_withdraw_epargne_negative_balance_raises_error(
    compte_service: CompteService,
):
    """Rule 1: EPARGNE accounts cannot have negative balance after withdrawal."""
    create_dto = CompteCreate(solde=500.0, type=TypeCompte.EPARGNE, devise="MAD")
    epargne = await compte_service.create(create_dto)

    withdraw_amount = 500.01

    with pytest.raises(NegativeBalanceError):
        await compte_service.withdraw(epargne.id, withdraw_amount)

    # Verify balance is unchanged
    current_state = await compte_service.get_by_id(epargne.id)
    assert current_state.solde == 500.0


@pytest.mark.asyncio
async def test_withdraw_epargne_zero_balance_allowed(compte_service: CompteService):
    """Test successful withdrawal that brings EPARGNE account to exactly zero."""
    create_dto = CompteCreate(solde=500.0, type=TypeCompte.EPARGNE, devise="MAD")
    epargne = await compte_service.create(create_dto)

    withdraw_amount = 500.0
    updated = await compte_service.withdraw(epargne.id, withdraw_amount)

    assert updated.solde == 0.0


# --- 6. Tests for Filtering Methods ---


@pytest.mark.asyncio
async def test_find_by_type(compte_service: CompteService):
    """Test filtering accounts by type."""
    await compte_service.create(CompteCreate(type=TypeCompte.COURANT, solde=100.0))
    await compte_service.create(CompteCreate(type=TypeCompte.COURANT, solde=200.0))
    await compte_service.create(CompteCreate(type=TypeCompte.EPARGNE, solde=300.0))

    courants = await compte_service.find_by_type(TypeCompte.COURANT)
    assert len(courants) == 2
    for c in courants:
        assert c.type == TypeCompte.COURANT


@pytest.mark.asyncio
async def test_find_by_solde_range(compte_service: CompteService):
    """Test filtering accounts by balance range."""
    # Accounts with solde 100, 500, 1000
    await compte_service.create(CompteCreate(type=TypeCompte.COURANT, solde=100.0))
    await compte_service.create(CompteCreate(type=TypeCompte.COURANT, solde=500.0))
    await compte_service.create(CompteCreate(type=TypeCompte.EPARGNE, solde=1000.0))

    # Range 200.0 to 800.0 should only find the 500.0 account
    comptes = await compte_service.find_by_solde_range(min_solde=200.0, max_solde=800.0)

    assert len(comptes) == 1
    assert comptes[0].solde == 500.0
