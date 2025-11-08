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


async def extract_claim_fields(transcription: str) -> ExtractedClaimFields:
    """
    Extract claim fields from transcription using OpenAI with structured outputs
    Returns the full ExtractedClaimFields object with all extracted information
    """
    from openai import OpenAI
    from app.models import ExtractedClaimFields
    
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    response = client.responses.parse(
        model="gpt-5-mini-2025-08-07",
        input=[
            {"role": "system", "content": "Extract structured information from insurance claim conversations. Extract the policyholder's name, car details, location, assistance type, safety status, and confirmation status."},
            {"role": "user", "content": f"Transcription: {transcription}"}
        ],
        text_format=ExtractedClaimFields,
    )
    
    return response.output_parsed

