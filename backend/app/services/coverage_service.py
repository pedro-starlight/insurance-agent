import json
import os
from typing import Optional, Dict, List


def load_policies() -> List[Dict]:
    """Load sample policies from JSON file"""
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    policies_path = os.path.join(data_dir, 'sample_policies.json')
    
    with open(policies_path, 'r') as f:
        data = json.load(f)
    return data.get('policies', [])


def get_policy_coverage(policy_holder_name: str) -> Optional[Dict]:
    """
    Tool function: Get insurance policy by policyholder name
    Uses exact match first, then fuzzy search fallback
    
    Args:
        policy_holder_name: Full name of the policyholder
        
    Returns:
        Policy dictionary if found, None otherwise
    """
    policies = load_policies()
    policy = None
    
    if policy_holder_name:
        # First try exact match (case-insensitive substring)
        for p in policies:
            policy_name = p.get('policyholder_name', '')
            if policy_name.lower() in policy_holder_name.lower() or policy_holder_name.lower() in policy_name.lower():
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
                        score = fuzz.ratio(policy_holder_name.lower(), policy_name.lower())
                        if score > best_score and score >= threshold:
                            best_score = score
                            best_match = p
                
                if best_match:
                    policy = best_match
            except ImportError:
                # Fallback if fuzzy matching library not available
                pass
    
    return policy


# Note: All OpenAI-based coverage evaluation moved to unified agent service
# This file now only contains helper functions for loading and finding policies

