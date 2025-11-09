"""
Response builder service for formatting API responses.

Centralizes response formatting logic for claim, coverage, action, and message endpoints.
"""
from typing import Dict, Optional
from datetime import datetime
from app.models import Claim, UnifiedAgentOutput


def build_coverage_response(
    claim_id: str,
    claim: Claim,
    agent_output: Optional[UnifiedAgentOutput] = None
) -> Dict:
    """
    Build coverage decision response.
    
    Args:
        claim_id: Unique claim identifier
        claim: Claim object
        agent_output: UnifiedAgentOutput from agent processing (optional)
        
    Returns:
        Dictionary with claim details and coverage decision
    """
    if agent_output:
        return {
            "claim_id": claim_id,
            "claim_details": {
                "full_name": agent_output.full_name,
                "car_model": {
                    "make": agent_output.car_make,
                    "model": agent_output.car_model,
                    "year": agent_output.car_year
                } if agent_output.car_make else None,
                "location_data": {
                    "free_text": agent_output.location,
                    "components": {
                        "city": agent_output.city,
                        "road_or_street": "",
                        "direction": "",
                        "landmark_or_exit": ""
                    }
                } if agent_output.location else None,
                "assistance_type": agent_output.assistance_type,
                "safety_status": agent_output.safety_status,
                "confirmation": "confirmed"
            },
            "coverage_decision": {
                "covered": agent_output.coverage_covered,
                "reasoning": agent_output.coverage_reasoning,
                "policy_section": agent_output.coverage_policy_section,
                "confidence": agent_output.coverage_confidence
            }
        }
    else:
        # Fallback to claim data if agent hasn't processed yet
        return {
            "claim_id": claim_id,
            "claim_details": {
                "full_name": claim.full_name,
                "car_model": claim.car_model.dict() if claim.car_model else None,
                "location_data": claim.location_data.dict() if claim.location_data else None,
                "assistance_type": claim.assistance_type,
                "safety_status": claim.safety_status,
                "confirmation": claim.confirmation
            },
            "coverage_decision": {
                "covered": False,
                "reasoning": "Agent is still processing this claim",
                "policy_section": None,
                "confidence": 0.0
            }
        }


def build_action_response(
    claim_id: str,
    agent_output: Optional[UnifiedAgentOutput] = None
) -> Dict:
    """
    Build action recommendation response.
    
    Args:
        claim_id: Unique claim identifier
        agent_output: UnifiedAgentOutput from agent processing (optional)
        
    Returns:
        Dictionary with action recommendation
    """
    if agent_output:
        return {
            "claim_id": claim_id,
            "action": {
                "type": agent_output.action_type,
                "garage_name": agent_output.action_garage_name,
                "garage_location": agent_output.action_garage_location,
                "reasoning": agent_output.action_reasoning,
                "estimated_time": agent_output.action_estimated_time
            }
        }
    else:
        return {
            "claim_id": claim_id,
            "action": {
                "type": "unknown",
                "garage_name": None,
                "garage_location": None,
                "reasoning": "Agent is still processing this claim",
                "estimated_time": None
            }
        }


def build_message_response(
    claim_id: str,
    agent_output: Optional[UnifiedAgentOutput] = None
) -> Dict:
    """
    Build policyholder message response.
    
    Args:
        claim_id: Unique claim identifier
        agent_output: UnifiedAgentOutput from agent processing (optional)
        
    Returns:
        Dictionary with policyholder message
    """
    if agent_output:
        return {
            "claim_id": claim_id,
            "message": {
                "assessment": agent_output.message_assessment,
                "next_actions": agent_output.message_next_actions,
                "sent_at": datetime.now().isoformat()
            }
        }
    else:
        return {
            "claim_id": claim_id,
            "message": {
                "assessment": "Your claim is being processed",
                "next_actions": "Please wait while our system reviews your information",
                "sent_at": datetime.now().isoformat()
            }
        }


def build_claim_response(
    claim: Claim,
    agent_output: Optional[UnifiedAgentOutput] = None
) -> Dict:
    """
    Build full claim details response.
    
    Args:
        claim: Claim object
        agent_output: UnifiedAgentOutput from agent processing (optional)
        
    Returns:
        Dictionary with complete claim information
    """
    if not agent_output:
        return {
            "claim": claim.dict(),
            "status": "processing",
            "message": "Agent is still processing this claim"
        }
    
    return {
        "claim": claim.dict(),
        "agent_output": agent_output.dict(),
        "status": "completed"
    }

