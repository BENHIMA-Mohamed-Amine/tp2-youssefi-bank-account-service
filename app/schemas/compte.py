from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.compte import TypeCompte


class CompteBase(BaseModel):
    type: TypeCompte
    solde: float = Field(default=0.0, ge=0)
    devise: str = Field(default="MAD")


class CompteCreate(CompteBase):
    pass


class CompteUpdate(BaseModel):
    type: Optional[TypeCompte] = None
    solde: Optional[float] = Field(default=None, ge=0)
    devise: Optional[str] = None


class CompteResponse(CompteBase):
    id: str
    dateCreation: datetime

    class Config:
        from_attributes = True


class CompteMinimal(BaseModel):
    id: str
    solde: float

    class Config:
        from_attributes = True


class CompteSummary(BaseModel):
    id: str
    type: TypeCompte
    solde: float
    devise: str

    class Config:
        from_attributes = True


class TransactionRequest(BaseModel):
    amount: float = Field(gt=0)
