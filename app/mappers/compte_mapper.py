from datetime import datetime
from uuid import uuid4

from app.models import Compte
from app.schemas import (
    CompteCreate,
    CompteMinimal,
    CompteResponse,
    CompteSummary,
    CompteUpdate,
)


class CompteMapper:
    """Handles conversion between Compte entities and various DTO formats."""

    @staticmethod
    def to_response(compte: Compte) -> CompteResponse:
        """Convert Compte entity to CompteResponse DTO."""
        return CompteResponse(
            id=compte.id,
            solde=compte.solde,
            dateCreation=compte.dateCreation,
            type=compte.type,
            devise=compte.devise,
        )

    @staticmethod
    def to_minimal(compte: Compte) -> CompteMinimal:
        """Convert Compte entity to CompteMinimal projection."""
        return CompteMinimal(
            id=compte.id,
            solde=compte.solde,
        )

    @staticmethod
    def to_summary(compte: Compte) -> CompteSummary:
        """Convert Compte entity to CompteSummary projection."""
        return CompteSummary(
            id=compte.id,
            type=compte.type,
            solde=compte.solde,
            devise=compte.devise,
        )

    @staticmethod
    def to_entity(dto: CompteCreate) -> Compte:
        """Convert CompteCreate DTO to Compte entity."""
        return Compte(
            id=str(uuid4()),
            solde=dto.solde,
            dateCreation=datetime.now(),
            type=dto.type,
            devise=dto.devise,
        )

    @staticmethod
    def update_entity(compte: Compte, dto: CompteUpdate) -> Compte:
        """Update Compte entity with CompteUpdate DTO fields (only non-None values)."""
        if dto.solde is not None:
            compte.solde = dto.solde
        if dto.type is not None:
            compte.type = dto.type
        if dto.devise is not None:
            compte.devise = dto.devise
        return compte
