from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel
import uuid

class TypeCompte(str, Enum):
    COURANT = "COURANT"
    EPARGNE = "EPARGNE"


class Compte(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    solde : float = Field(default=0.0)
    dateCreation: datetime = Field(default_factory=datetime.now)
    type : TypeCompte
    devise: str = Field(default="MAD")