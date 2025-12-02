import pytest
import pytest_asyncio
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.compte import Compte, TypeCompte
from app.repositories.compte_repository import CompteRepository


@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def repository(test_session):
    return CompteRepository(test_session)


@pytest.mark.asyncio
async def test_create_compte(repository):
    compte = Compte(type=TypeCompte.COURANT, solde=1000.0)
    created = await repository.create(compte)

    assert created.id is not None
    assert created.solde == 1000.0
    assert created.type == TypeCompte.COURANT
    assert created.devise == "MAD"


@pytest.mark.asyncio
async def test_get_by_id(repository):
    compte = Compte(type=TypeCompte.EPARGNE, solde=500.0)
    created = await repository.create(compte)

    found = await repository.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id
    assert found.solde == 500.0


@pytest.mark.asyncio
async def test_get_all(repository):
    await repository.create(Compte(type=TypeCompte.COURANT, solde=100.0))
    await repository.create(Compte(type=TypeCompte.EPARGNE, solde=200.0))

    comptes = await repository.get_all()
    assert len(comptes) == 2


@pytest.mark.asyncio
async def test_update_compte(repository):
    compte = Compte(type=TypeCompte.COURANT, solde=1000.0)
    created = await repository.create(compte)

    created.solde = 1500.0
    updated = await repository.update(created)

    assert updated.solde == 1500.0


@pytest.mark.asyncio
async def test_delete_compte(repository):
    compte = Compte(type=TypeCompte.COURANT, solde=1000.0)
    created = await repository.create(compte)

    result = await repository.delete(created.id)
    assert result is True

    found = await repository.get_by_id(created.id)
    assert found is None


@pytest.mark.asyncio
async def test_find_by_type(repository):
    await repository.create(Compte(type=TypeCompte.COURANT, solde=100.0))
    await repository.create(Compte(type=TypeCompte.COURANT, solde=200.0))
    await repository.create(Compte(type=TypeCompte.EPARGNE, solde=300.0))

    courants = await repository.find_by_type(TypeCompte.COURANT)
    assert len(courants) == 2


@pytest.mark.asyncio
async def test_find_by_solde_range(repository):
    await repository.create(Compte(type=TypeCompte.COURANT, solde=100.0))
    await repository.create(Compte(type=TypeCompte.COURANT, solde=500.0))
    await repository.create(Compte(type=TypeCompte.EPARGNE, solde=1000.0))

    comptes = await repository.find_by_solde_range(min_solde=200.0, max_solde=800.0)
    assert len(comptes) == 1
    assert comptes[0].solde == 500.0
