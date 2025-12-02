from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.compte import Compte, TypeCompte

class CompteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all(self) -> List[Compte]:
        result = await self.session.execute(select(Compte))
        return result.scalars().all()
    
    async def get_by_id(self, compte_id: str) -> Optional[Compte]:
        result = await self.session.execute(select(Compte).where(Compte.id == compte_id))
        return result.scalar_one_or_none()
    
    async def create(self, compte: Compte) -> Compte:
        self.session.add(compte)
        await self.session.commit()
        await self.session.refresh(compte)
        return compte
    
    async def update(self, compte: Compte) -> Compte:
        return await self.create(compte)
    
    async def delete(self, compte_id: str) -> bool:
        compte = await self.get_by_id(compte_id)
        if compte:
            await self.session.delete(compte)
            await self.session.commit()
            return True
        return False
    
    async def find_by_type(self, type_compte: TypeCompte) -> List[Compte]:
        stmt = select(Compte).where(Compte.type == type_compte)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def find_by_sold_range(self, min_sold: Optional[float], max_sold: Optional[float]) -> List[Compte]:
        query = select(Compte)
        if min_sold is not None:
            query = query.where(Compte.solde >= min_sold)
        if max_sold is not None:
            query = query.where(Compte.solde <= max_sold)
        result = await self.session.execute(query)
        return result.scalars().all()