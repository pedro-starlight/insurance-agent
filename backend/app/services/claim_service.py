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


# Note: extract_claim_fields moved to unified agent service
# Claim extraction is now part of the unified agent processing

