import uuid
from typing import Optional, Dict
from datetime import datetime
from app.models import Claim, ClaimStatus, ExtractedClaimFields
import json
import os


# In-memory storage for claims
claims_store: Dict[str, Claim] = {}


def get_claims_directory() -> str:
    """
    Get the path to the claims directory.
    
    Returns:
        Absolute path to claims directory
    """
    current_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(current_dir, 'data', 'claims')


def save_claim_to_file(claim: Claim) -> str:
    """
    Save claim to a JSON file for persistence and debugging.
    
    Args:
        claim: Claim object to save
        
    Returns:
        Path to the saved file
        
    Raises:
        Exception: If file save fails
    """
    claims_dir = get_claims_directory()
    os.makedirs(claims_dir, exist_ok=True)
    
    claim_file = os.path.join(claims_dir, f"{claim.id}.json")
    
    # Convert claim to dict for JSON serialization
    claim_data = claim.dict()
    
    # Ensure datetime fields are ISO format strings
    if 'created_at' in claim_data and claim_data['created_at']:
        if hasattr(claim_data['created_at'], 'isoformat'):
            claim_data['created_at'] = claim_data['created_at'].isoformat()
    if 'updated_at' in claim_data and claim_data['updated_at']:
        if hasattr(claim_data['updated_at'], 'isoformat'):
            claim_data['updated_at'] = claim_data['updated_at'].isoformat()
    
    with open(claim_file, 'w') as f:
        json.dump(claim_data, f, indent=2, default=str)
    
    print(f"✓ Saved claim to file: {claim_file}")
    return claim_file


def load_claim_from_file(claim_id: str) -> Optional[Claim]:
    """
    Load claim from JSON file.
    
    Args:
        claim_id: Unique claim identifier
        
    Returns:
        Claim object or None if not found
    """
    claims_dir = get_claims_directory()
    claim_file = os.path.join(claims_dir, f"{claim_id}.json")
    
    if not os.path.exists(claim_file):
        return None
    
    try:
        with open(claim_file, 'r') as f:
            data = json.load(f)
            return Claim(**data)
    except Exception as e:
        print(f"Error loading claim from file: {e}")
        return None


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
    save_claim_to_file(claim)  # Persist to file
    return claim_id


def get_claim(claim_id: str) -> Optional[Claim]:
    """Retrieve a claim by ID from memory or file"""
    # Check memory first
    claim = claims_store.get(claim_id)
    if claim:
        return claim
    
    # Fallback to file if not in memory (e.g., after restart)
    claim = load_claim_from_file(claim_id)
    if claim:
        claims_store[claim_id] = claim  # Load into memory for future access
        print(f"✓ Loaded claim {claim_id} from file into memory")
        return claim
    
    return None


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
    save_claim_to_file(claim)  # Persist to file
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

