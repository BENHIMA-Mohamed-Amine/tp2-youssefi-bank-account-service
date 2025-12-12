import pytest
import pytest_asyncio

# 🚨 FIX: Using TestClient which is compatible with FastAPI testing structure
from fastapi.testclient import TestClient
from httpx import (
    AsyncClient,
    ASGITransport,  # 1. Import ASGITransport
)
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import the FastAPI app and the dependency to override
from app.main import app
from app.database import get_session
from app.models.compte import TypeCompte


# --- Fixtures for Test Database Setup ---


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Creates a temporary in-memory database engine for the test module."""
    # Using a module scope engine to keep the memory database available
    # for all tests within this file, but isolated from other test files.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    # Dispose of the engine resources
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Provides a fresh, isolated session for each test."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


# --- Fixture for FastAPI Dependency Override ---


@pytest_asyncio.fixture
async def async_client(test_session: AsyncSession, test_engine):
    """
    Initializes the FastAPI application, overrides the session dependency,
    and provides an httpx.AsyncClient for API calls using the TestClient.
    """
    # 1. Apply the dependency override, passing the session fixture directly
    # FIX: Directly return the session object. The previous method returned a generator object
    # which caused 'AttributeError: async_generator object has no attribute add'
    app.dependency_overrides[get_session] = lambda: test_session

    # 2. Re-create tables before starting the client (ensures clean slate for the test)
    # This must be done here to clean the database for each test that uses the client
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    # 3. Create the client
    # We use TestClient as a context manager to trigger startup/shutdown events
    with TestClient(app) as _:
        # 4. Create the AsyncClient with ASGITransport (Fixes the TypeError)
        # 🚨 KEY FIX: 'app' arg is deprecated in AsyncClient, use 'transport' instead
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as async_client_wrapper:
            # Manually set the base_url prefix for tests to use
            async_client_wrapper.base_url = "http://test/api/v1/comptes"
            yield async_client_wrapper

    # 5. Cleanup overrides
    app.dependency_overrides = {}


# --- Test Cases ---


@pytest.mark.asyncio
async def test_create_and_read_compte_success(async_client: AsyncClient):
    """Tests POST /comptes (create) and GET /comptes/{id} (read)."""

    # 1. Test POST /comptes (Create)
    create_payload = {
        "type": TypeCompte.COURANT.value,
        "solde": 150.75,
        "devise": "USD",
    }
    # Note: async_client handles the relative path properly using the fixture's base_url
    response = await async_client.post("/", json=create_payload)

    assert response.status_code == 201
    created_compte = response.json()
    assert created_compte["solde"] == 150.75
    assert created_compte["type"] == TypeCompte.COURANT.value
    assert "id" in created_compte
    compte_id = created_compte["id"]

    # 2. Test GET /comptes/{id} (Read)
    response = await async_client.get(f"/{compte_id}")
    assert response.status_code == 200
    read_compte = response.json()
    assert read_compte["id"] == compte_id
    assert read_compte["solde"] == 150.75


@pytest.mark.asyncio
async def test_create_compte_negative_balance_failure(async_client: AsyncClient):
    """Tests POST /comptes failure for EPARGNE with negative balance."""

    create_payload = {"type": TypeCompte.EPARGNE.value, "solde": -10.0, "devise": "MAD"}
    response = await async_client.post("/", json=create_payload)

    # Should fail with 422 Unprocessable Entity due to business rule
    assert response.status_code == 422
    assert "EPARGNE accounts cannot have negative balance" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_compte_not_found(async_client: AsyncClient):
    """Tests GET /comptes/{id} with non-existent ID."""
    response = await async_client.get("/99999")
    assert response.status_code == 404
    assert "Compte with id 99999 not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_and_delete_compte(async_client: AsyncClient):
    """Tests PUT /comptes/{id} (update) and DELETE /comptes/{id} (delete)."""

    # Setup: Create an account
    create_payload = {"type": TypeCompte.COURANT.value, "solde": 500.0}
    created_response = await async_client.post("/", json=create_payload)
    compte_id = created_response.json()["id"]

    # 1. Test PUT /comptes/{id} (Update)
    update_payload = {"solde": 750.0}
    response = await async_client.put(f"/{compte_id}", json=update_payload)

    assert response.status_code == 200
    updated_compte = response.json()
    assert updated_compte["solde"] == 750.0

    # 2. Test DELETE /comptes/{id} (Delete)
    response = await async_client.delete(f"/{compte_id}")
    assert response.status_code == 204  # No Content

    # 3. Verify deletion
    response = await async_client.get(f"/{compte_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_comptes_and_projections(async_client: AsyncClient):
    """Tests GET /comptes with different projection query parameters."""

    # Setup: Create accounts
    await async_client.post(
        "/", json={"type": TypeCompte.COURANT.value, "solde": 100.0}
    )
    await async_client.post(
        "/", json={"type": TypeCompte.EPARGNE.value, "solde": 200.0}
    )

    # 1. Test 'full' projection
    response_full = await async_client.get("/", params={"projection": "full"})
    assert response_full.status_code == 200
    assert len(response_full.json()) == 2
    assert "dateCreation" in response_full.json()[0]  # Check for full detail

    # 2. Test 'summary' projection
    response_summary = await async_client.get("/", params={"projection": "summary"})
    assert response_summary.status_code == 200
    assert "type" in response_summary.json()[0]
    assert "dateCreation" not in response_summary.json()[0]  # Check for summary detail

    # 3. Test 'minimal' projection
    response_minimal = await async_client.get("/", params={"projection": "minimal"})
    assert response_minimal.status_code == 200
    assert "solde" in response_minimal.json()[0]
    assert "type" not in response_minimal.json()[0]  # Check for minimal detail


@pytest.mark.asyncio
async def test_search_by_type_and_range(async_client: AsyncClient):
    """Tests GET /comptes/search endpoint."""

    # Setup: Create accounts with distinct values
    await async_client.post(
        "/", json={"type": TypeCompte.COURANT.value, "solde": 100.0}
    )
    await async_client.post(
        "/", json={"type": TypeCompte.COURANT.value, "solde": 500.0}
    )
    await async_client.post(
        "/", json={"type": TypeCompte.EPARGNE.value, "solde": 1000.0}
    )

    # 1. Search by type EPARGNE
    response_type = await async_client.get(
        "/search", params={"type": TypeCompte.EPARGNE.value}
    )
    assert response_type.status_code == 200
    assert len(response_type.json()) == 1
    assert response_type.json()[0]["solde"] == 1000.0

    # 2. Search by solde range (200.0 to 800.0)
    response_range = await async_client.get(
        "/search", params={"min_solde": 200.0, "max_solde": 800.0}
    )
    assert response_range.status_code == 200
    assert len(response_range.json()) == 1
    assert response_range.json()[0]["solde"] == 500.0

    # 3. Search with no criteria
    response_bad = await async_client.get("/search")
    assert response_bad.status_code == 400
    assert "Must provide at least one search criterion" in response_bad.json()["detail"]


@pytest.mark.asyncio
async def test_deposit_success_and_failure(async_client: AsyncClient):
    """Tests POST /comptes/{id}/deposit."""

    # Setup: Create an account
    created_response = await async_client.post(
        "/", json={"type": TypeCompte.COURANT.value, "solde": 100.0}
    )
    compte_id = created_response.json()["id"]

    # 1. Deposit Success
    deposit_payload = {"amount": 50.0}
    response = await async_client.post(f"/{compte_id}/deposit", json=deposit_payload)
    assert response.status_code == 200
    assert response.json()["solde"] == 150.0

    # 2. Deposit Invalid Amount Failure (amount <= 0)
    deposit_payload_invalid = {"amount": 0.0}
    response_invalid = await async_client.post(
        f"/{compte_id}/deposit", json=deposit_payload_invalid
    )
    assert response_invalid.status_code == 422
    assert "Deposit amount must be positive" in response_invalid.json()["detail"]


@pytest.mark.asyncio
async def test_withdraw_success_and_failures(async_client: AsyncClient):
    """Tests POST /comptes/{id}/withdraw."""

    # Setup: Create a COURANT (Current) account
    created_courant = await async_client.post(
        "/", json={"type": TypeCompte.COURANT.value, "solde": 200.0}
    )
    compte_id_courant = created_courant.json()["id"]

    # Setup: Create an EPARGNE (Savings) account
    created_epargne = await async_client.post(
        "/", json={"type": TypeCompte.EPARGNE.value, "solde": 100.0}
    )
    compte_id_epargne = created_epargne.json()["id"]

    # 1. Withdrawal Success (COURANT)
    withdraw_payload = {"amount": 50.0}
    response_success = await async_client.post(
        f"/{compte_id_courant}/withdraw", json=withdraw_payload
    )
    assert response_success.status_code == 200
    assert response_success.json()["solde"] == 150.0  # 200 - 50 = 150

    # 2. Withdrawal Invalid Amount Failure
    withdraw_payload_invalid = {"amount": -10.0}
    response_invalid = await async_client.post(
        f"/{compte_id_courant}/withdraw", json=withdraw_payload_invalid
    )
    assert response_invalid.status_code == 422
    assert "Withdrawal amount must be positive" in response_invalid.json()["detail"]

    # 3. Withdrawal Negative Balance Failure (EPARGNE)
    withdraw_payload_excessive = {"amount": 100.01}
    response_negative = await async_client.post(
        f"/{compte_id_epargne}/withdraw", json=withdraw_payload_excessive
    )
    assert response_negative.status_code == 422
    assert (
        "EPARGNE accounts cannot have negative balance"
        in response_negative.json()["detail"]
    )

    # 4. Withdrawal Not Found Failure
    response_not_found = await async_client.post(
        "/99999/withdraw", json={"amount": 10.0}
    )
    assert response_not_found.status_code == 404
