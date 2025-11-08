import json
import os
from typing import Optional, List, Dict
from app.models import Claim, ActionRecommendation, ActionType, CoverageDecision


def load_garages() -> List[Dict]:
    """Load garage data from JSON file"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    policies_path = os.path.join(data_dir, 'sample_policies.json')
    
    with open(policies_path, 'r') as f:
        data = json.load(f)
    return data.get('garages', [])


def get_garages(city: str) -> List[Dict]:
    """
    Tool function: Get available garages by city
    Returns list of garage dicts matching the city
    
    Args:
        city: City name to search for garages
        
    Returns:
        List of garage dictionaries in that city
    """
    all_garages = load_garages()
    
    # Filter garages by city (case-insensitive partial match)
    matching_garages = [
        g for g in all_garages 
        if city.lower() in g.get('location', '').lower()
    ]
    
    # If no exact match, return all garages as fallback
    if not matching_garages:
        matching_garages = all_garages
    
    return matching_garages


# Legacy function - kept for backward compatibility but not used by unified agent
def recommend_action(claim: Claim, coverage: CoverageDecision) -> ActionRecommendation:
    """
    Recommend next best action using OpenAI
    """
    
    if not coverage.covered:
        return ActionRecommendation(
            claim_id=claim.id,
            action=ActionType.DISPATCH_TAXI,
            reasoning="Claim not covered. Providing basic assistance.",
            estimated_time="15 minutes"
        )
    
    from openai import OpenAI
    
    garages = load_garages()
    garage_info = json.dumps(garages, indent=2)
    
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    # Use structured fields if available, fallback to legacy fields
    assistance_type = claim.assistance_type or claim.damage_type or "unknown"
    full_name = claim.full_name or claim.policyholder_name or "unknown"
    location_text = claim.location_data.free_text if claim.location_data else (claim.location or "unknown")
    car_info = None
    if claim.car_model:
        car_info = f"{claim.car_model.year} {claim.car_model.make} {claim.car_model.model}".strip()
    else:
        car_info = claim.car_info or "unknown"
    safety_status = claim.safety_status or "unknown"
    confirmation = claim.confirmation or "pending"
    
    claim_text = f"""
Claim Details:
- Full Name: {full_name}
- Assistance Type: {assistance_type}
- Location: {location_text}
- Car: {car_info}
- Safety Status: {safety_status}
- Confirmation: {confirmation}
- Coverage: {coverage.reasoning}
- Car Details: {f"Make: {claim.car_model.make}, Model: {claim.car_model.model}, Year: {claim.car_model.year}" if claim.car_model else "Not available"}
- Location Components: {f"Road: {claim.location_data.components.road_or_street}, City: {claim.location_data.components.city}, Landmark: {claim.location_data.components.landmark_or_exit}" if claim.location_data else "Not available"}
"""
    
    prompt = f"""You are an insurance agent determining the best action for a roadside assistance claim.

{claim_text}

Available Garages:
{garage_info}

Determine the best action:
- "repair": Mobile repair unit can fix on-site (for flat tires, battery issues, minor repairs)
- "tow": Vehicle needs towing to garage (for engine failure, major damage, accidents)
- "dispatch_taxi": Client needs immediate transportation (for urgent situations, no vehicle transport)
- "rental_car": Client needs rental car (for covered claims requiring extended repair)

Also select the best garage if repair or tow is needed.

Return JSON with:
- action: one of "repair", "tow", "dispatch_taxi", "rental_car"
- garage_name: name of selected garage (if applicable)
- garage_location: location of selected garage (if applicable)
- reasoning: explanation of the decision
- estimated_time: estimated time for service (e.g., "30 minutes")"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert insurance agent. Always return valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    result = json.loads(response.choices[0].message.content)
    
    return ActionRecommendation(
        claim_id=claim.id,
        action=ActionType(result.get("action", "repair")),
        garage_name=result.get("garage_name"),
        garage_location=result.get("garage_location"),
        reasoning=result.get("reasoning", "Action recommended based on claim details."),
        estimated_time=result.get("estimated_time", "30 minutes")
    )

