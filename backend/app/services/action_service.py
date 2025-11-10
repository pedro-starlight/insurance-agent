import json
import os
from typing import List, Dict


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

