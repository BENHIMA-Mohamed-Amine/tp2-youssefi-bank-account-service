import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_session

# --- Fixtures ---


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Creates a temporary in-memory database engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Provides a fresh, isolated session for each test."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(test_session: AsyncSession, test_engine):
    """Initializes client and overrides DB session."""
    app.dependency_overrides[get_session] = lambda: test_session

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides = {}


# --- GraphQL Test Cases ---


@pytest.mark.asyncio
async def test_graphql_create_and_get_compte(async_client: AsyncClient):
    """Test creating an account via Mutation and fetching it via Query."""

    # 1. Mutation
    mutation = """
    mutation {
        createCompte(input: {solde: 5000.0, type: COURANT, devise: "EUR"}) {
            id, solde, type
        }
    }
    """
    response = await async_client.post("/graphql", json={"query": mutation})
    assert response.status_code == 200
    compte_id = response.json()["data"]["createCompte"]["id"]

    # 2. Query
    query = f"""
    query {{ getCompte(id: "{compte_id}") {{ id, solde, devise }} }}
    """
    response = await async_client.post("/graphql", json={"query": query})
    data = response.json()["data"]["getCompte"]
    assert data["id"] == compte_id
    assert data["solde"] == 5000.0


@pytest.mark.asyncio
async def test_graphql_update_compte(async_client: AsyncClient):
    """Test updating an account."""

    # Setup
    setup = """mutation { createCompte(input: {solde: 100.0, type: COURANT}) { id } }"""
    resp = await async_client.post("/graphql", json={"query": setup})
    compte_id = resp.json()["data"]["createCompte"]["id"]

    # Update
    update = f"""
    mutation {{ updateCompte(id: "{compte_id}", input: {{solde: 999.0}}) {{ solde }} }}
    """
    response = await async_client.post("/graphql", json={"query": update})
    assert response.json()["data"]["updateCompte"]["solde"] == 999.0


@pytest.mark.asyncio
async def test_graphql_delete_compte(async_client: AsyncClient):
    """Test deleting an account."""

    # Setup
    setup = """mutation { createCompte(input: {solde: 100.0, type: COURANT}) { id } }"""
    resp = await async_client.post("/graphql", json={"query": setup})
    compte_id = resp.json()["data"]["createCompte"]["id"]

    # Delete
    delete = f"""mutation {{ deleteCompte(id: "{compte_id}") }}"""
    response = await async_client.post("/graphql", json={"query": delete})
    assert "deleted successfully" in response.json()["data"]["deleteCompte"]

    # Verify
    query = f"""query {{ getCompte(id: "{compte_id}") {{ id }} }}"""
    response = await async_client.post("/graphql", json={"query": query})
    assert response.json()["data"]["getCompte"] is None


@pytest.mark.asyncio
async def test_graphql_deposit_withdraw(async_client: AsyncClient):
    """Test custom domain logic."""

    # Setup
    setup = """mutation { createCompte(input: {solde: 100.0, type: COURANT}) { id } }"""
    resp = await async_client.post("/graphql", json={"query": setup})
    compte_id = resp.json()["data"]["createCompte"]["id"]

    # Deposit
    deposit = f"""mutation {{ deposit(id: "{compte_id}", amount: 50.0) {{ solde }} }}"""
    await async_client.post("/graphql", json={"query": deposit})

    # Withdraw
    withdraw = (
        f"""mutation {{ withdraw(id: "{compte_id}", amount: 20.0) {{ solde }} }}"""
    )
    response = await async_client.post("/graphql", json={"query": withdraw})
    assert response.json()["data"]["withdraw"]["solde"] == 130.0


@pytest.mark.asyncio
async def test_graphql_search_filters(async_client: AsyncClient):
    """Test filtering by Type and Balance Range."""

    # Setup: Create 3 accounts
    # 1. COURANT, 100.0
    await async_client.post(
        "/graphql",
        json={
            "query": """
        mutation { createCompte(input: {solde: 100.0, type: COURANT}) { id } }
    """
        },
    )
    # 2. COURANT, 500.0
    await async_client.post(
        "/graphql",
        json={
            "query": """
        mutation { createCompte(input: {solde: 500.0, type: COURANT}) { id } }
    """
        },
    )
    # 3. EPARGNE, 1000.0
    await async_client.post(
        "/graphql",
        json={
            "query": """
        mutation { createCompte(input: {solde: 1000.0, type: EPARGNE}) { id } }
    """
        },
    )

    # Test 1: Search by Type (EPARGNE)
    query_type = """
    query {
        getAllComptes(type: EPARGNE) {
            solde
            type
        }
    }
    """
    response = await async_client.post("/graphql", json={"query": query_type})
    data = response.json()["data"]["getAllComptes"]
    assert len(data) == 1
    assert data[0]["type"] == "EPARGNE"
    assert data[0]["solde"] == 1000.0

    # Test 2: Search by Range (200.0 - 800.0) -> Should find the 500.0 one
    query_range = """
    query {
        getAllComptes(minSolde: 200.0, maxSolde: 800.0) {
            solde
        }
    }
    """
    response = await async_client.post("/graphql", json={"query": query_range})
    data = response.json()["data"]["getAllComptes"]
    assert len(data) == 1
    assert data[0]["solde"] == 500.0

    # Test 3: Get All (No args) -> Should find 3
    query_all = """
    query { getAllComptes { id } }
    """
    response = await async_client.post("/graphql", json={"query": query_all})
    assert len(response.json()["data"]["getAllComptes"]) == 3
