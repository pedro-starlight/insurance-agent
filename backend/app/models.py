from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class ClaimStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COVERED = "covered"
    DENIED = "denied"
    APPROVED = "approved"


# Pydantic models for structured claim extraction (defined before Claim to avoid forward reference issues)
class CarModel(BaseModel):
    make: str
    model: str
    year: str


class LocationComponents(BaseModel):
    road_or_street: str
    direction: str
    city: str
    landmark_or_exit: str


class Location(BaseModel):
    free_text: str
    components: LocationComponents


class ExtractedClaimFields(BaseModel):
    full_name: str
    car_model: CarModel
    location: Location
    assistance_type: Literal["flat_tire", "dead_battery", "tow", "lockout", "out_of_fuel", "accident", "unknown"]
    safety_status: Literal["safe", "unsafe", "unknown"]
    confirmation: Literal["pending", "confirmed"]


class Claim(BaseModel):
    id: str
    full_name: Optional[str] = None
    car_model: Optional[CarModel] = None
    location_data: Optional[Location] = None
    assistance_type: Optional[str] = None
    safety_status: Optional[str] = None
    confirmation: Optional[str] = None
    status: ClaimStatus = ClaimStatus.PENDING
    transcription: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class CoverageDecision(BaseModel):
    claim_id: str
    covered: bool
    reasoning: str
    policy_section: Optional[str] = None
    confidence: float = 0.0


class ActionType(str, Enum):
    REPAIR = "repair"
    TOW = "tow"
    DISPATCH_TAXI = "dispatch_taxi"
    RENTAL_CAR = "rental_car"


class ActionRecommendation(BaseModel):
    claim_id: str
    action: ActionType
    garage_name: Optional[str] = None
    garage_location: Optional[str] = None
    reasoning: str
    estimated_time: Optional[str] = None


class Message(BaseModel):
    claim_id: str
    assessment: str
    next_actions: str
    sent_at: datetime = datetime.now()


class AudioRequest(BaseModel):
    conversation_id: str


class ConversationTranscription(BaseModel):
    conversation_id: str
    transcription: str
    received_at: datetime = datetime.now()


class PolicyholderMessage(BaseModel):
    assessment: str
    next_actions: str


class UnifiedAgentOutput(BaseModel):
    """Output from unified agent processing"""
    # Extracted claim fields
    full_name: str
    car_make: str
    car_model: str
    car_year: str
    location: str
    city: str
    assistance_type: str
    safety_status: str
    
    # Coverage decision
    coverage_covered: bool
    coverage_reasoning: str
    coverage_policy_section: Optional[str] = None
    coverage_confidence: float = 0.0
    
    # Action recommendation
    action_type: str
    action_garage_name: Optional[str] = None
    action_garage_location: Optional[str] = None
    action_reasoning: str
    action_estimated_time: Optional[str] = None
    
    # Policyholder message
    message_assessment: str
    message_next_actions: str

