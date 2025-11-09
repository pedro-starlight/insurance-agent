import uuid
from typing import Optional, Dict
from datetime import datetime
from app.models import Claim, ClaimStatus, ExtractedClaimFields
import json
import os


# In-memory storage for claims
claims_store: Dict[str, Claim] = {}


def create_claim() -> str:
    """Create a new claim and return its ID"""
    claim_id = str(uuid.uuid4())
    claim = Claim(
        id=claim_id,
        status=ClaimStatus.PENDING,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    claims_store[claim_id] = claim
    return claim_id


def get_claim(claim_id: str) -> Optional[Claim]:
    """Retrieve a claim by ID"""
    return claims_store.get(claim_id)


def update_claim(claim_id: str, **kwargs) -> Optional[Claim]:
    """Update claim fields"""
    claim = claims_store.get(claim_id)
    if not claim:
        return None
    
    for key, value in kwargs.items():
        if hasattr(claim, key):
            setattr(claim, key, value)
    
    claim.updated_at = datetime.now()
    claims_store[claim_id] = claim
    return claim


def get_claim_by_conversation_id(conversation_id: str) -> Optional[Claim]:
    """
    Find claim by conversation ID.
    
    Args:
        conversation_id: Unique conversation identifier
        
    Returns:
        Claim object or None if not found
    """
    for claim in claims_store.values():
        if hasattr(claim, 'conversation_id') and claim.conversation_id == conversation_id:
            return claim
    return None


def create_claim_from_conversation(conversation_id: str, transcription: str) -> str:
    """
    Create a new claim with conversation data.
    
    Args:
        conversation_id: Unique conversation identifier
        transcription: Full transcription text
        
    Returns:
        The new claim ID
    """
    claim_id = create_claim()
    update_claim(
        claim_id,
        transcription=transcription,
        conversation_id=conversation_id,
        status=ClaimStatus.PENDING
    )
    return claim_id


def update_claim_status(claim_id: str, status: ClaimStatus) -> Optional[Claim]:
    """
    Update claim status with validation.
    
    Args:
        claim_id: Unique claim identifier
        status: New claim status
        
    Returns:
        Updated Claim object or None if not found
    """
    return update_claim(claim_id, status=status)


# Note: extract_claim_fields moved to unified agent service
# Claim extraction is now part of the unified agent processing

