import json
import os
from typing import Optional, Dict
from app.models import Claim, CoverageDecision


def load_policies():
    """Load sample policies from JSON file"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    policies_path = os.path.join(data_dir, 'sample_policies.json')
    
    with open(policies_path, 'r') as f:
        data = json.load(f)
    return data.get('policies', [])


def find_policy(claim: Claim) -> Optional[Dict]:
    """
    Find the matching policy for a claim using exact and fuzzy name matching
    
    Args:
        claim: The claim to find a policy for
        
    Returns:
        Policy dictionary if found, None otherwise
    """
    policies = load_policies()
    
    # Find matching policy (use full_name if available, fallback to policyholder_name)
    full_name = claim.full_name or claim.policyholder_name
    policy = None
    
    if full_name:
        # First try exact match (case-insensitive substring)
        for p in policies:
            policy_name = p.get('policyholder_name', '')
            if policy_name.lower() in full_name.lower() or full_name.lower() in policy_name.lower():
                policy = p
                break
        
        # If no exact match, try fuzzy search
        if not policy:
            try:
                from thefuzz import fuzz
                
                best_match = None
                best_score = 0
                threshold = 70  # Minimum similarity score (0-100)
                
                for p in policies:
                    policy_name = p.get('policyholder_name', '')
                    if policy_name:
                        # Calculate similarity score
                        score = fuzz.ratio(full_name.lower(), policy_name.lower())
                        if score > best_score and score >= threshold:
                            best_score = score
                            best_match = p
                
                if best_match:
                    policy = best_match
            except ImportError:
                # Fallback if fuzzy matching library not available
                pass
    
    # Final fallback: use first policy if no match found
    if not policy:
        policy = policies[0] if policies else None
    
    return policy


def draft_policy_text(policy: Dict) -> str:
    """
    Draft formatted policy text for coverage evaluation
    
    Args:
        policy: The policy dictionary
        
    Returns:
        Formatted policy text string
    """
    return f"""
Policy Type: {policy.get('policy_type')}
Coverage Rules:
{json.dumps(policy.get('coverage_rules', []), indent=2)}
Exclusions:
{json.dumps(policy.get('exclusions', []), indent=2)}
"""


def draft_claim_text(claim: Claim) -> str:
    """
    Draft formatted claim text for coverage evaluation
    
    Args:
        claim: The claim to format
        
    Returns:
        Formatted claim text string
    """
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
    
    # Build car details string
    car_details = "Not available"
    if claim.car_model:
        car_details = f"Make: {claim.car_model.make}, Model: {claim.car_model.model}, Year: {claim.car_model.year}"
    
    # Build location components string
    location_components = "Not available"
    if claim.location_data:
        location_components = f"Road: {claim.location_data.components.road_or_street}, City: {claim.location_data.components.city}, Landmark: {claim.location_data.components.landmark_or_exit}"
    
    return f"""
Claim Details:
- Full Name: {full_name}
- Assistance Type: {assistance_type}
- Location: {location_text}
- Car: {car_info}
- Safety Status: {safety_status}
- Car Details: {car_details}
- Location Components: {location_components}
"""


def evaluate_coverage(claim: Claim, policy: Dict) -> CoverageDecision:
    """
    Evaluate if a claim is covered by a policy using OpenAI
    
    Args:
        claim: The claim to evaluate
        policy: The policy dictionary to check against
        
    Returns:
        CoverageDecision with coverage result and reasoning
    """
    from openai import OpenAI
    
    # Use OpenAI to check coverage against policy
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    # Draft policy and claim texts
    policy_text = draft_policy_text(policy)
    claim_text = draft_claim_text(claim)
    
    prompt = f"""Review this claim against the policy and determine if it's covered.

{policy_text}

{claim_text}

Determine if this claim is covered. Consider:
1. Does the damage type match any coverage rules?
2. Are there any exclusions that apply?
3. What is the reasoning for your decision?

Return JSON with:
- covered: boolean
- reasoning: string explaining the decision
- policy_section: string indicating which rule applies
- confidence: float between 0 and 1"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert insurance coverage analyst. Always return valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    result = json.loads(response.choices[0].message.content)
    
    return CoverageDecision(
        claim_id=claim.id,
        covered=result.get("covered", False),
        reasoning=result.get("reasoning", "Unable to determine coverage."),
        policy_section=result.get("policy_section", "general"),
        confidence=result.get("confidence", 0.5)
    )


def check_coverage(claim: Claim) -> CoverageDecision:
    """
    Check if claim is covered by policy using OpenAI with RAG
    Uses policy documents to make coverage decisions
    """
    # Find the matching policy
    policy = find_policy(claim)
    
    if not policy:
        return CoverageDecision(
            claim_id=claim.id,
            covered=False,
            reasoning="No policy found for this customer.",
            confidence=0.0
        )
    
    # Evaluate coverage against the found policy
    return evaluate_coverage(claim, policy)

