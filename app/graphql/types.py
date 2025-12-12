import strawberry
from typing import Optional
from app.models.compte import TypeCompte as EnumTypeCompte

# 1. Register the Enum so GraphQL understands "COURANT" and "EPARGNE"
strawberry.enum(EnumTypeCompte, name="TypeCompte")


# 2. OUTPUT Type (Reading data)
# This mirrors your SQLModel 'Compte' but for GraphQL response
@strawberry.type
class CompteType:
    id: str
    solde: float
    dateCreation: str
    type: EnumTypeCompte
    devise: str


# 3. INPUT Types (Writing data)
# We use separate classes because inputs often have different rules (optional fields, defaults)


@strawberry.input
class CompteCreateInput:
    solde: float
    type: EnumTypeCompte
    devise: str = "MAD"


@strawberry.input
class CompteUpdateInput:
    solde: Optional[float] = None
    type: Optional[EnumTypeCompte] = None
    devise: Optional[str] = None
