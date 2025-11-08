"""
Unified Agent Service - Single OpenAI agent with function calling
Processes insurance claims end-to-end using tools for dynamic data retrieval
"""

import json
import os
from typing import Optional, Callable
from openai import OpenAI
from app.models import UnifiedAgentOutput
from app.services.coverage_service import get_policy_coverage
from app.services.action_service import get_garages


# JSON Schema for structured output (matches UnifiedAgentOutput)
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "car_make": {"type": "string"},
        "car_model": {"type": "string"},
        "car_year": {"type": "string"},
        "location": {"type": "string"},
        "city": {"type": "string"},
        "assistance_type": {"type": "string"},
        "safety_status": {"type": "string"},
        "coverage_covered": {"type": "boolean"},
        "coverage_reasoning": {"type": "string"},
        "coverage_policy_section": {"type": ["string", "null"]},
        "coverage_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "action_type": {"type": "string"},
        "action_garage_name": {"type": ["string", "null"]},
        "action_garage_location": {"type": ["string", "null"]},
        "action_reasoning": {"type": "string"},
        "action_estimated_time": {"type": ["string", "null"]},
        "message_assessment": {"type": "string"},
        "message_next_actions": {"type": "string"}
    },
    "required": [
        "full_name", "car_make", "car_model", "car_year",
        "location", "city", "assistance_type", "safety_status",
        "coverage_covered", "coverage_reasoning",
        "action_type", "action_reasoning",
        "message_assessment", "message_next_actions"
    ],
    "additionalProperties": False
}


# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_policy_coverage",
            "description": "Get insurance policy details by policyholder name. Returns policy coverage rules, exclusions, and limits. Returns None if policy not found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_holder_name": {
                        "type": "string",
                        "description": "Full name of the policyholder extracted from the call transcription"
                    }
                },
                "required": ["policy_holder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_garages",
            "description": "Get list of available garages in a specific city for towing or repair services. Returns list of garages with name, location, and contact info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name extracted from the location in the call transcription"
                    }
                },
                "required": ["city"]
            }
        }
    }
]


async def process_claim_with_agent(
    transcription: str,
    claim_id: str,
    log_callback: Optional[Callable[[str, str], None]] = None
) -> UnifiedAgentOutput:
    """
    Process insurance claim using unified OpenAI agent with function calling
    
    Args:
        transcription: Call transcription text from ElevenLabs
        claim_id: Claim identifier for logging
        log_callback: Optional callback for streaming logs (message, type)
    
    Returns:
        UnifiedAgentOutput with all extracted data and decisions
    """
    
    def log(message: str, log_type: str = "info"):
        """Helper to log with callback"""
        if log_callback:
            log_callback(message, log_type)
        print(f"[{log_type.upper()}] {message}")
    
    try:
        log("Starting unified agent processing", "info")
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        client = OpenAI(api_key=api_key)
        
        # System prompt for the agent
        system_prompt = """You are an insurance claims processing agent. Your task is to:

1. Extract claim details from the call transcription:
   - Policyholder full name
   - Car make, model, and year
   - Location (full address) and city
   - Assistance type (flat_tire, dead_battery, tow, lockout, out_of_fuel, accident, or unknown)
   - Safety status (safe, unsafe, or unknown)

2. Use the get_policy_coverage tool to look up the policyholder's insurance policy

3. Determine coverage eligibility based on:
   - Policy coverage rules
   - Policy exclusions
   - Assistance type requested
   
4. If repair or tow is needed, use the get_garages tool to find nearby garages in the city

5. Recommend the best action:
   - "repair" for on-site fixes (flat tire, battery)
   - "tow" for vehicle transport needed
   - "dispatch_taxi" for basic assistance or if not covered
   - "rental_car" for extended repairs

6. Compose a professional message to the policyholder explaining:
   - Coverage decision (covered or not covered)
   - Recommended next steps
   - Garage details if applicable
   - Estimated time

IMPORTANT: Always return valid data matching the required schema, even if the transcription is incomplete or missing information. 
For missing information, use appropriate defaults:
- Use "unknown" for assistance_type and safety_status if not found
- Use empty string "" for missing text fields
- Use false for coverage_covered if policy cannot be determined
- Use 0.0 for coverage_confidence if information is insufficient
- Use "dispatch_taxi" for action_type if no clear action can be determined"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Process this insurance claim call transcription:\n\n{transcription}"}
        ]
        
        log("Sending initial request to OpenAI agent", "info")
        
        # Multi-turn conversation with function calling
        iteration = 0
        max_iterations = 10  # Safety limit
        tools_used = False  # Track if we've used tools
        
        while iteration < max_iterations:
            iteration += 1
            log(f"Agent iteration {iteration}", "info")
            
            # Determine if we should use structured outputs
            # Use structured outputs after tool calls complete, or if no tools are needed
            if tools_used:
                # Use structured outputs to guarantee JSON format matching schema
                log("Using structured outputs for final response", "info")
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    response_format={
                        "type": "json_schema",
                        "json_schema": OUTPUT_SCHEMA
                    },
                    temperature=0.1
                )
            else:
                # Allow tool calls on first iteration
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.1
                )
            
            message = response.choices[0].message
            messages.append(message)  # Add assistant's response to conversation
            
            # Check if agent wants to call a function
            if message.tool_calls:
                tools_used = True  # Mark that we've used tools
                log(f"Agent requesting {len(message.tool_calls)} tool call(s)", "info")
                
                # Execute function calls
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    log(f"Calling tool: {function_name} with arguments {arguments}", "info")
                    
                    # Call the appropriate function
                    if function_name == "get_policy_coverage":
                        result = get_policy_coverage(arguments["policy_holder_name"])
                        if result:
                            log(f"Policy found for {arguments['policy_holder_name']}", "success")
                        else:
                            log(f"No policy found for {arguments['policy_holder_name']}", "warning")
                    elif function_name == "get_garages":
                        result = get_garages(arguments["city"])
                        log(f"Found {len(result)} garage(s) in {arguments['city']}", "info")
                    else:
                        result = {"error": f"Unknown function: {function_name}"}
                        log(f"Unknown function called: {function_name}", "error")
                    
                    # Add function result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result) if result else "null"
                    })
                
                # Continue conversation - next iteration will use structured outputs
                continue
            
            # Agent finished without tool calls - use structured outputs for final response
            if message.content and not tools_used:
                # First response without tools - retry with structured outputs
                log("Agent returned response without tools, retrying with structured outputs", "info")
                tools_used = True
                messages.pop()  # Remove the non-structured response
                iteration -= 1  # Don't count this iteration
                continue  # Retry with structured outputs
            
            # Agent finished - parse final response
            # With structured outputs, the response is guaranteed to be valid JSON
            if message.content:
                log("Agent completed processing, parsing final output", "info")
                try:
                    # Parse JSON (structured outputs guarantee valid JSON)
                    final_output = json.loads(message.content)
                    log("Successfully parsed agent output", "success")
                    return UnifiedAgentOutput(**final_output)
                except json.JSONDecodeError as e:
                    log(f"Failed to parse agent output as JSON: {e}", "error")
                    log(f"Raw output: {message.content[:500]}", "error")
                    raise ValueError(f"Agent output is not valid JSON: {e}")
            else:
                log("Agent finished without content", "warning")
                break
        
        # If we exit the loop without returning, something went wrong
        log(f"Agent exceeded maximum iterations ({max_iterations})", "error")
        raise ValueError("Agent processing exceeded maximum iterations")
        
    except Exception as e:
        log(f"Error in agent processing: {str(e)}", "error")
        raise

